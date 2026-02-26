"""
文本分析模块
提供基于规则引擎的文本分析功能（简化版）
"""

import re
import jieba
import jieba.analyse
from typing import List, Dict, Any
from loguru import logger


class TextAnalyzer:
    """文本分析器（规则引擎 - 简化版）"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化分析器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.top_keywords = self.config.get('top_keywords', 15)

        logger.info("文本分析器初始化完成（简化版）")

    def extract_keywords(self, text: str, top_n: int = None) -> List[Dict[str, Any]]:
        """
        提取关键词（改进版）

        Args:
            text: 文本内容
            top_n: 返回前 N 个关键词

        Returns:
            关键词列表，每个元素包含 word 和 weight
        """
        if top_n is None:
            top_n = self.top_keywords

        # 使用 jieba 的 TF-IDF 算法提取关键词
        # 只保留名词、动词、形容词
        keywords = jieba.analyse.extract_tags(
            text,
            topK=top_n,
            withWeight=True,
            allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn', 'a', 'an', 'vd', 'vg')
        )

        result = [
            {'word': word, 'weight': float(weight)}
            for word, weight in keywords
        ]

        logger.info(f"提取了 {len(result)} 个关键词")
        return result

    def generate_timeline(self, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成时间轴（改进版）

        Args:
            paragraphs: 段落列表

        Returns:
            时间轴列表
        """
        timeline = []

        for i, para in enumerate(paragraphs):
            text = para['text']

            # 提取段落摘要：优先使用第一句，如果第一句太短则使用前两句
            sentences = re.split(r'[。！？；]', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                continue

            # 生成摘要
            if len(sentences[0]) >= 20:
                summary = sentences[0]
            elif len(sentences) > 1:
                summary = sentences[0] + '。' + sentences[1]
            else:
                summary = sentences[0]

            # 限制长度
            if len(summary) > 80:
                summary = summary[:80] + '...'

            timeline.append({
                'index': i + 1,
                'start': para['start'],
                'end': para['end'],
                'time': self.format_time(para['start']),
                'summary': summary
            })

        logger.info(f"生成了 {len(timeline)} 个时间点")
        return timeline

    def format_time(self, seconds: float) -> str:
        """格式化时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def analyze(self, paragraphs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        完整分析（简化版）

        Args:
            paragraphs: 段落列表

        Returns:
            分析结果字典
        """
        logger.info("开始文本分析（简化版）")

        # 合并所有文本
        full_text = ' '.join([p['text'] for p in paragraphs])

        result = {
            'keywords': self.extract_keywords(full_text),
            'timeline': self.generate_timeline(paragraphs),
            'word_count': len(full_text)
        }

        logger.info("文本分析完成")
        return result
