"""
语音识别模块
负责使用 faster-whisper 将音频转录为文本
"""

import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from faster_whisper import WhisperModel
from loguru import logger


class TranscriptionError(Exception):
    """转录异常"""
    pass


class Transcriber:
    """语音识别器"""

    def __init__(self, config: dict = None):
        """
        初始化语音识别器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.model_size = self.config.get("model_size", "medium")
        self.device = self.config.get("device", "cpu")
        self.compute_type = self.config.get("compute_type", "int8")
        self.language = self.config.get("language", "zh")
        self.beam_size = self.config.get("beam_size", 5)
        self.vad_filter = self.config.get("vad_filter", True)
        self.paragraph_gap = self.config.get("paragraph_gap", 2.0)

        self.model = None
        self._load_model()

    def _load_model(self):
        """加载 Whisper 模型"""
        logger.info(f"正在加载 Whisper 模型: {self.model_size}")

        try:
            # 尝试使用 float32 compute_type 避免 int8 在某些 CPU 上的兼容性问题
            compute_type_to_try = "float32" if self.compute_type == "int8" else self.compute_type

            logger.info(f"使用 compute_type: {compute_type_to_try}")

            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=compute_type_to_try,
                download_root="models",  # 模型下载目录
                num_workers=1  # 减少并发以避免内存问题
            )
            logger.info("Whisper 模型加载成功")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise TranscriptionError(f"模型加载失败: {e}")

    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径

        Returns:
            段落列表，每个段落包含 start, end, text

        Raises:
            TranscriptionError: 转录失败
        """
        logger.info(f"开始转录音频: {audio_path}")
        start_time = time.time()

        try:
            # 执行转录
            segments, info = self.model.transcribe(
                audio_path,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            logger.info(f"检测到语言: {info.language}, 概率: {info.language_probability:.2f}")

            # 处理片段
            paragraphs = self._process_segments(segments)

            elapsed_time = time.time() - start_time
            total_duration = paragraphs[-1]["end"] if paragraphs else 0
            logger.info(
                f"转录完成: {len(paragraphs)} 个段落, "
                f"音频时长 {total_duration:.1f}s, "
                f"耗时 {elapsed_time:.1f}s"
            )

            return paragraphs

        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise TranscriptionError(f"转录失败: {e}")

    def _process_segments(self, segments) -> List[Dict[str, Any]]:
        """
        处理转录片段，合并为段落

        Args:
            segments: Whisper 输出的片段迭代器

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
            if segment.start - current_para["end"] > self.paragraph_gap and current_para["text"]:
                paragraphs.append(current_para)
                current_para = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                }
            else:
                # 合并到当前段落
                if not current_para["text"]:
                    current_para["start"] = segment.start
                current_para["end"] = segment.end
                current_para["text"] += segment.text.strip()

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


def transcribe_with_retry(audio_path: str, config: dict = None,
                          max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    带重试的转录

    Args:
        audio_path: 音频文件路径
        config: 配置字典
        max_retries: 最大重试次数

    Returns:
        段落列表

    Raises:
        TranscriptionError: 转录失败
    """
    transcriber = Transcriber(config)

    for attempt in range(max_retries):
        try:
            result = transcriber.transcribe(audio_path)

            # 验证结果
            if not result or len(result) == 0:
                raise TranscriptionError("转录结果为空")

            return result

        except Exception as e:
            logger.warning(f"转录失败（尝试 {attempt + 1}/{max_retries}）: {e}")
            if attempt == max_retries - 1:
                raise TranscriptionError(
                    f"转录失败（已重试 {max_retries} 次）: {e}"
                )
            else:
                time.sleep(2 ** attempt)  # 指数退避


def test_transcriber():
    """测试转录器"""
    # 测试配置
    config = {
        "model_size": "base",  # 使用 base 模型测试更快
        "device": "cpu",
        "compute_type": "int8",
        "language": "zh"
    }

    transcriber = Transcriber(config)

    # 测试用例（需要替换为真实的音频文件）
    test_audio = "data/audio/test.m4a"

    try:
        paragraphs = transcriber.transcribe(test_audio)
        print(f"✓ 转录成功: {len(paragraphs)} 个段落")

        # 显示前 3 个段落
        for i, para in enumerate(paragraphs[:3]):
            print(f"\n段落 {i+1}:")
            print(f"  时间: {para['start']:.1f}s - {para['end']:.1f}s")
            print(f"  内容: {para['text'][:100]}...")

        # 保存结果
        save_path = "data/transcripts/test.json"
        transcriber.save_transcript(paragraphs, save_path)
        print(f"\n✓ 转录结果已保存: {save_path}")

        # 格式化文本
        formatted = transcriber.format_transcript_text(paragraphs[:3])
        print(f"\n格式化文本:\n{formatted}")

    except Exception as e:
        print(f"✗ 转录失败: {e}")


if __name__ == "__main__":
    test_transcriber()
