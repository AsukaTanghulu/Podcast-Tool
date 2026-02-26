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


def get_podcast_files(podcast_id: str, base_dirs: dict) -> dict:
    """
    获取播客相关的所有文件路径

    Args:
        podcast_id: 播客 ID
        base_dirs: 基础目录配置 {'audio': ..., 'transcript': ..., 'note': ...}

    Returns:
        文件路径字典
    """
    files = {
        'audio': [],
        'transcript': [],
        'note': []
    }

    # 查找音频文件
    audio_dir = Path(base_dirs.get('audio', 'data/audio'))
    if audio_dir.exists():
        for ext in ['.m4a', '.mp3', '.wav']:
            audio_files = list(audio_dir.glob(f"*{podcast_id}*{ext}"))
            files['audio'].extend(audio_files)

    # 查找转录文件
    transcript_dir = Path(base_dirs.get('transcript', 'data/transcripts'))
    if transcript_dir.exists():
        for ext in ['.md', '.pdf', '.json']:
            transcript_files = list(transcript_dir.glob(f"{podcast_id}*{ext}"))
            files['transcript'].extend(transcript_files)

    # 查找笔记文件
    note_dir = Path(base_dirs.get('note', 'data/notes'))
    if note_dir.exists():
        note_files = list(note_dir.glob(f"{podcast_id}*.md"))
        files['note'].extend(note_files)

    return files


def rename_podcast_files(podcast_id: str, new_title: str, base_dirs: dict) -> dict:
    """
    重命名播客相关的所有文件

    Args:
        podcast_id: 播客 ID
        new_title: 新的播客标题
        base_dirs: 基础目录配置

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

    # 获取所有相关文件
    files = get_podcast_files(podcast_id, base_dirs)

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
                logger.info(f"重命名文件: {old_path.name} -> {new_path.name}")
        except Exception as e:
            logger.error(f"重命名文件失败 {old_path}: {e}")
            result['failed'].append(str(old_path))
            result['success'] = False

    # 重命名笔记文件
    for old_path in files['note']:
        try:
            # 保留笔记类型后缀 (_auto, _ai, _qwen_ai 等)
            old_name = old_path.stem
            if '_auto' in old_name:
                new_name = f"{clean_title}_auto.md"
            elif '_qwen_ai' in old_name:
                new_name = f"{clean_title}_qwen_ai.md"
            elif '_deepseek_ai' in old_name:
                new_name = f"{clean_title}_deepseek_ai.md"
            elif '_ai' in old_name:
                new_name = f"{clean_title}_ai.md"
            else:
                new_name = f"{clean_title}.md"

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
                logger.info(f"重命名文件: {old_path.name} -> {new_path.name}")
        except Exception as e:
            logger.error(f"重命名文件失败 {old_path}: {e}")
            result['failed'].append(str(old_path))
            result['success'] = False

    return result


def delete_podcast_files(podcast_id: str, base_dirs: dict) -> dict:
    """
    删除播客相关的所有文件

    Args:
        podcast_id: 播客 ID
        base_dirs: 基础目录配置

    Returns:
        删除结果 {'success': bool, 'deleted': [], 'failed': []}
    """
    result = {
        'success': True,
        'deleted': [],
        'failed': []
    }

    # 获取所有相关文件
    files = get_podcast_files(podcast_id, base_dirs)

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
