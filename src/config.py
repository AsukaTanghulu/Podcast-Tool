"""
配置加载模块
负责加载和管理配置文件
支持从环境变量读取敏感信息（API Keys）
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from loguru import logger

# 尝试加载 python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载 .env 文件
except ImportError:
    logger.warning("未安装 python-dotenv，无法从 .env 文件加载环境变量")


class Config:
    """配置管理类"""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化配置

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件并从环境变量覆盖敏感信息"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"配置文件加载成功: {self.config_path}")

            # 从环境变量覆盖 API Keys
            self._load_secrets_from_env(config)

            return config
        except Exception as e:
            logger.warning(f"配置文件加载失败，使用默认配置: {e}")
            return self._default_config()

    def _load_secrets_from_env(self, config: Dict[str, Any]):
        """从环境变量加载敏感信息（API Keys）"""
        # API Keys 映射：环境变量名 -> 配置路径列表（一个环境变量可以映射到多个配置位置）
        env_mappings = {
            'QWEN_API_KEY': [
                ['ai', 'qwen_api_key'],
                ['whisper', 'qwen_api_key']
            ],
            'DEEPSEEK_API_KEY': [
                ['ai', 'deepseek_api_key']
            ],
            'OPENAI_API_KEY': [
                ['ai', 'openai_api_key'],
                ['whisper', 'openai_api_key']
            ],
            'CLAUDE_API_KEY': [
                ['ai', 'claude_api_key']
            ],
            'DOUBAO_API_KEY': [
                ['ai', 'doubao_api_key']
            ],
            'HF_TOKEN': [
                ['diarization', 'hf_token']
            ],
        }

        # 从环境变量读取并覆盖配置
        for env_var, config_paths in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                # 将环境变量值设置到所有映射的配置路径
                for config_path in config_paths:
                    # 导航到配置的嵌套位置
                    current = config
                    for key in config_path[:-1]:
                        if key not in current:
                            current[key] = {}
                        current = current[key]

                    # 设置值
                    current[config_path[-1]] = env_value
                    logger.debug(f"从环境变量加载: {env_var} -> {'.'.join(config_path)}")


    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "app": {
                "name": "播客分析工具",
                "version": "1.0.0",
                "debug": True
            },
            "database": {
                "path": "data/database.db"
            },
            "storage": {
                "audio_dir": "data/audio",
                "transcript_dir": "data/transcripts",
                "note_dir": "data/notes",
                "keep_audio": True
            },
            "whisper": {
                "model_size": "medium",
                "device": "cpu",
                "compute_type": "int8",
                "language": "zh"
            }
        }

    def get(self, key: str, default=None):
        """
        获取配置项

        Args:
            key: 配置键，支持点号分隔的嵌套键（如 "app.name"）
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def __getitem__(self, key: str):
        """支持字典式访问"""
        return self.get(key)


# 全局配置实例
_config_instance = None


def get_config(config_path: str = "config/config.yaml") -> Config:
    """
    获取配置实例（单例模式）

    Args:
        config_path: 配置文件路径

    Returns:
        Config 实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
