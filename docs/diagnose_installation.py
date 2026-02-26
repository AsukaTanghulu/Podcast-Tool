"""
诊断 PyTorch 和 pyannote.audio 安装问题
"""

import sys
import subprocess

print("=" * 60)
print("Diagnose PyTorch and pyannote.audio Installation")
print("=" * 60)

# 检查 Python 版本
print("\n1. Python version:")
print(f"   {sys.version}")

# 检查已安装的包
print("\n2. Check installed packages:")

packages_to_check = ['torch', 'torchaudio', 'pyannote.audio']

for package in packages_to_check:
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', package],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            version_line = [l for l in lines if l.startswith('Version:')]
            if version_line:
                print(f"   [OK] {package}: {version_line[0].split(':')[1].strip()}")
        else:
            print(f"   [NOT INSTALLED] {package}")
    except Exception as e:
        print(f"   [ERROR] {package}: {e}")

# 尝试导入 torch
print("\n3. Try importing torch:")
try:
    import torch
    print(f"   [OK] torch imported successfully")
    print(f"   Version: {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
except Exception as e:
    print(f"   [ERROR] Failed to import torch: {e}")
    print("\n   This is usually caused by:")
    print("   1. Missing Visual C++ Redistributable")
    print("   2. Incompatible torch version")
    print("   3. Corrupted installation")
    print("\n   Solutions:")
    print("   A. Install Visual C++ Redistributable:")
    print("      https://aka.ms/vs/17/release/vc_redist.x64.exe")
    print("   B. Reinstall torch:")
    print("      pip uninstall torch torchaudio")
    print("      pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu")

# 尝试导入 pyannote.audio
print("\n4. Try importing pyannote.audio:")
try:
    import pyannote.audio
    print(f"   [OK] pyannote.audio imported successfully")
    print(f"   Version: {pyannote.audio.__version__}")
except Exception as e:
    print(f"   [ERROR] Failed to import pyannote.audio: {e}")

print("\n" + "=" * 60)
print("Diagnosis completed")
print("=" * 60)
