"""
测试通义千问 AI 笔记生成
"""

import sys
from pathlib import Path
import re

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import get_config
from ai_note_generator import create_ai_generator
from loguru import logger


def load_transcript(transcript_path: str):
    """加载转录结果"""
    with open(transcript_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析 Markdown 格式的转录文件
    paragraphs = []

    # 匹配段落标题和内容
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


def main():
    """测试通义千问 AI 笔记生成"""
    logger.info("=" * 50)
    logger.info("测试通义千问 AI 笔记生成")
    logger.info("=" * 50)

    # 加载配置
    config = get_config("config/config.yaml")

    # 检查 API Key
    api_key = config.get('ai.qwen_api_key')
    if not api_key:
        logger.error("未配置通义千问 API Key")
        logger.info("请在 config/config.yaml 中配置 ai.qwen_api_key")
        return

    # 加载转录结果
    transcript_path = "data/transcripts/23af277a-6b01-4270-80a8-5401ef5247f7.md"
    logger.info(f"加载转录文件: {transcript_path}")

    paragraphs = load_transcript(transcript_path)
    logger.info(f"加载了 {len(paragraphs)} 个段落")

    # 生成 AI 笔记
    try:
        generator = create_ai_generator('qwen', {
            'qwen_api_key': config.get('ai.qwen_api_key'),
            'qwen_model': config.get('ai.qwen_model'),
            'max_tokens': config.get('ai.max_tokens'),
            'temperature': config.get('ai.temperature'),
            'timeout': config.get('ai.timeout')
        })

        note = generator.generate(
            paragraphs,
            podcast_info={
                'podcast_id': '23af277a-6b01-4270-80a8-5401ef5247f7',
                'duration': paragraphs[-1]['end'] if paragraphs else 0
            }
        )

        # 保存笔记
        output_path = "data/notes/23af277a-6b01-4270-80a8-5401ef5247f7_qwen_ai.md"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(note)

        logger.info("=" * 50)
        logger.info("通义千问 AI 笔记生成完成")
        logger.info(f"输出文件: {output_path}")
        logger.info("=" * 50)

        # 显示笔记预览
        logger.info("\n笔记预览（前 800 字）:")
        logger.info(note[:800])
        logger.info("...")

    except ImportError as e:
        logger.error(f"导入失败: {e}")
        logger.info("请安装 openai 库: pip install openai")
    except Exception as e:
        logger.error(f"AI 笔记生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
