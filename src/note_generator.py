"""
笔记生成模块
支持规则引擎和 AI 两种模式
"""

from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from jinja2 import Template


class NoteGenerator:
    """笔记生成器"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化笔记生成器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        logger.info("笔记生成器初始化完成")

    def format_time(self, seconds: float) -> str:
        """格式化时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def generate_from_analysis(self, analysis_result: Dict[str, Any],
                               podcast_info: Dict[str, Any] = None) -> str:
        """
        基于规则引擎分析结果生成笔记（简化版）

        Args:
            analysis_result: 分析结果
            podcast_info: 播客信息

        Returns:
            Markdown 格式的笔记
        """
        logger.info("开始生成规则引擎笔记（简化版）")

        # 计算时长
        duration = "未知"
        if podcast_info and 'duration' in podcast_info:
            duration = self.format_time(podcast_info['duration'])

        # Markdown 模板（简化版）
        template_str = """# 播客快速预览

{% if podcast_info %}
**播客 ID**: {{ podcast_info.podcast_id }}
**生成时间**: {{ podcast_info.generated_at }}
**笔记类型**: 规则引擎快速预览

---
{% endif %}

## 📊 基础信息

- **时长**: {{ duration }}
- **字数统计**: {{ word_count }} 字

## 🔑 关键词

{% for kw in keywords %}
- **{{ kw.word }}** (权重: {{ "%.2f"|format(kw.weight) }})
{% endfor %}

## ⏱️ 时间轴

{% for item in timeline %}
**{{ item.time }}**
{{ item.summary }}

{% endfor %}

---

*本预览由规则引擎自动生成，仅供快速浏览*
*建议使用 AI 笔记功能获取详细的内容摘要*
"""

        # 渲染模板
        template = Template(template_str)
        note = template.render(
            keywords=analysis_result.get('keywords', []),
            timeline=analysis_result.get('timeline', []),
            word_count=analysis_result.get('word_count', 0),
            duration=duration,
            podcast_info=podcast_info,
            format_time=self.format_time
        )

        logger.info("规则引擎笔记生成完成（简化版）")
        return note

    def save_note(self, content: str, output_path: str):
        """
        保存笔记到文件

        Args:
            content: 笔记内容
            output_path: 输出路径
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"笔记已保存: {output_path}")
