"""
转录文件加载工具
用于从 Markdown 格式的转录文件中加载段落数据
"""

import json
import re
from pathlib import Path
from typing import List, Dict


def load_transcript(transcript_path: str) -> List[Dict]:
    """
    加载转录结果

    Args:
        transcript_path: 转录文件路径（Markdown 格式）

    Returns:
        段落列表，每个段落包含 start, end, text 字段
        [
            {
                'start': 0,      # 开始时间（秒）
                'end': 15,       # 结束时间（秒）
                'text': '...'    # 段落文本
            },
            ...
        ]
    """
    path = Path(transcript_path)

    # 1) 优先支持 JSON（当前主流程保存的是 JSON 转录）
    if path.suffix.lower() == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        paragraphs = []
        for segment in data.get('segments', []):
            text = str(segment.get('text', '')).strip()
            if not text:
                continue

            try:
                start = float(segment.get('start', 0))
            except Exception:
                start = 0.0

            try:
                end = float(segment.get('end', 0))
            except Exception:
                end = start

            paragraphs.append({
                'start': start,
                'end': end,
                'text': text
            })

        return paragraphs

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    paragraphs: List[Dict] = []

    # 2) 兼容旧版 Markdown 格式
    # 格式: ## 段落 1 [00:00:00 - 00:00:15]\n- ...
    legacy_pattern = r'## 段落 \d+ \[(\d{2}):(\d{2}):(\d{2}) - (\d{2}):(\d{2}):(\d{2})\]\n((?:- .+\n)+)'
    legacy_matches = re.findall(legacy_pattern, content)

    for match in legacy_matches:
        start_h, start_m, start_s = int(match[0]), int(match[1]), int(match[2])
        end_h, end_m, end_s = int(match[3]), int(match[4]), int(match[5])
        text_lines = match[6]

        start = start_h * 3600 + start_m * 60 + start_s
        end = end_h * 3600 + end_m * 60 + end_s

        text = '\n'.join([line.strip('- ').strip() for line in text_lines.split('\n') if line.strip()])
        if not text:
            continue

        paragraphs.append({
            'start': start,
            'end': end,
            'text': text
        })

    if paragraphs:
        return paragraphs

    # 3) 兼容新版 Markdown 对话式格式
    # **[00:00:05 - 00:00:12] 说话人**\n> 文本
    dialogue_pattern = re.compile(
        r'\*\*\[(\d{2}):(\d{2}):(\d{2}) - (\d{2}):(\d{2}):(\d{2})\]\s*.+?\*\*\s*\n>\s*(.+?)(?=\n\n\*\*\[|\Z)',
        re.S,
    )
    dialogue_matches = dialogue_pattern.findall(content)

    for match in dialogue_matches:
        start_h, start_m, start_s = int(match[0]), int(match[1]), int(match[2])
        end_h, end_m, end_s = int(match[3]), int(match[4]), int(match[5])
        text = re.sub(r'\n>\s*', '\n', match[6]).strip()
        if not text:
            continue

        start = start_h * 3600 + start_m * 60 + start_s
        end = end_h * 3600 + end_m * 60 + end_s

        paragraphs.append({
            'start': start,
            'end': end,
            'text': text
        })

    return paragraphs
