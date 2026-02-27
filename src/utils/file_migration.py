"""
文件迁移工具
处理播客文件在不同栏目间的迁移
"""

from pathlib import Path
from typing import Optional, Dict, List
from loguru import logger
import shutil


def move_podcast_files_to_category(
    podcast_id: str,
    old_category: Optional[str],
    new_category: str,
    base_dirs: dict,
    db
) -> Dict[str, any]:
    """
    将播客的所有文件迁移到新的栏目文件夹

    Args:
        podcast_id: 播客 ID
        old_category: 旧栏目（None 或空字符串表示"未分类"）
        new_category: 新栏目
        base_dirs: 基础目录配置
        db: 数据库实例

    Returns:
        迁移结果 {'success': bool, 'moved': [], 'failed': []}
    """
    result = {
        'success': True,
        'moved': [],
        'failed': []
    }

    # 标准化栏目名称
    old_category = old_category or '未分类'
    new_category = new_category or '未分类'

    # 如果栏目没变，不需要迁移
    if old_category == new_category:
        logger.info(f"栏目未变化，无需迁移: {old_category}")
        return result

    logger.info(f"开始迁移文件: {old_category} -> {new_category}")

    # 1. 迁移音频文件
    audio_moved = _move_audio_files(podcast_id, old_category, new_category, base_dirs, db)
    result['moved'].extend(audio_moved['moved'])
    result['failed'].extend(audio_moved['failed'])
    if not audio_moved['success']:
        result['success'] = False

    # 2. 迁移转录文件
    transcript_moved = _move_transcript_files(podcast_id, old_category, new_category, base_dirs, db)
    result['moved'].extend(transcript_moved['moved'])
    result['failed'].extend(transcript_moved['failed'])
    if not transcript_moved['success']:
        result['success'] = False

    # 3. 迁移笔记文件
    note_moved = _move_note_files(podcast_id, old_category, new_category, base_dirs, db)
    result['moved'].extend(note_moved['moved'])
    result['failed'].extend(note_moved['failed'])
    if not note_moved['success']:
        result['success'] = False

    logger.info(f"文件迁移完成: 成功 {len(result['moved'])} 个, 失败 {len(result['failed'])} 个")

    return result


def _move_audio_files(podcast_id: str, old_category: str, new_category: str, base_dirs: dict, db) -> dict:
    """迁移音频文件（音频文件不按栏目分类，所以这个函数实际上不需要迁移）"""
    result = {'success': True, 'moved': [], 'failed': []}

    # 音频文件不按栏目分类，所以不需要迁移
    logger.info("音频文件不按栏目分类，跳过迁移")

    return result


def _move_transcript_files(podcast_id: str, old_category: str, new_category: str, base_dirs: dict, db) -> dict:
    """迁移转录文件"""
    result = {'success': True, 'moved': [], 'failed': []}

    transcript_dir = Path(base_dirs.get('transcript', 'data/transcripts'))

    # 从数据库获取转录记录
    transcripts = db.get_transcripts_by_podcast(podcast_id)

    for transcript in transcripts:
        old_path = Path(transcript['file_path'])

        if not old_path.exists():
            logger.warning(f"转录文件不存在: {old_path}")
            continue

        try:
            # 确定文件格式（md 或 pdf）
            file_format = old_path.suffix[1:]  # 去掉点号

            # 创建新目录
            new_dir = transcript_dir / new_category / file_format
            new_dir.mkdir(parents=True, exist_ok=True)

            # 新文件路径
            new_path = new_dir / old_path.name

            # 如果目标文件已存在，添加序号
            counter = 1
            while new_path.exists():
                stem = old_path.stem
                ext = old_path.suffix
                new_path = new_dir / f"{stem}_{counter}{ext}"
                counter += 1

            # 移动文件
            shutil.move(str(old_path), str(new_path))

            # 更新数据库中的文件路径
            cursor = db.conn.cursor()
            cursor.execute(
                "UPDATE transcripts SET file_path = ? WHERE id = ?",
                (str(new_path), transcript['id'])
            )
            db.conn.commit()

            result['moved'].append({
                'old': str(old_path),
                'new': str(new_path),
                'type': 'transcript'
            })
            logger.info(f"迁移转录文件: {old_path.name} -> {new_category}/{file_format}/")

        except Exception as e:
            logger.error(f"迁移转录文件失败 {old_path}: {e}")
            result['failed'].append(str(old_path))
            result['success'] = False

    return result


def _move_note_files(podcast_id: str, old_category: str, new_category: str, base_dirs: dict, db) -> dict:
    """迁移笔记文件"""
    result = {'success': True, 'moved': [], 'failed': []}

    note_dir = Path(base_dirs.get('note', 'data/notes'))

    # 从数据库获取笔记记录
    notes = db.get_notes_by_podcast(podcast_id)

    for note in notes:
        old_path = Path(note['file_path'])

        if not old_path.exists():
            logger.warning(f"笔记文件不存在: {old_path}")
            continue

        try:
            # 确定文件格式（通常是 md）
            file_format = old_path.suffix[1:]

            # 创建新目录
            new_dir = note_dir / new_category / file_format
            new_dir.mkdir(parents=True, exist_ok=True)

            # 新文件路径
            new_path = new_dir / old_path.name

            # 如果目标文件已存在，添加序号
            counter = 1
            while new_path.exists():
                stem = old_path.stem
                ext = old_path.suffix
                new_path = new_dir / f"{stem}_{counter}{ext}"
                counter += 1

            # 移动文件
            shutil.move(str(old_path), str(new_path))

            # 更新数据库中的文件路径
            cursor = db.conn.cursor()
            cursor.execute(
                "UPDATE notes SET file_path = ? WHERE id = ?",
                (str(new_path), note['id'])
            )
            db.conn.commit()

            result['moved'].append({
                'old': str(old_path),
                'new': str(new_path),
                'type': 'note'
            })
            logger.info(f"迁移笔记文件: {old_path.name} -> {new_category}/{file_format}/")

        except Exception as e:
            logger.error(f"迁移笔记文件失败 {old_path}: {e}")
            result['failed'].append(str(old_path))
            result['success'] = False

    return result
