"""
配置 HuggingFace Token
用于 pyannote.audio 讲话人识别功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

print("=" * 60)
print("Configure HuggingFace Token for Speaker Diarization")
print("=" * 60)

print("\nSteps to get HuggingFace Token:")
print("1. Visit https://huggingface.co/")
print("2. Sign up or log in")
print("3. Go to Settings -> Access Tokens")
print("4. Create a new token (need 'read' permission)")
print("5. Accept model license: https://huggingface.co/pyannote/speaker-diarization-3.1")

print("\n" + "=" * 60)

# 获取用户输入
token = input("\nPlease enter your HuggingFace token: ").strip()

if not token:
    print("\n[ERROR] Token cannot be empty!")
    sys.exit(1)

# 更新配置文件
try:
    from config import get_config
    import yaml

    # 使用绝对路径
    config_path = Path(__file__).parent / 'config' / 'config.yaml'

    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    # 更新 token
    if 'diarization' not in config_data:
        config_data['diarization'] = {}

    config_data['diarization']['hf_token'] = token

    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)

    print("\n[OK] Token configured successfully!")
    print(f"Token: {token[:10]}...{token[-10:]}")

    # 验证配置
    config = get_config(str(config_path))
    saved_token = config.get('diarization.hf_token')

    if saved_token == token:
        print("[OK] Configuration verified!")
    else:
        print("[WARNING] Configuration verification failed!")

except Exception as e:
    print(f"\n[ERROR] Failed to configure token: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Next steps:")
print("1. Install pyannote.audio: pip install pyannote.audio")
print("2. Run test: python test_diarization_with_model.py")
print("=" * 60)
