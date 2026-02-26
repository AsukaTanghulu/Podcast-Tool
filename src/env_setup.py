"""
环境变量配置
用于设置 HuggingFace 镜像等
"""

import os

# 配置 HuggingFace 镜像（国内加速）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 可选：设置模型缓存目录
# os.environ['HF_HOME'] = 'models'
