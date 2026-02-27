"""
文件上传处理模块
支持音频和视频文件的上传和验证
"""

from pathlib import Path
from typing import Tuple, Optional
from loguru import logger
import mimetypes


class FileUploader:
    """文件上传处理器"""

    # Qwen API 支持的音频格式
    SUPPORTED_AUDIO_FORMATS = {
        '.mp3', '.wav', '.m4a', '.flac', '.aac', '.opus'
    }

    # Qwen API 支持的视频格式
    SUPPORTED_VIDEO_FORMATS = {
        '.mp4', '.flv', '.webm', '.mkv', '.avi', '.mov'
    }

    # 文件大小限制（2GB）
    MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB in bytes

    def __init__(self, upload_dir: str = "data/uploads"):
        """
        初始化文件上传器

        Args:
            upload_dir: 上传文件保存目录
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        验证文件格式和大小

        Args:
            filename: 文件名
            file_size: 文件大小（字节）

        Returns:
            (是否有效, 错误信息)
        """
        file_ext = Path(filename).suffix.lower()

        # 检查文件格式
        if file_ext not in self.SUPPORTED_AUDIO_FORMATS and file_ext not in self.SUPPORTED_VIDEO_FORMATS:
            supported = ', '.join(sorted(self.SUPPORTED_AUDIO_FORMATS | self.SUPPORTED_VIDEO_FORMATS))
            return False, f"不支持的文件格式 {file_ext}。支持的格式: {supported}"

        # 检查文件大小
        if file_size > self.MAX_FILE_SIZE:
            max_size_gb = self.MAX_FILE_SIZE / (1024 * 1024 * 1024)
            actual_size_gb = file_size / (1024 * 1024 * 1024)
            return False, f"文件过大 ({actual_size_gb:.2f}GB)，最大支持 {max_size_gb:.0f}GB"

        return True, None

    def save_file(self, file_obj, filename: str, podcast_id: str) -> Path:
        """
        保存上传的文件

        Args:
            file_obj: 文件对象（Flask request.files）
            filename: 原始文件名
            podcast_id: 播客/纪录片 ID

        Returns:
            保存后的文件路径
        """
        # 清理文件名，保留扩展名
        file_ext = Path(filename).suffix.lower()
        safe_filename = f"{podcast_id}{file_ext}"

        # 保存文件
        file_path = self.upload_dir / safe_filename
        file_obj.save(str(file_path))

        logger.info(f"文件已保存: {file_path}")
        return file_path

    def get_file_type(self, filename: str) -> str:
        """
        获取文件类型（音频或视频）

        Args:
            filename: 文件名

        Returns:
            'audio' 或 'video'
        """
        file_ext = Path(filename).suffix.lower()
        if file_ext in self.SUPPORTED_AUDIO_FORMATS:
            return 'audio'
        elif file_ext in self.SUPPORTED_VIDEO_FORMATS:
            return 'video'
        else:
            return 'unknown'

    def get_mime_type(self, filename: str) -> str:
        """
        获取文件的 MIME 类型

        Args:
            filename: 文件名

        Returns:
            MIME 类型字符串
        """
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'
