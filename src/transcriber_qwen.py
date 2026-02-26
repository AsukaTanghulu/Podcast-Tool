"""
语音识别模块 - 通义千问 API 版本
使用阿里云通义千问语音识别服务
"""

import time
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
import dashscope
from http import HTTPStatus


class TranscriptionError(Exception):
    """转录异常"""
    pass


class QwenTranscriber:
    """通义千问转录器"""

    def __init__(self, config: dict = None):
        """
        初始化转录器

        Args:
            config: 配置字典，需包含 api_key
        """
        self.config = config or {}
        self.api_key = self.config.get("api_key") or os.getenv("DASHSCOPE_API_KEY")
        self.language = self.config.get("language", "zh")
        self.paragraph_gap = self.config.get("paragraph_gap", 2.0)

        if not self.api_key:
            raise TranscriptionError(
                "未提供 API Key，请在配置中设置 api_key 或环境变量 DASHSCOPE_API_KEY"
            )

        # 设置 API Key
        dashscope.api_key = self.api_key
        logger.info(f"通义千问转录器初始化成功")

    def transcribe(self, audio_path: str, audio_url: str = None) -> List[Dict[str, Any]]:
        """
        使用通义千问 API 转录音频文件

        Args:
            audio_path: 音频文件路径（本地）
            audio_url: 音频文件的 HTTP/HTTPS URL（优先使用）

        Returns:
            段落列表，每个段落包含 start, end, text

        Raises:
            TranscriptionError: 转录失败
        """
        logger.info(f"开始使用通义千问 API 转录音频: {audio_path}")
        start_time = time.time()

        try:
            # 使用通义千问的语音识别 API
            logger.info("正在调用通义千问语音识别 API...")

            from dashscope.audio.asr import Transcription

            # 优先使用 HTTP URL，因为通义千问 API 需要可访问的 URL
            if audio_url and audio_url.strip():
                logger.info(f"使用音频 URL: {audio_url}")
                file_urls = [audio_url]
            else:
                # 如果没有 URL，抛出错误
                error_msg = "通义千问 API 需要音频文件的 HTTP/HTTPS URL，无法使用本地文件路径"
                logger.error(error_msg)
                raise TranscriptionError(error_msg)

            # 提交异步转录任务
            task_response = Transcription.async_call(
                model='paraformer-v2',
                file_urls=file_urls,
                language_hints=['zh']
            )

            if task_response.status_code != HTTPStatus.OK:
                error_msg = f"API 请求失败: {task_response.status_code} - {task_response.message}"
                logger.error(error_msg)
                raise TranscriptionError(error_msg)

            # 获取任务 ID
            task_id = task_response.output['task_id']
            logger.info(f"转录任务已提交，任务 ID: {task_id}")

            # 轮询任务状态
            logger.info("等待转录完成...")
            transcription_response = Transcription.wait(task=task_id)

            if transcription_response.status_code != HTTPStatus.OK:
                error_msg = f"转录失败: {transcription_response.status_code} - {transcription_response.message}"
                logger.error(error_msg)
                raise TranscriptionError(error_msg)

            # 解析结果
            logger.info(f"API 响应: {transcription_response.output}")

            if not transcription_response.output:
                raise TranscriptionError("API 返回结果为空")

            # 检查是否有转录结果 URL
            if 'results' in transcription_response.output:
                results = transcription_response.output['results']
                if results and len(results) > 0:
                    result = results[0]

                    # 如果有 transcription_url，需要下载
                    if 'transcription_url' in result:
                        transcription_url = result['transcription_url']
                        logger.info(f"下载转录结果: {transcription_url}")

                        import requests
                        response = requests.get(transcription_url)
                        transcription_data = response.json()

                        # 处理转录数据
                        paragraphs = self._process_transcription_data(transcription_data)
                    elif 'sentences' in result:
                        # 直接包含句子数据
                        paragraphs = self._process_sentences(result['sentences'])
                    else:
                        logger.warning(f"未知的结果格式: {result}")
                        paragraphs = []
                else:
                    paragraphs = []
            else:
                paragraphs = []

            elapsed_time = time.time() - start_time
            logger.info(
                f"通义千问转录完成: {len(paragraphs)} 个段落, "
                f"耗时 {elapsed_time:.1f}s"
            )

            return paragraphs

        except Exception as e:
            logger.error(f"转录失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise TranscriptionError(f"转录失败: {e}")

    def _process_transcription_data(self, data: Dict) -> List[Dict[str, Any]]:
        """
        处理从 URL 下载的转录数据

        Args:
            data: 转录数据

        Returns:
            段落列表
        """
        paragraphs = []

        # 尝试不同的数据格式
        if 'transcripts' in data:
            for transcript in data['transcripts']:
                if 'sentences' in transcript:
                    paragraphs.extend(self._process_sentences(transcript['sentences']))
        elif 'sentences' in data:
            paragraphs = self._process_sentences(data['sentences'])

        return paragraphs

    def _process_sentences(self, sentences: List[Dict]) -> List[Dict[str, Any]]:
        """
        处理句子列表

        Args:
            sentences: 句子列表

        Returns:
            段落列表
        """
        paragraphs = []
        current_para = {
            "start": 0,
            "end": 0,
            "text": ""
        }

        for sentence in sentences:
            text = sentence.get('text', '').strip()
            if not text:
                continue

            # 转换时间单位：毫秒 -> 秒
            start = sentence.get('begin_time', 0) / 1000.0
            end = sentence.get('end_time', 0) / 1000.0

            # 如果间隔超过阈值，开始新段落
            if start - current_para["end"] > self.paragraph_gap and current_para["text"]:
                paragraphs.append(current_para)
                current_para = {
                    "start": start,
                    "end": end,
                    "text": text
                }
            else:
                # 合并到当前段落
                if not current_para["text"]:
                    current_para["start"] = start
                current_para["end"] = end
                current_para["text"] += text

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
