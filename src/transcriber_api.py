"""
语音识别模块 - API 版本
使用 OpenAI Whisper API 进行转录（无需本地模型）
"""

import time
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
import requests


class TranscriptionError(Exception):
    """转录异常"""
    pass


class WhisperAPITranscriber:
    """Whisper API 转录器"""

    def __init__(self, config: dict = None):
        """
        初始化转录器

        Args:
            config: 配置字典，需包含 api_key
        """
        self.config = config or {}
        self.api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.language = self.config.get("language", "zh")
        self.paragraph_gap = self.config.get("paragraph_gap", 2.0)

        if not self.api_key:
            raise TranscriptionError("未提供 API Key，请在配置中设置 api_key 或环境变量 OPENAI_API_KEY")

        self.api_url = "https://api.openai.com/v1/audio/transcriptions"
        logger.info("Whisper API 转录器初始化成功")

    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        使用 API 转录音频文件

        Args:
            audio_path: 音频文件路径

        Returns:
            段落列表，每个段落包含 start, end, text

        Raises:
            TranscriptionError: 转录失败
        """
        logger.info(f"开始使用 API 转录音频: {audio_path}")
        start_time = time.time()

        try:
            # 准备请求
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'file': audio_file,
                }
                data = {
                    'model': 'whisper-1',
                    'language': self.language,
                    'response_format': 'verbose_json',  # 获取时间戳
                }
                headers = {
                    'Authorization': f'Bearer {self.api_key}'
                }

                # 发送请求
                logger.info("正在调用 Whisper API...")
                response = requests.post(
                    self.api_url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=300  # 5分钟超时
                )

                if response.status_code != 200:
                    error_msg = f"API 请求失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise TranscriptionError(error_msg)

                result = response.json()

            # 处理结果
            if 'segments' in result:
                paragraphs = self._process_segments(result['segments'])
            else:
                # 如果没有时间戳，创建单个段落
                paragraphs = [{
                    "start": 0,
                    "end": 0,
                    "text": result.get('text', '')
                }]

            elapsed_time = time.time() - start_time
            logger.info(
                f"API 转录完成: {len(paragraphs)} 个段落, "
                f"耗时 {elapsed_time:.1f}s"
            )

            return paragraphs

        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求失败: {e}")
            raise TranscriptionError(f"API 请求失败: {e}")
        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise TranscriptionError(f"转录失败: {e}")

    def _process_segments(self, segments: List[Dict]) -> List[Dict[str, Any]]:
        """
        处理转录片段，合并为段落

        Args:
            segments: API 返回的片段列表

        Returns:
            段落列表
        """
        paragraphs = []
        current_para = {
            "start": 0,
            "end": 0,
            "text": ""
        }

        for segment in segments:
            # 如果间隔超过阈值，开始新段落
            if segment['start'] - current_para["end"] > self.paragraph_gap and current_para["text"]:
                paragraphs.append(current_para)
                current_para = {
                    "start": segment['start'],
                    "end": segment['end'],
                    "text": segment['text'].strip()
                }
            else:
                # 合并到当前段落
                if not current_para["text"]:
                    current_para["start"] = segment['start']
                current_para["end"] = segment['end']
                current_para["text"] += segment['text'].strip()

        # 添加最后一个段落
        if current_para["text"]:
            paragraphs.append(current_para)

        return paragraphs

    def save_transcript(self, paragraphs: List[Dict[str, Any]],
                       save_path: str, metadata: dict = None) -> str:
        """
        保存转录结果

        Args:
            paragraphs: 段落列表
            save_path: 保存路径
            metadata: 元数据

        Returns:
            保存的文件路径
        """
        # 确保保存目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # 构建完整数据
        data = {
            "segments": paragraphs,
            "metadata": metadata or {},
            "word_count": sum(len(p["text"]) for p in paragraphs),
            "paragraph_count": len(paragraphs)
        }

        # 保存为 JSON
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"转录结果已保存: {save_path}")
        return save_path

    def format_transcript_text(self, paragraphs: List[Dict[str, Any]]) -> str:
        """
        格式化转录文本为可读格式

        Args:
            paragraphs: 段落列表

        Returns:
            格式化的文本
        """
        lines = []
        for para in paragraphs:
            start_time = self._format_time(para["start"])
            end_time = self._format_time(para["end"])
            lines.append(f"[{start_time} - {end_time}]")
            lines.append(para["text"])
            lines.append("")  # 空行

        return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        """
        格式化时间

        Args:
            seconds: 秒数

        Returns:
            格式化的时间字符串 (HH:MM:SS)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# 使用示例
if __name__ == "__main__":
    # 测试配置
    config = {
        "api_key": "your-api-key-here",  # 替换为实际的 API Key
        "language": "zh"
    }

    transcriber = WhisperAPITranscriber(config)

    # 测试转录
    test_audio = "data/audio/test.m4a"
    try:
        paragraphs = transcriber.transcribe(test_audio)
        print(f"✓ 转录成功: {len(paragraphs)} 个段落")

        # 显示前 3 个段落
        for i, para in enumerate(paragraphs[:3]):
            print(f"\n段落 {i+1}:")
            print(f"  时间: {para['start']:.1f}s - {para['end']:.1f}s")
            print(f"  内容: {para['text'][:100]}...")
    except Exception as e:
        print(f"✗ 转录失败: {e}")
