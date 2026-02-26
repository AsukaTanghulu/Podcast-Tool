"""
讲话人分离模块
使用 pyannote.audio 进行讲话人识别（Speaker Diarization）
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    logger.warning("未安装 pyannote.audio，讲话人识别功能不可用。安装方法: pip install pyannote.audio torch torchaudio")


class DiarizationError(Exception):
    """讲话人分离异常"""
    pass


class SpeakerDiarizer:
    """讲话人分离器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化讲话人分离器

        Args:
            config: 配置字典，包含 hf_token, model 等

        Raises:
            DiarizationError: 初始化失败
        """
        if not PYANNOTE_AVAILABLE:
            raise DiarizationError("pyannote.audio 未安装")

        self.config = config
        self.hf_token = config.get('hf_token')
        self.model_name = config.get('model', 'pyannote/speaker-diarization-3.1')
        self.min_speakers = config.get('min_speakers', 1)
        self.max_speakers = config.get('max_speakers', 10)

        if not self.hf_token:
            raise DiarizationError("未配置 HuggingFace token")

        self.pipeline = None
        self._load_pipeline()

    def _load_pipeline(self):
        """加载 pyannote.audio pipeline"""
        logger.info(f"正在加载讲话人分离模型: {self.model_name}")

        try:
            self.pipeline = Pipeline.from_pretrained(
                self.model_name,
                use_auth_token=self.hf_token
            )
            logger.info("讲话人分离模型加载成功")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise DiarizationError(f"模型加载失败: {e}")

    def diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        对音频进行讲话人分离

        Args:
            audio_path: 音频文件路径

        Returns:
            讲话人片段列表，格式：
            [
                {"start": 0.0, "end": 5.2, "speaker": "SPEAKER_00"},
                {"start": 5.2, "end": 10.5, "speaker": "SPEAKER_01"},
                ...
            ]

        Raises:
            DiarizationError: 分离失败
        """
        logger.info(f"开始讲话人分离: {audio_path}")
        start_time = time.time()

        try:
            # 执行讲话人分离
            diarization = self.pipeline(
                audio_path,
                min_speakers=self.min_speakers,
                max_speakers=self.max_speakers
            )

            # 转换为列表格式
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    'start': turn.start,
                    'end': turn.end,
                    'speaker': speaker
                })

            elapsed_time = time.time() - start_time
            speaker_count = len(set(seg['speaker'] for seg in segments))

            logger.info(
                f"讲话人分离完成: {len(segments)} 个片段, "
                f"{speaker_count} 个讲话人, "
                f"耗时 {elapsed_time:.1f}s"
            )

            return segments

        except Exception as e:
            logger.error(f"讲话人分离失败: {e}")
            raise DiarizationError(f"讲话人分离失败: {e}")

    def merge_with_transcript(self,
                             transcript: List[Dict[str, Any]],
                             diarization: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将讲话人信息合并到转录结果中

        Args:
            transcript: 转录结果列表，格式：[{"start": 0.0, "end": 5.2, "text": "..."}]
            diarization: 讲话人分离结果

        Returns:
            合并后的结果，格式：[{"start": 0.0, "end": 5.2, "text": "...", "speaker": "SPEAKER_00"}]
        """
        logger.info("合并转录和讲话人信息")

        merged = []
        for trans_seg in transcript:
            # 找到与转录片段重叠最多的讲话人片段
            best_speaker = self._find_best_speaker(trans_seg, diarization)

            merged.append({
                'start': trans_seg['start'],
                'end': trans_seg['end'],
                'text': trans_seg['text'],
                'speaker': best_speaker
            })

        logger.info(f"合并完成: {len(merged)} 个片段")
        return merged

    def _find_best_speaker(self,
                          trans_seg: Dict[str, Any],
                          diarization: List[Dict[str, Any]]) -> str:
        """
        找到与转录片段重叠最多的讲话人

        Args:
            trans_seg: 转录片段
            diarization: 讲话人分离结果

        Returns:
            讲话人标识（如 "SPEAKER_00"）
        """
        trans_start = trans_seg['start']
        trans_end = trans_seg['end']

        max_overlap = 0
        best_speaker = "UNKNOWN"

        for dia_seg in diarization:
            # 计算重叠时间
            overlap_start = max(trans_start, dia_seg['start'])
            overlap_end = min(trans_end, dia_seg['end'])
            overlap = max(0, overlap_end - overlap_start)

            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = dia_seg['speaker']

        return best_speaker

    def get_speaker_list(self, diarization: List[Dict[str, Any]]) -> List[str]:
        """
        获取所有讲话人列表

        Args:
            diarization: 讲话人分离结果

        Returns:
            讲话人列表，如 ["SPEAKER_00", "SPEAKER_01"]
        """
        speakers = set(seg['speaker'] for seg in diarization)
        return sorted(list(speakers))
