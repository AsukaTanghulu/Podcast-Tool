# Whisper API 配置指南

## 获取 OpenAI API Key

1. 访问 OpenAI 平台：https://platform.openai.com/api-keys
2. 登录或注册账号
3. 点击 "Create new secret key"
4. 复制生成的 API Key（格式：sk-...）

## 配置步骤

### 1. 编辑配置文件

打开 `config/config.yaml`，找到 whisper 配置部分：

```yaml
whisper:
  use_api: true  # 已设置为 true，使用 API 模式
  api_key: ""    # 在这里填入你的 API Key
  language: "zh"
```

将你的 API Key 填入 `api_key` 字段：

```yaml
whisper:
  use_api: true
  api_key: "sk-your-actual-api-key-here"  # 替换为实际的 Key
  language: "zh"
```

### 2. 运行程序

```bash
python src/main.py "https://www.xiaoyuzhoufm.com/episode/6953183a2db086f897b08ad9"
```

## API 费用说明

OpenAI Whisper API 按音频时长计费：
- 价格：$0.006 / 分钟
- 测试播客（约 60 分钟）：约 $0.36

## 环境变量方式（可选）

如果不想在配置文件中保存 API Key，可以使用环境变量：

### Windows (PowerShell)
```powershell
$env:OPENAI_API_KEY="sk-your-api-key"
python src/main.py "播客URL"
```

### Windows (CMD)
```cmd
set OPENAI_API_KEY=sk-your-api-key
python src/main.py "播客URL"
```

### Linux/Mac
```bash
export OPENAI_API_KEY="sk-your-api-key"
python src/main.py "播客URL"
```

## 切换回本地模式

如果以后想使用本地模型（需要先解决 PyTorch 依赖问题），只需修改配置：

```yaml
whisper:
  use_api: false  # 改为 false
  model_size: "base"  # 选择模型大小：tiny, base, small, medium, large
  device: "cpu"
  language: "zh"
```

## 故障排除

### API Key 无效
- 错误：`401 Unauthorized`
- 解决：检查 API Key 是否正确复制，确保没有多余空格

### 配额不足
- 错误：`429 Too Many Requests` 或 `insufficient_quota`
- 解决：检查账户余额，充值或等待配额重置

### 网络问题
- 错误：`Connection timeout`
- 解决：检查网络连接，可能需要配置代理

### 文件太大
- 错误：`File size exceeds limit`
- 解决：Whisper API 限制单个文件 25MB，需要先压缩音频

## 下一步

配置完成后，程序将：
1. ✅ 下载音频
2. ✅ 使用 API 转录
3. ✅ 保存转录结果
4. ⏳ 生成笔记（待实现）

准备好后，运行程序开始测试！
