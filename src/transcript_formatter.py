"""
转录结果格式化模块
支持将转录结果导出为 Markdown 和 PDF 格式
"""

import re
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger


class TranscriptFormatter:
    """转录结果格式化器"""

    def __init__(self):
        """初始化格式化器"""
        pass

    def split_into_sentences(self, text: str) -> List[str]:
        """
        将文本按语义切分成句子

        Args:
            text: 原始文本

        Returns:
            句子列表
        """
        # 中文句子分隔符
        sentence_endings = r'[。！？；\n]+'

        # 按标点符号切分
        sentences = re.split(sentence_endings, text)

        # 过滤空句子并去除首尾空格
        sentences = [s.strip() for s in sentences if s.strip()]

        # 进一步处理：如果句子太长（超过100字），尝试按逗号切分
        result = []
        for sentence in sentences:
            if len(sentence) > 100:
                # 按逗号切分长句
                sub_sentences = re.split(r'[，、]', sentence)
                for sub in sub_sentences:
                    sub = sub.strip()
                    if sub:
                        result.append(sub)
            else:
                result.append(sentence)

        return result

    def format_time(self, seconds: float) -> str:
        """
        格式化时间

        Args:
            seconds: 秒数

        Returns:
            格式化的时间字符串 (HH:MM:SS)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def to_markdown(self, segments: List[Dict[str, Any]],
                   metadata: Dict[str, Any] = None,
                   output_path: str = None) -> str:
        """
        将转录结果转换为 Markdown 格式（对话式布局）

        Args:
            segments: 段落列表
            metadata: 元数据
            output_path: 输出文件路径（可选）

        Returns:
            Markdown 文本
        """
        lines = []

        # 获取说话人名称映射
        speaker_names = metadata.get('speaker_names', {}) if metadata else {}

        # 统计说话人数量
        speakers = set()
        for segment in segments:
            speaker_id = segment.get('speaker_id')
            if speaker_id:
                speakers.add(speaker_id)

        # 添加标题和元数据
        if metadata:
            lines.append(f"# 播客转录\n")
            if metadata.get('podcast_id'):
                lines.append(f"**播客 ID**: {metadata['podcast_id']}\n")
            if metadata.get('model'):
                lines.append(f"**转录模型**: {metadata['model']}\n")
            if speakers:
                # 显示说话人信息
                speaker_list = []
                for speaker_id in sorted(speakers):
                    speaker_key = str(speaker_id)
                    speaker_name = speaker_names.get(speaker_key, speaker_names.get(speaker_id, speaker_key))
                    speaker_list.append(str(speaker_name))
                lines.append(f"**说话人**: {', '.join(speaker_list)}\n")
            lines.append("\n---\n")

        # 处理每个段落（对话式布局）
        for segment in segments:
            start_time = self.format_time(segment['start'])
            end_time = self.format_time(segment['end'])
            speaker_id = segment.get('speaker_id', 'unknown')
            speaker_key = str(speaker_id)

            # 获取说话人名称（如果有自定义名称则使用，否则使用 speaker_id）
            speaker_name = speaker_names.get(speaker_key, speaker_names.get(speaker_id, speaker_key))

            # 对话式布局：**[时间] 说话人**
            lines.append(f"\n**[{start_time} - {end_time}] {speaker_name}**\n")

            # 使用引用块显示对话内容
            lines.append(f"> {segment['text']}\n")

        markdown_text = "".join(lines)

        # 保存到文件
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            logger.info(f"Markdown 文件已保存: {output_path}")

        return markdown_text

    def to_pdf(self, segments: List[Dict[str, Any]],
              metadata: Dict[str, Any] = None,
              output_path: str = None) -> str:
        """
        将转录结果转换为 PDF 格式

        Args:
            segments: 段落列表
            metadata: 元数据
            output_path: 输出文件路径

        Returns:
            PDF 文件路径
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.enums import TA_LEFT
        except ImportError:
            logger.error("需要安装 reportlab 库: pip install reportlab")
            raise ImportError("请安装 reportlab: pip install reportlab")

        if not output_path:
            raise ValueError("PDF 输出需要指定 output_path")

        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 注册中文字体（使用系统字体）
        try:
            # Windows 系统字体路径
            font_path = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑
            pdfmetrics.registerFont(TTFont('Chinese', font_path))
            font_name = 'Chinese'
        except:
            logger.warning("无法加载中文字体，PDF 可能无法正确显示中文")
            font_name = 'Helvetica'

        # 创建 PDF 文档
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # 定义样式
        styles = getSampleStyleSheet()

        # 标题样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=18,
            spaceAfter=12,
        )

        # 段落标题样式
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=14,
            spaceAfter=6,
        )

        # 正文样式
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            leading=16,
            alignment=TA_LEFT,
            leftIndent=0.5*cm,
        )

        # 构建文档内容
        story = []

        # 添加标题
        story.append(Paragraph("播客转录", title_style))
        story.append(Spacer(1, 0.5*cm))

        # 获取说话人名称映射
        speaker_names = metadata.get('speaker_names', {}) if metadata else {}

        # 统计说话人
        speakers = set()
        for segment in segments:
            speaker_id = segment.get('speaker_id')
            if speaker_id:
                speakers.add(speaker_id)

        # 添加元数据
        if metadata:
            if metadata.get('podcast_id'):
                story.append(Paragraph(f"<b>播客 ID:</b> {metadata['podcast_id']}", body_style))
            if metadata.get('model'):
                story.append(Paragraph(f"<b>转录模型:</b> {metadata['model']}", body_style))
            if speakers:
                speaker_list = []
                for speaker_id in sorted(speakers):
                    speaker_key = str(speaker_id)
                    speaker_name = speaker_names.get(speaker_key, speaker_names.get(speaker_id, speaker_key))
                    speaker_list.append(str(speaker_name))
                story.append(Paragraph(f"<b>说话人:</b> {', '.join(speaker_list)}", body_style))
            story.append(Spacer(1, 0.5*cm))

        # 处理每个段落（对话式布局）
        for segment in segments:
            start_time = self.format_time(segment['start'])
            end_time = self.format_time(segment['end'])
            speaker_id = segment.get('speaker_id', 'unknown')
            speaker_key = str(speaker_id)

            # 获取说话人名称
            speaker_name = speaker_names.get(speaker_key, speaker_names.get(speaker_id, speaker_key))

            # 添加说话人和时间戳
            story.append(Paragraph(
                f"<b>[{start_time} - {end_time}] {speaker_name}</b>",
                heading_style
            ))
            story.append(Spacer(1, 0.2*cm))

            # 添加对话内容
            story.append(Paragraph(segment['text'], body_style))
            story.append(Spacer(1, 0.5*cm))

        # 生成 PDF
        doc.build(story)
        logger.info(f"PDF 文件已保存: {output_path}")

        return output_path


def format_transcript(segments: List[Dict[str, Any]],
                     metadata: Dict[str, Any] = None,
                     output_format: str = 'markdown',
                     output_path: str = None) -> str:
    """
    格式化转录结果的便捷函数

    Args:
        segments: 段落列表
        metadata: 元数据
        output_format: 输出格式 ('markdown' 或 'pdf')
        output_path: 输出文件路径

    Returns:
        输出文件路径或 Markdown 文本
    """
    formatter = TranscriptFormatter()

    if output_format.lower() == 'markdown' or output_format.lower() == 'md':
        return formatter.to_markdown(segments, metadata, output_path)
    elif output_format.lower() == 'pdf':
        return formatter.to_pdf(segments, metadata, output_path)
    else:
        raise ValueError(f"不支持的输出格式: {output_format}")
