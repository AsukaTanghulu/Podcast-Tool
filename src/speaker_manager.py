"""
讲话人管理模块
管理播客的讲话人信息和自定义名称
"""

from typing import List, Dict, Optional
from loguru import logger


class SpeakerManager:
    """讲话人管理器"""

    def __init__(self, db):
        """
        初始化讲话人管理器

        Args:
            db: 数据库实例
        """
        self.db = db

    def save_speakers(self, podcast_id: str, speakers: List[str]) -> bool:
        """
        保存播客的讲话人列表

        Args:
            podcast_id: 播客ID
            speakers: 讲话人ID列表，如 ["SPEAKER_00", "SPEAKER_01"]

        Returns:
            是否成功
        """
        try:
            # 先删除旧的讲话人记录
            self.db.conn.execute(
                "DELETE FROM speakers WHERE podcast_id = ?",
                (podcast_id,)
            )

            # 插入新的讲话人记录
            for speaker_id in speakers:
                self.db.conn.execute(
                    """
                    INSERT INTO speakers (podcast_id, speaker_id, speaker_name)
                    VALUES (?, ?, ?)
                    """,
                    (podcast_id, speaker_id, None)
                )

            self.db.conn.commit()
            logger.info(f"保存讲话人列表成功: {podcast_id}, {len(speakers)} 个讲话人")
            return True

        except Exception as e:
            logger.error(f"保存讲话人列表失败: {e}")
            return False

    def update_speaker_name(self, podcast_id: str, speaker_id: str, name: str) -> bool:
        """
        更新讲话人名称

        Args:
            podcast_id: 播客ID
            speaker_id: 讲话人ID（如 "SPEAKER_00"）
            name: 自定义名称

        Returns:
            是否成功
        """
        try:
            self.db.conn.execute(
                """
                UPDATE speakers
                SET speaker_name = ?
                WHERE podcast_id = ? AND speaker_id = ?
                """,
                (name, podcast_id, speaker_id)
            )
            self.db.conn.commit()
            logger.info(f"更新讲话人名称成功: {speaker_id} -> {name}")
            return True

        except Exception as e:
            logger.error(f"更新讲话人名称失败: {e}")
            return False

    def get_speakers(self, podcast_id: str) -> Dict[str, Optional[str]]:
        """
        获取播客的讲话人映射

        Args:
            podcast_id: 播客ID

        Returns:
            讲话人映射字典，格式：{"SPEAKER_00": "张三", "SPEAKER_01": None}
        """
        try:
            cursor = self.db.conn.execute(
                """
                SELECT speaker_id, speaker_name
                FROM speakers
                WHERE podcast_id = ?
                ORDER BY speaker_id
                """,
                (podcast_id,)
            )

            speakers = {}
            for row in cursor.fetchall():
                speakers[row[0]] = row[1]

            return speakers

        except Exception as e:
            logger.error(f"获取讲话人列表失败: {e}")
            return {}

    def get_speaker_display_name(self, podcast_id: str, speaker_id: str) -> str:
        """
        获取讲话人的显示名称

        Args:
            podcast_id: 播客ID
            speaker_id: 讲话人ID

        Returns:
            显示名称（如果有自定义名称则返回自定义名称，否则返回ID）
        """
        speakers = self.get_speakers(podcast_id)
        custom_name = speakers.get(speaker_id)

        if custom_name:
            return custom_name
        else:
            # 返回格式化的默认名称，如 "讲话人1"
            speaker_num = speaker_id.replace("SPEAKER_", "")
            try:
                return f"讲话人{int(speaker_num) + 1}"
            except ValueError:
                return speaker_id

    def has_diarization(self, podcast_id: str) -> bool:
        """
        检查播客是否有讲话人信息

        Args:
            podcast_id: 播客ID

        Returns:
            是否有讲话人信息
        """
        try:
            cursor = self.db.conn.execute(
                "SELECT COUNT(*) FROM speakers WHERE podcast_id = ?",
                (podcast_id,)
            )
            count = cursor.fetchone()[0]
            return count > 0

        except Exception as e:
            logger.error(f"检查讲话人信息失败: {e}")
            return False
