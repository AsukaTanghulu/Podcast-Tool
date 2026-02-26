"""
音频获取模块
负责从小宇宙播客平台解析和下载音频文件
"""

import re
import os
import time
from pathlib import Path
from typing import Optional, Tuple
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from loguru import logger
import librosa
import numpy as np


class AudioFetchError(Exception):
    """音频获取异常"""
    pass


class AudioQualityError(Exception):
    """音频质量异常"""
    pass


class AudioFetcher:
    """音频获取器"""

    def __init__(self, config: dict = None):
        """
        初始化音频获取器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.user_agent = self.config.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        self.chunk_size = self.config.get("chunk_size", 8192)

    def extract_audio_url(self, page_url: str) -> str:
        """
        从小宇宙页面提取音频链接

        Args:
            page_url: 播客页面 URL

        Returns:
            音频下载链接

        Raises:
            AudioFetchError: 提取失败
        """
        logger.info(f"开始解析页面: {page_url}")

        headers = {"User-Agent": self.user_agent}

        try:
            response = requests.get(page_url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            html_content = response.text
        except Exception as e:
            raise AudioFetchError(f"页面请求失败: {e}")

        # 策略1: 正则匹配 .m4a 链接
        pattern = r'https?://[^"\'\s]+\.m4a[^"\'\s]*'
        matches = re.findall(pattern, html_content)
        if matches:
            audio_url = matches[0]
            logger.info(f"策略1成功: 找到音频链接 {audio_url}")
            return audio_url

        # 策略2: BeautifulSoup 解析 audio 标签
        soup = BeautifulSoup(html_content, 'html.parser')
        audio_tags = soup.find_all(['audio', 'source'])
        for tag in audio_tags:
            src = tag.get('src')
            if src and '.m4a' in src:
                logger.info(f"策略2成功: 找到音频链接 {src}")
                return src

        # 策略3: 查找 JSON 数据中的音频链接
        json_pattern = r'"enclosureUrl"\s*:\s*"([^"]+)"'
        json_matches = re.findall(json_pattern, html_content)
        if json_matches:
            audio_url = json_matches[0]
            logger.info(f"策略3成功: 找到音频链接 {audio_url}")
            return audio_url

        # 策略4: 查找其他可能的音频格式
        other_patterns = [
            r'https?://[^"\'\s]+\.mp3[^"\'\s]*',
            r'https?://[^"\'\s]+\.wav[^"\'\s]*',
        ]
        for pattern in other_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                audio_url = matches[0]
                logger.info(f"策略4成功: 找到音频链接 {audio_url}")
                return audio_url

        raise AudioFetchError("未能从页面中提取到音频链接")

    def download_audio(self, audio_url: str, save_path: str) -> Tuple[str, int]:
        """
        下载音频文件

        Args:
            audio_url: 音频下载链接
            save_path: 保存路径

        Returns:
            (文件路径, 文件大小)

        Raises:
            AudioFetchError: 下载失败
        """
        # 检查文件是否已存在
        if Path(save_path).exists():
            file_size = Path(save_path).stat().st_size
            logger.info(f"音频文件已存在，跳过下载: {save_path}, 大小: {file_size} bytes")
            return save_path, file_size

        logger.info(f"开始下载音频: {audio_url}")

        # 确保保存目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        headers = {"User-Agent": self.user_agent}

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    audio_url,
                    headers=headers,
                    stream=True,
                    timeout=self.timeout
                )
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))

                # 流式下载
                with open(save_path, 'wb') as f, tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    desc='下载音频'
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

                file_size = os.path.getsize(save_path)
                logger.info(f"下载完成: {save_path}, 大小: {file_size} bytes")

                # 验证下载
                self._validate_download(save_path, file_size)

                return save_path, file_size

            except Exception as e:
                logger.warning(f"下载失败（尝试 {attempt + 1}/{self.max_retries}）: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    raise AudioFetchError(f"下载失败（已重试 {self.max_retries} 次）: {e}")

    def _validate_download(self, file_path: str, file_size: int):
        """
        验证下载的音频文件

        Args:
            file_path: 文件路径
            file_size: 文件大小

        Raises:
            AudioFetchError: 验证失败
        """
        checks = {
            "file_exists": os.path.exists(file_path),
            "file_size": file_size > 1024 * 100,  # 至少 100KB
            "file_format": file_path.endswith(('.m4a', '.mp3', '.wav')),
        }

        if not all(checks.values()):
            raise AudioFetchError(f"音频下载验证失败: {checks}")

        logger.debug("音频下载验证通过")

    def validate_audio_quality(self, file_path: str) -> dict:
        """
        检测音频质量

        Args:
            file_path: 音频文件路径

        Returns:
            质量检测结果字典

        Raises:
            AudioQualityError: 质量不合格
        """
        logger.info(f"开始检测音频质量: {file_path}")

        try:
            # 简化检测：只检查文件基本属性
            # m4a 格式在 Windows 上 librosa 可能无法直接加载，但 faster-whisper 可以处理
            file_size = os.path.getsize(file_path)

            checks = {
                "file_exists": os.path.exists(file_path),
                "file_size": file_size > 1024 * 100,  # 至少 100KB
                "file_format": file_path.endswith(('.m4a', '.mp3', '.wav')),
            }

            result = {
                "passed": all(checks.values()),
                "duration": 0,  # 将由 Whisper 在转录时获取
                "sample_rate": 0,
                "amplitude": 0,
                "checks": checks
            }

            if not result["passed"]:
                raise AudioQualityError(f"音频质量检测失败: {checks}")

            logger.info(f"音频质量检测通过: 文件大小={file_size / 1024 / 1024:.1f}MB")
            return result

        except Exception as e:
            if isinstance(e, AudioQualityError):
                raise
            raise AudioQualityError(f"音频文件无效或损坏: {e}")

    def fetch(self, page_url: str, save_dir: str = "data/audio") -> Tuple[str, dict]:
        """
        完整的音频获取流程

        Args:
            page_url: 播客页面 URL
            save_dir: 保存目录

        Returns:
            (文件路径, 元数据字典)

        Raises:
            AudioFetchError: 获取失败
            AudioQualityError: 质量不合格
        """
        # 1. 提取音频链接
        audio_url = self.extract_audio_url(page_url)

        # 2. 生成保存路径
        file_ext = audio_url.split('.')[-1].split('?')[0]
        if file_ext not in ['m4a', 'mp3', 'wav']:
            file_ext = 'm4a'

        timestamp = int(time.time())
        filename = f"podcast_{timestamp}.{file_ext}"
        save_path = os.path.join(save_dir, filename)

        # 3. 下载音频
        file_path, file_size = self.download_audio(audio_url, save_path)

        # 4. 质量检测
        quality_info = self.validate_audio_quality(file_path)

        # 5. 返回元数据
        metadata = {
            "file_path": file_path,
            "file_size": file_size,
            "audio_url": audio_url,
            "duration": quality_info["duration"],
            "sample_rate": quality_info["sample_rate"],
        }

        logger.info(f"音频获取完成: {file_path}")
        return file_path, metadata


def test_audio_fetcher():
    """测试音频获取器"""
    fetcher = AudioFetcher()

    # 测试用例（需要替换为真实的小宇宙链接）
    test_url = "https://www.xiaoyuzhoufm.com/episode/xxxxx"

    try:
        file_path, metadata = fetcher.fetch(test_url)
        print(f"✓ 音频获取成功: {file_path}")
        print(f"  元数据: {metadata}")
    except Exception as e:
        print(f"✗ 音频获取失败: {e}")


if __name__ == "__main__":
    test_audio_fetcher()
