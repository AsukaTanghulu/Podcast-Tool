# 语音转录 API 选择指南

## 支持的转录方式

项目现在支持三种转录方式：

1. **本地模型**（local）- 使用 Whisper 本地模型
2. **OpenAI API**（openai）- 使用 OpenAI Whisper API
3. **通义千问 API**（qwen）- 使用阿里云通义千问 Paraformer

## 快速对比

| 特性 | 本地模型 | OpenAI API | 通义千问 API |
|------|----------|------------|--------------|
| **费用** | 免费 | $0.006/分钟 | ¥0.0008/分钟 |
| **60分钟成本** | ¥0 | ¥2.5 ($0.36) | ¥0.05 ($0.007) |
| **中文准确率** | 85-90% | 85-90% | 90-95% |
| **转录速度** | 慢（取决于CPU） | 快（5-8分钟） | 快（3-5分钟） |
| **网络要求** | 无 | 需要代理 | 国内直连 |
| **系统要求** | 高（需要依赖） | 低 | 低 |
| **推荐场景** | 大量转录 | 偶尔使用 | 中文播客 |

## 详细对比

### 1. 本地模型（local）

**优点：**
- ✅ 完全免费
- ✅ 无网络要求
- ✅ 数据隐私保护
- ✅ 无使用限制

**缺点：**
- ❌ 需要安装依赖（PyTorch 等）
- ❌ Windows 兼容性问题
- ❌ 转录速度慢
- ❌ 占用系统资源

**适合：**
- 有大量转录需求
- 对成本敏感
- 有技术能力解决依赖问题
- 对数据隐私有要求

**配置：**
```yaml
whisper:
  api_provider: "local"
  model_size: "base"  # tiny, base, small, medium, large
  device: "cpu"
  language: "zh"
```

### 2. OpenAI Whisper API（openai）

**优点：**
- ✅ 无需安装依赖
- ✅ 转录速度快
- ✅ 支持多语言
- ✅ 稳定可靠

**缺点：**
- ❌ 费用较高（$0.006/分钟）
- ❌ 需要代理访问
- ❌ 中文准确率一般
- ❌ 需要信用卡

**适合：**
- 偶尔使用
- 多语言需求
- 预算充足
- 能访问国际网络

**配置：**
```yaml
whisper:
  api_provider: "openai"
  openai_api_key: "sk-your-key"
  language: "zh"
```

**获取 API Key：**
https://platform.openai.com/api-keys

### 3. 通义千问 API（qwen）⭐ 推荐

**优点：**
- ✅ 价格极低（¥0.0008/分钟）
- ✅ 中文准确率最高（90-95%）
- ✅ 转录速度最快
- ✅ 国内直连，无需代理
- ✅ 支持支付宝充值
- ✅ 新用户有免费额度

**缺点：**
- ❌ 主要针对中文优化
- ❌ 需要阿里云账号

**适合：**
- 中文播客转录（强烈推荐）
- 预算有限
- 国内用户
- 需要高准确率

**配置：**
```yaml
whisper:
  api_provider: "qwen"
  qwen_api_key: "sk-your-key"
  qwen_model: "paraformer-v2"
  language: "zh"
```

**获取 API Key：**
https://dashscope.console.aliyun.com/

## 成本计算

### 示例：转录 100 小时播客

| 方式 | 总成本 | 单集成本（60分钟） |
|------|--------|-------------------|
| 本地模型 | ¥0 | ¥0 |
| OpenAI | ¥250 ($36) | ¥2.5 |
| 通义千问 | ¥5 ($0.7) | ¥0.05 |

**结论：通义千问比 OpenAI 便宜 50 倍！**

## 推荐方案

### 方案 1：通义千问（最推荐）

适合大多数中文播客用户：

```yaml
whisper:
  api_provider: "qwen"
  qwen_api_key: "your-key"
  qwen_model: "paraformer-v2"
  language: "zh"
```

**理由：**
- 价格极低，100小时仅需 ¥5
- 中文准确率最高
- 国内访问快速稳定
- 新用户有免费额度

### 方案 2：本地模型

适合技术用户或大量转录需求：

```yaml
whisper:
  api_provider: "local"
  model_size: "medium"
  device: "cpu"
  language: "zh"
```

**前提条件：**
- 已解决 Windows 依赖问题
- 有足够的计算资源
- 不介意较慢的转录速度

### 方案 3：OpenAI

适合偶尔使用或多语言需求：

```yaml
whisper:
  api_provider: "openai"
  openai_api_key: "your-key"
  language: "zh"
```

**适用场景：**
- 只转录几集播客
- 需要多语言支持
- 已有 OpenAI 账号

## 配置步骤

### 1. 选择 API 提供商

编辑 `config/config.yaml`，设置 `api_provider`：

```yaml
whisper:
  api_provider: "qwen"  # 或 "openai" 或 "local"
```

### 2. 配置 API Key

根据选择的提供商，填入对应的 API Key：

```yaml
# 通义千问
qwen_api_key: "sk-your-dashscope-key"

# 或 OpenAI
openai_api_key: "sk-your-openai-key"
```

### 3. 测试配置

```bash
python test_api_config.py
```

### 4. 开始转录

```bash
python src/main.py "播客URL"
```

## 切换 API

随时可以在 `config/config.yaml` 中切换：

```yaml
# 切换到通义千问
whisper:
  api_provider: "qwen"

# 切换到 OpenAI
whisper:
  api_provider: "openai"

# 切换到本地模型
whisper:
  api_provider: "local"
```

## 常见问题

### Q: 哪个 API 最便宜？
A: 通义千问最便宜，比 OpenAI 便宜约 50 倍。

### Q: 哪个准确率最高？
A: 对于中文播客，通义千问准确率最高（90-95%）。

### Q: 我没有信用卡，能用哪个？
A: 通义千问支持支付宝充值，无需信用卡。

### Q: 我在国外，能用通义千问吗？
A: 可以，但建议使用 OpenAI，访问速度更快。

### Q: 本地模型为什么不能用？
A: Windows 系统需要安装 Visual C++ Redistributable，详见 TROUBLESHOOTING.md。

### Q: 可以混合使用吗？
A: 可以，随时在配置文件中切换。

## 总结

**对于中文播客转录，强烈推荐使用通义千问 API：**
- ✅ 价格最低（¥0.05/小时）
- ✅ 准确率最高（90-95%）
- ✅ 速度最快（3-5分钟/小时）
- ✅ 国内访问无障碍

**配置指南：**
- 通义千问：查看 `QWEN_SETUP.md`
- OpenAI：查看 `API_SETUP.md`
- 本地模型：查看 `TROUBLESHOOTING.md`
