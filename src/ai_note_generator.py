"""
AI 笔记生成模块
集成大模型 API 进行深度分析
"""

import time
from typing import List, Dict, Any
from loguru import logger

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("未安装 openai 库，AI 笔记功能不可用。安装方法: pip install openai")


class AINotGenerator:
    """AI 笔记生成器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 AI 笔记生成器

        Args:
            config: 配置字典，包含 api_key, model, base_url 等
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("需要安装 openai 库: pip install openai")

        self.config = config
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'deepseek-chat')
        self.base_url = config.get('base_url', 'https://api.deepseek.com')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.7)
        self.timeout = config.get('timeout', 60)

        if not self.api_key:
            raise ValueError("未配置 API Key")

        # 初始化客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        logger.info(f"AI 笔记生成器初始化完成 (模型: {self.model})")

    def _build_prompt(self, transcript_text: str, podcast_info: Dict[str, Any] = None) -> str:
        """
        构建 Prompt（优化版 v2.0）

        Args:
            transcript_text: 转录文本
            podcast_info: 播客信息

        Returns:
            Prompt 文本
        """
        prompt = """你是一名专业的播客内容分析师，擅长提炼和总结播客中的要点。

请你对这份播客的逐字稿进行深入解读，识别所有关键信息点，并对每个关键信息点进行详细分析和描述，生成一份详细、清晰、易懂的播客内容摘要。

## 要求：
1. **忠于原文**：摘要必须完全基于播客内容，不添加个人解释、评论或总结性语言
2. **详细描述**：对每个重点进行深入解释，确保普通人也能轻松理解
3. **结构化输出**：使用清晰的Markdown格式，包含引言、主体（每个重点的详细描述）和结尾
4. **完整性**：不遗漏任何重要信息点
5. **金句提取**：从原文中提取3-5句最精彩、最有价值的原话

## 输出格式：

# 播客内容摘要

## 引言
[简要介绍播客的主题和背景，1-2段]

## 主要内容

### 重点1：[标题]
[详细描述这个重点的内容，包括：
- 具体讨论了什么
- 提到了哪些关键信息、数据、案例
- 相关的论述和解释
保持客观，忠于原文]

### 重点2：[标题]
[同上格式]

### 重点3：[标题]
[同上格式]

...（根据实际内容添加更多重点）

## 金句分享

> "金句1原文"

> "金句2原文"

> "金句3原文"

[根据需要添加更多金句，每句都必须是播客中的原话]

## 结尾
[总结播客涵盖的主要话题，1段]

---

## 播客逐字稿：
"""
        prompt += transcript_text
        return prompt

    def generate(self, paragraphs: List[Dict[str, Any]],
                podcast_info: Dict[str, Any] = None,
                max_retries: int = 3) -> str:
        """
        生成 AI 笔记

        Args:
            paragraphs: 段落列表
            podcast_info: 播客信息
            max_retries: 最大重试次数

        Returns:
            Markdown 格式的笔记
        """
        logger.info("开始生成 AI 笔记")

        # 构建转录文本
        transcript_text = ""
        for i, para in enumerate(paragraphs, 1):
            start_time = self._format_time(para['start'])
            end_time = self._format_time(para['end'])
            transcript_text += f"\n## 段落 {i} [{start_time} - {end_time}]\n"
            transcript_text += para['text'] + "\n"

        # 构建 Prompt
        prompt = self._build_prompt(transcript_text, podcast_info)

        # 调用 API
        for attempt in range(max_retries):
            try:
                logger.info(f"调用 {self.model} API (尝试 {attempt + 1}/{max_retries})")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一位专业的播客内容分析师，擅长提炼核心观点和深度分析。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    timeout=self.timeout
                )

                note = response.choices[0].message.content

                logger.info("AI 笔记生成成功")
                return note

            except Exception as e:
                logger.warning(f"API 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error("API 调用失败，已达最大重试次数")
                    raise

    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def create_ai_generator(provider: str, config: Dict[str, Any]) -> AINotGenerator:
    """
    创建 AI 笔记生成器

    Args:
        provider: API 提供商 (deepseek, claude, openai, doubao, qwen)
        config: 配置字典

    Returns:
        AI 笔记生成器实例
    """
    if provider == 'deepseek':
        return AINotGenerator({
            'api_key': config.get('deepseek_api_key'),
            'model': config.get('deepseek_model', 'deepseek-chat'),
            'base_url': 'https://api.deepseek.com',
            'max_tokens': config.get('max_tokens', 2000),
            'temperature': config.get('temperature', 0.7),
            'timeout': config.get('timeout', 60)
        })
    elif provider == 'claude':
        # Claude API 不兼容 OpenAI SDK，暂不支持
        raise ValueError("Claude 暂不支持，因为其 API 不兼容 OpenAI SDK。请使用 qwen、deepseek 或 openai。")
    elif provider == 'openai':
        return AINotGenerator({
            'api_key': config.get('openai_api_key'),
            'model': config.get('openai_model', 'gpt-3.5-turbo'),
            'base_url': 'https://api.openai.com/v1',
            'max_tokens': config.get('max_tokens', 2000),
            'temperature': config.get('temperature', 0.7),
            'timeout': config.get('timeout', 60)
        })
    elif provider == 'doubao':
        # 豆包（字节跳动）使用 OpenAI 兼容接口
        return AINotGenerator({
            'api_key': config.get('doubao_api_key'),
            'model': config.get('doubao_model', 'doubao-pro-32k'),
            'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
            'max_tokens': config.get('max_tokens', 2000),
            'temperature': config.get('temperature', 0.7),
            'timeout': config.get('timeout', 60)
        })
    elif provider == 'qwen':
        # 通义千问使用 OpenAI 兼容接口
        return AINotGenerator({
            'api_key': config.get('qwen_api_key'),
            'model': config.get('qwen_model', 'qwen-plus'),
            'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'max_tokens': config.get('max_tokens', 2000),
            'temperature': config.get('temperature', 0.7),
            'timeout': config.get('timeout', 60)
        })
    else:
        raise ValueError(f"不支持的 AI 提供商: {provider}")
