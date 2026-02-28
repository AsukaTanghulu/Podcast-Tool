# 密钥配置指南

## 为什么需要使用环境变量？

将 API Keys 等敏感信息直接写在配置文件中是**不安全**的做法，因为：
1. 配置文件可能被误提交到 Git 仓库
2. 配置文件可能被分享给他人
3. 密钥泄露会导致账户被盗用和产生费用

## 配置步骤

### 1. 安装依赖

```bash
pip install python-dotenv
```

### 2. 创建 .env 文件

在项目根目录（`podcast-analyzer/`）下创建 `.env` 文件：

```bash
# 复制示例文件
cp .env.example .env
```

或者手动创建 `.env` 文件，内容如下：

```env
# 通义千问 API Key
QWEN_API_KEY=sk-your-qwen-api-key-here

# DeepSeek API Key
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Claude API Key
CLAUDE_API_KEY=sk-ant-your-claude-api-key-here

# 豆包 API Key
DOUBAO_API_KEY=your-doubao-api-key-here

# HuggingFace Token (用于讲话人识别)
HF_TOKEN=hf_your-huggingface-token-here
```

### 3. 填入你的真实密钥

编辑 `.env` 文件，将 `your-xxx-api-key-here` 替换为你的真实密钥。

**注意**：
- 只填写你需要使用的 API Key
- 不需要的可以留空或删除该行
- `.env` 文件已经在 `.gitignore` 中，不会被提交到 Git

### 4. 验证配置

运行测试脚本验证配置是否正确：

```bash
python test_api_config.py
```

## 如何获取 API Keys？

### 通义千问 (推荐)
1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/)
2. 注册并登录
3. 在"API-KEY管理"中创建 API Key
4. 价格低廉，准确率高

### DeepSeek
1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册并登录
3. 在"API Keys"中创建密钥
4. 性价比高，适合 AI 笔记生成

### OpenAI
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册并登录
3. 在"API Keys"中创建密钥
4. 需要国际信用卡

### Claude
1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 注册并登录
3. 在"API Keys"中创建密钥

### HuggingFace Token
1. 访问 [HuggingFace](https://huggingface.co/)
2. 注册并登录
3. 在 Settings -> Access Tokens 中创建 Token
4. 用于下载讲话人识别模型

## 配置优先级

程序会按以下优先级读取配置：

1. **环境变量** (最高优先级) - 从 `.env` 文件或系统环境变量读取
2. **配置文件** - 从 `config/config.yaml` 读取

这意味着：
- 如果设置了环境变量，会覆盖配置文件中的值
- 如果没有设置环境变量，会使用配置文件中的值

## 安全建议

1. ✅ **永远不要**将 `.env` 文件提交到 Git
2. ✅ **永远不要**在配置文件中写明文密钥
3. ✅ **定期轮换** API Keys
4. ✅ **设置使用限额**，防止密钥被盗用后产生大额费用
5. ✅ **不要分享**你的 `.env` 文件给他人

## 故障排查

### 问题：提示"未配置 API Key"

**解决方案**：
1. 检查 `.env` 文件是否存在
2. 检查 `.env` 文件中的密钥是否正确填写
3. 检查环境变量名是否正确（区分大小写）
4. 重启应用程序

### 问题：API 调用失败

**解决方案**：
1. 检查密钥是否有效（未过期、未被删除）
2. 检查账户余额是否充足
3. 检查网络连接是否正常
4. 查看日志文件 `logs/app.log` 获取详细错误信息

## 示例

假设你只使用通义千问，你的 `.env` 文件应该是：

```env
QWEN_API_KEY= xxx
```

其他不需要的 API Key 可以不填写。

## 更多帮助

如有问题，请查看：
- [项目 README](README.md)
- [配置文件说明](config/config.yaml)
- [故障排查文档](TROUBLESHOOTING.md)
