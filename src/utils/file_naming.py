"""
文件命名工具
处理播客文件的命名和重命名
"""

import re
from pathlib import Path
from typing import Optional
from loguru import logger


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """
    清理文件名，移除非法字符

    Args:
        name: 原始文件名
        max_length: 最大长度

    Returns:
        清理后的文件名
    """
    # 移除非法字符
    illegal_chars = r'[/\\:*?"<>|]'
    clean_name = re.sub(illegal_chars, '_', name)

    # 移除首尾空格
    clean_name = clean_name.strip()

    # 限制长度
    if len(clean_name) > max_length:
        clean_name = clean_name[:max_length]

    # 如果清理后为空，使用默认名称
    if not clean_name:
        clean_name = "未命名"

    return clean_name


def get_podcast_files(podcast_id: str, base_dirs: dict, db=None) -> dict:
    """
    获取播客相关的所有文件路径（支持栏目分类存储）

    Args:
        podcast_id: 播客 ID
        base_dirs: 基础目录配置 {'audio': ..., 'transcript': ..., 'note': ...}
        db: 数据库实例（可选，用于获取更准确的文件路径）

    Returns:
        文件路径字典
    """
    files = {
        'audio': [],
        'transcript': [],
        'note': []
    }

    # 如果提供了数据库，优先从数据库获取文件路径
    if db:
        # 获取播客信息
        podcast = db.get_podcast(podcast_id)

        # 获取音频文件路径（优先从数据库）
        if podcast and podcast.get('audio_file_path'):
            audio_path = Path(podcast['audio_file_path'])
            if audio_path.exists():
                files['audio'].append(audio_path)

        # 如果数据库中没有音频路径，尝试通过标题查找
        if not files['audio'] and podcast:
            audio_dir = Path(base_dirs.get('audio', 'data/audio'))
            title = podcast.get('title', '')

            if title:
                clean_title = sanitize_filename(title)
                for ext in ['.m4a', '.mp3', '.wav', '.flac', '.aac', '.opus']:
                    audio_path = audio_dir / f"{clean_title}{ext}"
                    if audio_path.exists() and audio_path not in files['audio']:
                        files['audio'].append(audio_path)

            # 如果还是找不到，尝试通过 podcast_timestamp 格式查找
            if not files['audio']:
                for ext in ['.m4a', '.mp3', '.wav', '.flac', '.aac', '.opus']:
                    audio_files = list(audio_dir.glob(f"podcast_*{ext}"))
                    # 简单添加所有匹配的文件（可能需要更精确的匹配）
                    for audio_file in audio_files:
                        if audio_file not in files['audio']:
                            files['audio'].append(audio_file)

        # 获取转录文件
        transcripts = db.get_transcripts_by_podcast(podcast_id)
        for transcript in transcripts:
            file_path = Path(transcript['file_path'])
            if file_path.exists():
                files['transcript'].append(file_path)

        # 获取笔记文件
        notes = db.get_notes_by_podcast(podcast_id)
        for note in notes:
            file_path = Path(note['file_path'])
            if file_path.exists():
                files['note'].append(file_path)

    # 如果没有数据库或数据库查找失败，使用文件系统搜索
    if not db or (not files['audio'] and not files['transcript'] and not files['note']):
        # 查找音频文件（递归搜索，支持栏目分类）
        audio_dir = Path(base_dirs.get('audio', 'data/audio'))
        if audio_dir.exists():
            for ext in ['.m4a', '.mp3', '.wav', '.flac', '.aac']:
                # 递归搜索所有子目录
                audio_files = list(audio_dir.rglob(f"*{podcast_id}*{ext}"))
                files['audio'].extend([f for f in audio_files if f not in files['audio']])

        # 查找转录文件（递归搜索，支持栏目分类）
        transcript_dir = Path(base_dirs.get('transcript', 'data/transcripts'))
        if transcript_dir.exists():
            for ext in ['.md', '.pdf', '.json']:
                # 递归搜索所有子目录
                transcript_files = list(transcript_dir.rglob(f"{podcast_id}*{ext}"))
                files['transcript'].extend([f for f in transcript_files if f not in files['transcript']])

        # 查找笔记文件（递归搜索，支持栏目分类）
        note_dir = Path(base_dirs.get('note', 'data/notes'))
        if note_dir.exists():
            # 递归搜索所有子目录
            note_files = list(note_dir.rglob(f"{podcast_id}*.md"))
            files['note'].extend([f for f in note_files if f not in files['note']])

    return files


