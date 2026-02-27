"""
AI 对话模块
基于转录全文与 AI 进行对话
"""

import os
from typing import List, Dict, Any
from loguru import logger


class AIChatError(Exception):
    """AI 对话异常"""
    pass


class AIChat:
    """AI 对话基类"""

    def __init__(self, config: dict):
        """
        初始化 AI 对话

        Args:
            config: 配置字典
        """
        self.config = config
        self.conversation_history = []
        self.transcript_context = ""

    def set_transcript_context(self, transcript_text: str, metadata: dict = None):
        """
        设置转录文本上下文

        Args:
            transcript_text: 转录全文
            metadata: 元数据（标题、时长等）
        """
        self.transcript_context = transcript_text
        self.metadata = metadata or {}

        # 构建系统提示词
        system_prompt = self._build_system_prompt()
        self.conversation_history = [
            {"role": "system", "content": system_prompt}
        ]

    def _build_system_prompt(self) -> str:
        """构建系统提示词（从 prompts.yaml 加载）"""
        title = self.metadata.get('title', '这个播客')

        # 尝试从配置加载 prompt 模板
        try:
            from config import get_config
            from pathlib import Path
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"
            cfg = get_config(str(config_path))
            prompt_template = cfg.get('prompts.ai_chat_system', None)

            if prompt_template:
                # 使用配置的模板
                return prompt_template.format(
                    title=title,
                    transcript_context=self.transcript_context
                )
        except Exception as e:
            logger.warning(f"加载 AI 对话 prompt 模板失败，使用默认模板: {e}")

        # 默认模板（如果配置加载失败）
        prompt = f"""你是一个专业的播客内容分析助手。用户刚刚收听了《{title}》这期播客，现在想与你讨论其中的内容。

# 你的角色定位
- 你是一个深度思考者，帮助用户理解和消化播客内容
- 你的所有回答必须基于播客的实际内容，不能编造或引入播客中没有的观点
- 你可以帮助用户复习要点、澄清疑惑、深化理解、激发思考

# 播客转录全文
{self.transcript_context}

# 对话原则
1. **忠于原文**: 所有观点和论述必须来自播客内容，引用时注明出处
2. **深度思考**: 帮助用户挖掘内容背后的深层含义和逻辑
3. **启发式提问**: 通过提问引导用户思考，而不是直接给出答案
4. **关联思考**: 帮助用户将播客内容与其他知识、经验关联
5. **批判性思维**: 鼓励用户质疑和反思播客中的观点

# 回答风格
- 简洁明了，避免冗长
- 使用具体例子和引用
- 鼓励对话和互动
- 承认不确定性（如果播客中没有明确说明）

现在，用户准备开始与你讨论这期播客的内容。"""

        return prompt

    def chat(self, user_message: str) -> str:
        """
        发送消息并获取回复

        Args:
            user_message: 用户消息

        Returns:
            AI 回复
        """
        raise NotImplementedError("子类必须实现 chat 方法")

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        # 返回除了系统提示词之外的对话历史
        return [msg for msg in self.conversation_history if msg['role'] != 'system']

    def clear_history(self):
        """清空对话历史（保留系统提示词）"""
        system_msg = self.conversation_history[0] if self.conversation_history else None
        self.conversation_history = [system_msg] if system_msg else []


class QwenChat(AIChat):
    """通义千问对话"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('qwen_api_key') or os.getenv('QWEN_API_KEY')
        self.model = config.get('qwen_model', 'qwen-plus')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.7)

        if not self.api_key:
            raise AIChatError("未配置通义千问 API Key")

    def chat(self, user_message: str) -> str:
        """发送消息并获取回复"""
        try:
            import dashscope
            from dashscope import Generation

            dashscope.api_key = self.api_key

            # 添加用户消息到历史
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })

            # 调用 API
            response = Generation.call(
                model=self.model,
                messages=self.conversation_history,
                result_format='message',
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            if response.status_code == 200:
                assistant_message = response.output.choices[0].message.content

                # 添加助手回复到历史
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                return assistant_message
            else:
                error_msg = f"API 调用失败: {response.code} - {response.message}"
                logger.error(error_msg)
                raise AIChatError(error_msg)

        except Exception as e:
            logger.error(f"通义千问对话失败: {e}")
            raise AIChatError(f"对话失败: {str(e)}")


class DeepseekChat(AIChat):
    """Deepseek 对话"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('deepseek_api_key') or os.getenv('DEEPSEEK_API_KEY')
        self.model = config.get('deepseek_model', 'deepseek-chat')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.7)
        self.base_url = config.get('deepseek_base_url', 'https://api.deepseek.com')

        if not self.api_key:
            raise AIChatError("未配置 Deepseek API Key")

    def chat(self, user_message: str) -> str:
        """发送消息并获取回复"""
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

            # 添加用户消息到历史
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })

            # 调用 API
            response = client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            assistant_message = response.choices[0].message.content

            # 添加助手回复到历史
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return assistant_message

        except Exception as e:
            logger.error(f"Deepseek 对话失败: {e}")
            raise AIChatError(f"对话失败: {str(e)}")


def create_ai_chat(provider: str, config: dict) -> AIChat:
    """
    创建 AI 对话实例

    Args:
        provider: AI 提供商 ('qwen' 或 'deepseek')
        config: 配置字典

    Returns:
        AIChat 实例
    """
    if provider == 'qwen':
        return QwenChat(config)
    elif provider == 'deepseek':
        return DeepseekChat(config)
    else:
        raise AIChatError(f"不支持的 AI 提供商: {provider}")
