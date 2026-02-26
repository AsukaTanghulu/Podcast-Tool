"""
数据库模块
负责 SQLite 数据库的初始化、表结构创建和基础操作
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str = "data/database.db"):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        # 确保数据库目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._connect()
        self._init_tables()

    def _connect(self):
        """建立数据库连接"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # 返回字典格式
            logger.info(f"数据库连接成功: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def _init_tables(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()

        # 播客记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS podcasts (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                audio_url TEXT,
                duration INTEGER,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                error_message TEXT
            )
        """)

        # 转录记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                podcast_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                word_count INTEGER,
                model_version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
            )
        """)

        # 笔记记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                podcast_id TEXT NOT NULL,
                note_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                model_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
            )
        """)

        # 任务队列表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                podcast_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
            )
        """)

        # 系统配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 讲话人表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS speakers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                podcast_id TEXT NOT NULL,
                speaker_id TEXT NOT NULL,
                speaker_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (podcast_id) REFERENCES podcasts(id) ON DELETE CASCADE
            )
        """)

        # 检查并添加 has_diarization 字段到 transcripts 表
        cursor.execute("PRAGMA table_info(transcripts)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'has_diarization' not in columns:
            cursor.execute("""
                ALTER TABLE transcripts ADD COLUMN has_diarization BOOLEAN DEFAULT 0
            """)
            logger.info("添加 has_diarization 字段到 transcripts 表")

        self.conn.commit()
        logger.info("数据库表初始化完成")

    # ==================== 播客相关操作 ====================

    def create_podcast(self, url: str, title: str = "") -> str:
        """
        创建新的播客记录

        Args:
            url: 播客页面 URL
            title: 播客标题（可选）

        Returns:
            podcast_id: 播客 ID
        """
        podcast_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO podcasts (id, title, url, status)
            VALUES (?, ?, ?, ?)
        """, (podcast_id, title or "未命名播客", url, "pending"))
        self.conn.commit()
        logger.info(f"创建播客记录: {podcast_id}")
        return podcast_id

    def get_podcast(self, podcast_id: str) -> Optional[Dict[str, Any]]:
        """
        获取播客信息

        Args:
            podcast_id: 播客 ID

        Returns:
            播客信息字典，不存在则返回 None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM podcasts WHERE id = ?", (podcast_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_podcast(self, podcast_id: str, **kwargs):
        """
        更新播客信息

        Args:
            podcast_id: 播客 ID
            **kwargs: 要更新的字段
        """
        if not kwargs:
            return

        fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [podcast_id]

        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE podcasts SET {fields} WHERE id = ?", values)
        self.conn.commit()
        logger.debug(f"更新播客 {podcast_id}: {kwargs}")

    def list_podcasts(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取播客列表

        Args:
            limit: 返回数量
            offset: 偏移量

        Returns:
            播客列表
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM podcasts
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]

    def get_all_podcasts(self) -> List[Dict[str, Any]]:
        """
        获取所有播客记录

        Returns:
            播客列表
        """
        return self.list_podcasts(limit=1000)

    def delete_podcast(self, podcast_id: str) -> bool:
        """
        删除播客及其关联的所有记录和文件

        Args:
            podcast_id: 播客 ID

        Returns:
            是否删除成功
        """
        try:
            cursor = self.conn.cursor()

            # 删除转录记录
            cursor.execute("DELETE FROM transcripts WHERE podcast_id = ?", (podcast_id,))

            # 删除笔记记录
            cursor.execute("DELETE FROM notes WHERE podcast_id = ?", (podcast_id,))

            # 删除任务记录
            cursor.execute("DELETE FROM tasks WHERE podcast_id = ?", (podcast_id,))

            # 删除播客记录
            cursor.execute("DELETE FROM podcasts WHERE id = ?", (podcast_id,))

            self.conn.commit()
            logger.info(f"删除播客记录: {podcast_id}")
            return True
        except Exception as e:
            logger.error(f"删除播客失败: {e}")
            self.conn.rollback()
            return False

    def delete_podcasts_batch(self, podcast_ids: List[str]) -> int:
        """
        批量删除播客

        Args:
            podcast_ids: 播客 ID 列表

        Returns:
            成功删除的数量
        """
        count = 0
        for podcast_id in podcast_ids:
            if self.delete_podcast(podcast_id):
                count += 1
        logger.info(f"批量删除播客: {count}/{len(podcast_ids)}")
        return count

    def clear_all_podcasts(self) -> int:
        """
        清空所有播客记录

        Returns:
            删除的播客数量
        """
        try:
            cursor = self.conn.cursor()

            # 获取所有播客 ID
            cursor.execute("SELECT id FROM podcasts")
            podcast_ids = [row[0] for row in cursor.fetchall()]

            # 删除所有记录
            cursor.execute("DELETE FROM transcripts")
            cursor.execute("DELETE FROM notes")
            cursor.execute("DELETE FROM tasks")
            cursor.execute("DELETE FROM podcasts")

            self.conn.commit()
            logger.info(f"清空所有播客: {len(podcast_ids)} 条记录")
            return len(podcast_ids)
        except Exception as e:
            logger.error(f"清空播客失败: {e}")
            self.conn.rollback()
            return 0

    # ==================== 转录相关操作 ====================

    def create_transcript(self, podcast_id: str, file_path: str,
                         word_count: int = 0, model_version: str = "") -> int:
        """
        创建转录记录

        Args:
            podcast_id: 播客 ID
            file_path: 转录文件路径
            word_count: 字数统计
            model_version: 模型版本

        Returns:
            transcript_id: 转录记录 ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO transcripts (podcast_id, file_path, word_count, model_version)
            VALUES (?, ?, ?, ?)
        """, (podcast_id, file_path, word_count, model_version))
        self.conn.commit()
        logger.info(f"创建转录记录: podcast_id={podcast_id}")
        return cursor.lastrowid

    def get_transcript(self, podcast_id: str) -> Optional[Dict[str, Any]]:
        """
        获取播客的转录记录

        Args:
            podcast_id: 播客 ID

        Returns:
            转录记录字典
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM transcripts
            WHERE podcast_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (podcast_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_transcripts_by_podcast(self, podcast_id: str) -> List[Dict[str, Any]]:
        """
        获取播客的所有转录记录

        Args:
            podcast_id: 播客 ID

        Returns:
            转录记录列表
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM transcripts
            WHERE podcast_id = ?
            ORDER BY created_at DESC
        """, (podcast_id,))
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 笔记相关操作 ====================

    def create_note(self, podcast_id: str, note_type: str,
                   file_path: str, model_name: str = "") -> int:
        """
        创建笔记记录

        Args:
            podcast_id: 播客 ID
            note_type: 笔记类型（auto/ai）
            file_path: 笔记文件路径
            model_name: AI 模型名称

        Returns:
            note_id: 笔记记录 ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO notes (podcast_id, note_type, file_path, model_name)
            VALUES (?, ?, ?, ?)
        """, (podcast_id, note_type, file_path, model_name))
        self.conn.commit()
        logger.info(f"创建笔记记录: podcast_id={podcast_id}, type={note_type}")
        return cursor.lastrowid

    def get_notes(self, podcast_id: str) -> List[Dict[str, Any]]:
        """
        获取播客的所有笔记

        Args:
            podcast_id: 播客 ID

        Returns:
            笔记列表
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM notes
            WHERE podcast_id = ?
            ORDER BY created_at DESC
        """, (podcast_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_notes_by_podcast(self, podcast_id: str) -> List[Dict[str, Any]]:
        """
        获取播客的所有笔记（别名方法）

        Args:
            podcast_id: 播客 ID

        Returns:
            笔记列表
        """
        return self.get_notes(podcast_id)

    # ==================== 任务相关操作 ====================

    def create_task(self, podcast_id: str, task_type: str) -> str:
        """
        创建任务记录

        Args:
            podcast_id: 播客 ID
            task_type: 任务类型（download/transcribe/analyze）

        Returns:
            task_id: 任务 ID
        """
        task_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (id, podcast_id, task_type, status)
            VALUES (?, ?, ?, ?)
        """, (task_id, podcast_id, task_type, "pending"))
        self.conn.commit()
        logger.info(f"创建任务: {task_id}, type={task_type}")
        return task_id

    def update_task(self, task_id: str, status: str = None, progress: int = None):
        """
        更新任务状态

        Args:
            task_id: 任务 ID
            status: 任务状态
            progress: 进度百分比
        """
        updates = []
        values = []

        if status:
            updates.append("status = ?")
            values.append(status)
        if progress is not None:
            updates.append("progress = ?")
            values.append(progress)

        if not updates:
            return

        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(task_id)

        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE tasks SET {', '.join(updates)} WHERE id = ?
        """, values)
        self.conn.commit()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息

        Args:
            task_id: 任务 ID

        Returns:
            任务信息字典
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ==================== 配置相关操作 ====================

    def set_setting(self, key: str, value: str):
        """
        设置配置项

        Args:
            key: 配置键
            value: 配置值
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.now().isoformat()))
        self.conn.commit()

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """
        获取配置项

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")


# 全局数据库实例
_db_instance = None


def get_db(db_path: str = "data/database.db") -> Database:
    """
    获取数据库实例（单例模式）

    Args:
        db_path: 数据库文件路径

    Returns:
        Database 实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance
