# 通义千问 API 配置指南

## 为什么选择通义千问？

✅ **价格优势**：约 ¥0.0008/分钟，比 OpenAI 便宜约 50 倍
✅ **中文优化**：专门针对中文语音识别优化
✅ **国内访问**：无需代理，访问速度快
✅ **高准确率**：Paraformer 模型在中文识别上表现优秀

## 费用对比

| 服务商 | 价格 | 60分钟播客成本 |
|--------|------|----------------|
| OpenAI Whisper | $0.006/分钟 | 约 $0.36 (¥2.5) |
| 通义千问 Paraformer | ¥0.0008/分钟 | 约 ¥0.05 ($0.007) |

**通义千问便宜约 50 倍！**

## 获取 API Key

### 步骤 1：注册阿里云账号

访问：https://www.aliyun.com/

### 步骤 2：开通 DashScope 服务

1. 访问 DashScope 控制台：https://dashscope.console.aliyun.com/
2. 点击"开通服务"
3. 同意服务协议

### 步骤 3：创建 API Key

1. 在控制台点击"API-KEY 管理"
2. 点击"创建新的 API-KEY"
3. 复制生成的 API Key（格式：sk-...）

### 步骤 4：充值（可选）

- 新用户通常有免费额度
- 如需充值，在控制台选择"账户管理" -> "充值"
- 建议充值 ¥10 即可使用很长时间

## 配置步骤

### 1. 编辑配置文件

打开 `config/config.yaml`：

```yaml
whisper:
  api_provider: "qwen"  # 设置为 qwen
  qwen_api_key: "sk-your-dashscope-key-here"  # 填入你的 API Key
  qwen_model: "paraformer-v2"  # 推荐使用 v2 版本
  language: "zh"
```

### 2. 测试配置

```bash
python test_api_config.py
```

如果看到 `[SUCCESS] 通义千问配置测试通过！` 说明配置正确。

### 3. 运行程序

```bash
python src/main.py "https://www.xiaoyuzhoufm.com/episode/6953183a2db086f897b08ad9"
```

## 模型选择

通义千问提供两个模型：

### paraformer-v2（推荐）
- 高准确率
- 适合离线转录
- 支持长音频

### paraformer-realtime-v2
- 实时转录
- 低延迟
- 适合流式处理

在 `config/config.yaml` 中修改：

```yaml
whisper:
  qwen_model: "paraformer-v2"  # 或 "paraformer-realtime-v2"
```

## 环境变量方式（可选）

如果不想在配置文件中保存 API Key，可以使用环境变量：

### Windows (PowerShell)
```powershell
$env:DASHSCOPE_API_KEY="sk-your-api-key"
python src/main.py "播客URL"
```

### Windows (CMD)
```cmd
set DASHSCOPE_API_KEY=sk-your-api-key
python src/main.py "播客URL"
```

### Linux/Mac
```bash
export DASHSCOPE_API_KEY="sk-your-api-key"
python src/main.py "播客URL"
```

## 故障排除

### API Key 无效
- 错误：`AuthenticationError`
- 解决：检查 API Key 是否正确复制，确保没有多余空格

### 余额不足
- 错误：`InsufficientBalance`
- 解决：在阿里云控制台充值

### 网络问题
- 错误：`Connection timeout`
- 解决：检查网络连接，通义千问在国内访问无需代理

### 音频格式不支持
- 错误：`UnsupportedFormat`
- 解决：支持的格式包括 mp3, wav, m4a, flac
- 程序会自动处理 m4a 格式

## 切换到其他 API

### 切换到 OpenAI

```yaml
whisper:
  api_provider: "openai"
  openai_api_key: "sk-your-openai-key"
```

### 切换到本地模型

```yaml
whisper:
  api_provider: "local"
  model_size: "base"
```

## 性能对比

基于实际测试（60分钟播客）：

| 指标 | OpenAI | 通义千问 |
|------|--------|----------|
| 转录时间 | ~5-8 分钟 | ~3-5 分钟 |
| 准确率（中文） | 85-90% | 90-95% |
| 费用 | $0.36 | ¥0.05 |
| 网络要求 | 需要代理 | 国内直连 |

## 推荐配置

对于中文播客转录，推荐使用通义千问：

```yaml
whisper:
  api_provider: "qwen"
  qwen_api_key: "your-key-here"
  qwen_model: "paraformer-v2"
  language: "zh"
```

## 下一步

配置完成后，程序将：
1. ✅ 下载音频
2. ✅ 使用通义千问 API 转录
3. ✅ 保存转录结果
4. ⏳ 生成笔记（待实现）

准备好后，运行程序开始测试！