def rename_podcast_files(podcast_id: str, new_title: str, base_dirs: dict, db=None) -> dict:
    """
    重命名播客相关的所有文件

    Args:
        podcast_id: 播客 ID
        new_title: 新的播客标题
        base_dirs: 基础目录配置
        db: 数据库实例（可选，用于更准确的文件查找）

    Returns:
        重命名结果 {'success': bool, 'renamed': [], 'failed': []}
    """
    result = {
        'success': True,
        'renamed': [],
        'failed': []
    }

    # 清理文件名
    clean_title = sanitize_filename(new_title)

    # 获取所有相关文件（传入数据库以获得更准确的结果）
    files = get_podcast_files(podcast_id, base_dirs, db)

    # 重命名音频文件
    for old_path in files['audio']:
        try:
            ext = old_path.suffix
            new_name = f"{clean_title}{ext}"
            new_path = old_path.parent / new_name

            # 如果目标文件已存在，添加序号
            counter = 1
            while new_path.exists() and new_path != old_path:
                new_name = f"{clean_title}_{counter}{ext}"
                new_path = old_path.parent / new_name
                counter += 1

            if old_path != new_path:
                old_path.rename(new_path)
                result['renamed'].append({
                    'old': str(old_path),
                    'new': str(new_path)
                })
                logger.info(f"重命名音频文件: {old_path.name} -> {new_path.name}")
        except Exception as e:
            logger.error(f"重命名音频文件失败 {old_path}: {e}")
            result['failed'].append(str(old_path))
            result['success'] = False

    # 重命名转录文件
    for old_path in files['transcript']:
        try:
            ext = old_path.suffix
            new_name = f"{clean_title}{ext}"
            new_path = old_path.parent / new_name

            # 如果目标文件已存在，添加序号
            counter = 1
            while new_path.exists() and new_path != old_path:
                new_name = f"{clean_title}_{counter}{ext}"
                new_path = old_path.parent / new_name
                counter += 1

            if old_path != new_path:
                old_path.rename(new_path)
                result['renamed'].append({
                    'old': str(old_path),
                    'new': str(new_path)
                })
                logger.info(f"重命名转录文件: {old_path.name} -> {new_path.name}")
        except Exception as e:
            logger.error(f"重命名转录文件失败 {old_path}: {e}")
            result['failed'].append(str(old_path))
            result['success'] = False

    # 重命名笔记文件
    for old_path in files['note']:
        try:
            # 保留笔记类型后缀 (_auto, _ai, _qwen_ai 等)，并添加"笔记"后缀
            old_name = old_path.stem
            if '_auto' in old_name:
                new_name = f"{clean_title}_auto_笔记.md"
            elif '_qwen_ai' in old_name:
                new_name = f"{clean_title}_qwen_ai_笔记.md"
            elif '_deepseek_ai' in old_name:
                new_name = f"{clean_title}_deepseek_ai_笔记.md"
            elif '_ai' in old_name:
                new_name = f"{clean_title}_ai_笔记.md"
            else:
                new_name = f"{clean_title}_笔记.md"

            new_path = old_path.parent / new_name

            # 如果目标文件已存在，添加序号
            counter = 1
            while new_path.exists() and new_path != old_path:
                base_name = new_name.replace('.md', '')
                new_name = f"{base_name}_{counter}.md"
                new_path = old_path.parent / new_name
                counter += 1

            if old_path != new_path:
                old_path.rename(new_path)
                result['renamed'].append({
                    'old': str(old_path),
                    'new': str(new_path)
                })
                logger.info(f"重命名笔记文件: {old_path.name} -> {new_path.name}")
        except Exception as e:
            logger.error(f"重命名笔记文件失败 {old_path}: {e}")
            result['failed'].append(str(old_path))
            result['success'] = False

    return result


def delete_podcast_files(podcast_id: str, base_dirs: dict, db=None) -> dict:
    """
    删除播客相关的所有文件

    Args:
        podcast_id: 播客 ID
        base_dirs: 基础目录配置
        db: 数据库实例（可选，用于更准确的文件查找）

    Returns:
        删除结果 {'success': bool, 'deleted': [], 'failed': []}
    """
    result = {
        'success': True,
        'deleted': [],
        'failed': []
    }

    # 获取所有相关文件（传入数据库以获得更准确的结果）
    files = get_podcast_files(podcast_id, base_dirs, db)

    # 删除所有文件
    for file_type, file_list in files.items():
        for file_path in file_list:
            try:
                if file_path.exists():
                    file_path.unlink()
                    result['deleted'].append(str(file_path))
                    logger.info(f"删除文件: {file_path}")
            except Exception as e:
                logger.error(f"删除文件失败 {file_path}: {e}")
                result['failed'].append(str(file_path))
                result['success'] = False

    return result
