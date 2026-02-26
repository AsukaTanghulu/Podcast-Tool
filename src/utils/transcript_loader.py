"""
转录文件加载工具
用于从 Markdown 格式的转录文件中加载段落数据
"""

import re
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
    with open(transcript_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析 Markdown 格式的转录文件
    paragraphs = []

    # 匹配段落标题和内容
    # 格式: ## 段落 1 [00:00:00 - 00:00:15]
    pattern = r'## 段落 \d+ \[(\d{2}):(\d{2}):(\d{2}) - (\d{2}):(\d{2}):(\d{2})\]\n((?:- .+\n)+)'

    matches = re.findall(pattern, content)

    for match in matches:
        start_h, start_m, start_s = int(match[0]), int(match[1]), int(match[2])
        end_h, end_m, end_s = int(match[3]), int(match[4]), int(match[5])
        text_lines = match[6]

        # 计算时间戳（秒）
        start = start_h * 3600 + start_m * 60 + start_s
        end = end_h * 3600 + end_m * 60 + end_s

        # 提取文本（移除 bullet points）
        text = '\n'.join([line.strip('- ').strip() for line in text_lines.split('\n') if line.strip()])

        paragraphs.append({
            'start': start,
            'end': end,
            'text': text
        })

    return paragraphs
