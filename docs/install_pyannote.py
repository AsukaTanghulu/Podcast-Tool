"""
安装 pyannote.audio 及其依赖
"""

import subprocess
import sys

print("=" * 60)
print("Install pyannote.audio for Speaker Diarization")
print("=" * 60)

print("\nThis will install:")
print("- pyannote.audio==3.1.1")
print("- torch (if not installed)")
print("- torchaudio (if not installed)")

print("\nNote:")
print("- First installation will download ~1GB model")
print("- Requires HuggingFace token")
print("- May take several minutes")

response = input("\nContinue? (y/n): ").strip().lower()

if response != 'y':
    print("Installation cancelled.")
    sys.exit(0)

print("\n" + "=" * 60)
print("Installing packages...")
print("=" * 60)

packages = [
    "pyannote.audio==3.1.1",
]

for package in packages:
    print(f"\nInstalling {package}...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", package
        ])
        print(f"[OK] {package} installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install {package}: {e}")
        sys.exit(1)

print("\n" + "=" * 60)
print("Installation completed!")
print("=" * 60)

print("\nNext steps:")
print("1. Configure HuggingFace token: python configure_hf_token.py")
print("2. Run test: python test_diarization_with_model.py")
