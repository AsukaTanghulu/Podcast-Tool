# 故障排除指南

## 当前问题：Whisper 模型加载失败

### 问题描述
在 Windows 系统上运行时，遇到以下错误：

1. **faster-whisper**: 段错误 (Segmentation fault)
2. **openai-whisper**: PyTorch DLL 加载失败

```
OSError: [WinError 1114] 动态链接库(DLL)初始化例程失败。
Error loading "D:\Anaconda\Lib\site-packages\torch\lib\c10.dll"
```

### 根本原因
这是 Windows 系统上常见的兼容性问题：
- PyTorch 需要 Visual C++ Redistributable 2015-2022
- 某些 CPU 架构与 faster-whisper 的 int8 量化不兼容
- 缺少必要的系统依赖

## 解决方案

### 方案 1：安装 Visual C++ Redistributable（推荐）

1. 下载并安装 Microsoft Visual C++ Redistributable：
   - 访问：https://aka.ms/vs/17/release/vc_redist.x64.exe
   - 或搜索 "Visual C++ Redistributable 2015-2022"

2. 安装后重启计算机

3. 重新运行程序：
   ```bash
   python src/main.py "https://www.xiaoyuzhoufm.com/episode/6953183a2db086f897b08ad9"
   ```

### 方案 2：使用 Whisper API（最简单）

如果本地模型无法运行，可以使用 OpenAI 的 Whisper API：

1. 获取 OpenAI API Key：https://platform.openai.com/api-keys

2. 修改 `src/transcriber_api.py`（已创建）使用 API 版本

3. 在 `config/config.yaml` 中添加：
   ```yaml
   whisper:
     use_api: true
     api_key: "your-api-key-here"
   ```

### 方案 3：使用 Docker（隔离环境）

创建 Docker 容器运行程序，避免 Windows 兼容性问题：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/main.py"]
```

### 方案 4：使用 WSL2（Linux 子系统）

在 Windows 上使用 Linux 环境：

1. 启用 WSL2：
   ```powershell
   wsl --install
   ```

2. 在 WSL2 中安装 Python 和依赖

3. 运行程序

## 临时解决方案

### 使用预转录的音频

如果急需测试其他功能，可以：

1. 使用在线转录服务（如讯飞听见、网易见外）手动转录音频

2. 将转录结果保存为 JSON 格式：
   ```json
   {
     "segments": [
       {
         "start": 0.0,
         "end": 5.2,
         "text": "这是第一段文本"
       }
     ]
   }
   ```

3. 跳过转录步骤，直接测试笔记生成功能

## 验证修复

运行以下命令验证 PyTorch 是否正常工作：

```python
python -c "import torch; print(torch.__version__); print('PyTorch 工作正常！')"
```

如果成功，应该看到版本号和成功消息。

## 需要帮助？

如果以上方案都无法解决问题，请提供：
1. Windows 版本（运行 `winver` 查看）
2. Python 版本（运行 `python --version`）
3. CPU 型号
4. 完整错误日志

## 下一步

修复 PyTorch 问题后，程序应该能够：
1. ✅ 下载音频（已验证工作）
2. ✅ 音频质量检查（已验证工作）
3. ⏳ 语音转录（待修复）
4. ⏳ 生成笔记（待实现）
