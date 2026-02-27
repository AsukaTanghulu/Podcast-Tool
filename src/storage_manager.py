"""
文件路径管理工具
负责根据栏目和文件类型生成正确的存储路径
"""

from pathlib import Path
from typing import Optional


class StorageManager:
    """存储路径管理器"""

    def __init__(self, config: dict):
        """
        初始化存储管理器

        Args:
            config: 配置字典
        """
        self.config = config
        self.base_dir = Path(config.get("storage.base_dir", "data"))
        self.audio_dir = Path(config.get("storage.audio_dir", "data/audio"))
        self.transcript_dir = Path(config.get("storage.transcript_dir", "data/transcripts"))
        self.note_dir = Path(config.get("storage.note_dir", "data/notes"))

        self.category_based = config.get("storage.category_based", True)
        self.default_category = config.get("storage.default_category", "未分类")
        self.separate_formats = config.get("storage.separate_formats", True)

    def get_audio_path(self, podcast_id: str, category: Optional[str] = None) -> Path:
        """
        获取音频文件路径

        Args:
            podcast_id: 播客 ID
            category: 栏目名称

        Returns:
            音频文件路径
        """
        if self.category_based and category:
            category = category or self.default_category
            return self.audio_dir / self._sanitize_category(category) / f"{podcast_id}.mp3"
        else:
            return self.audio_dir / f"{podcast_id}.mp3"

    def get_transcript_path(self, podcast_id: str, category: Optional[str] = None,
                           format_type: str = "md") -> Path:
        """
        获取转录文件路径

        Args:
            podcast_id: 播客 ID
            category: 栏目名称
            format_type: 文件格式 (md, pdf, json)

        Returns:
            转录文件路径
        """
        category = category or self.default_category

        if self.category_based:
            category_dir = self._sanitize_category(category)
            if self.separate_formats:
                # data/transcripts/{category}/{format}/
                return self.transcript_dir / category_dir / format_type / f"{podcast_id}.{format_type}"
            else:
                # data/transcripts/{category}/
                return self.transcript_dir / category_dir / f"{podcast_id}.{format_type}"
        else:
            return self.transcript_dir / f"{podcast_id}.{format_type}"

    def get_note_path(self, podcast_id: str, note_type: str,
                     category: Optional[str] = None, format_type: str = "md") -> Path:
        """
        获取笔记文件路径

        Args:
            podcast_id: 播客 ID
            note_type: 笔记类型 (auto, ai)
            category: 栏目名称
            format_type: 文件格式 (md, pdf)

        Returns:
            笔记文件路径
        """
        category = category or self.default_category
        filename = f"{podcast_id}_{note_type}.{format_type}"

        if self.category_based:
            category_dir = self._sanitize_category(category)
            if self.separate_formats:
                # data/notes/{category}/{format}/
                return self.note_dir / category_dir / format_type / filename
            else:
                # data/notes/{category}/
                return self.note_dir / category_dir / filename
        else:
            return self.note_dir / filename

    def ensure_directory(self, file_path: Path) -> None:
        """
        确保文件所在目录存在

        Args:
            file_path: 文件路径
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)

    def _sanitize_category(self, category: str) -> str:
        """
        清理栏目名称，移除不安全的字符

        Args:
            category: 栏目名称

        Returns:
            清理后的栏目名称
        """
        if not category or category.strip() == "":
            return self.default_category

        # 移除不安全的文件名字符
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        sanitized = category
        for char in unsafe_chars:
            sanitized = sanitized.replace(char, '_')

        return sanitized.strip()

    def get_category_dir(self, category: Optional[str] = None) -> Path:
        """
        获取栏目目录路径

        Args:
            category: 栏目名称

        Returns:
            栏目目录路径
        """
        category = category or self.default_category
        return self.base_dir / self._sanitize_category(category)

    def list_categories(self) -> list:
        """
        列出所有栏目

        Returns:
            栏目列表
        """
        categories = set()

        # 从各个目录中提取栏目
        for base_dir in [self.audio_dir, self.transcript_dir, self.note_dir]:
            if base_dir.exists():
                for item in base_dir.iterdir():
                    if item.is_dir():
                        categories.add(item.name)

        return sorted(list(categories))
