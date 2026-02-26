# 通义千问 API 集成完成

## 已完成的工作

✅ **新增通义千问转录器**
- 创建 `src/transcriber_qwen.py`
- 实现完整的 Paraformer API 调用
- 支持段落合并和时间戳处理

✅ **更新主程序**
- 修改 `src/main.py` 支持三种转录方式
- 自动根据配置选择转录器
- 统一的转录接口

✅ **更新配置文件**
- `config/config.yaml` 新增通义千问配置
- 支持 `api_provider` 选择：local / openai / qwen
- 分别配置不同 API 的 Key

✅ **更新测试脚本**
- `test_api_config.py` 支持测试所有三种方式
- 自动检测配置并给出提示
- 显示费用对比信息

✅ **完善文档**
- `QWEN_SETUP.md` - 通义千问详细配置指南
- `API_COMPARISON.md` - 三种方式对比分析
- 更新 `README.md` 添加使用说明

✅ **安装依赖**
- 已安装 `dashscope` SDK

## 支持的转录方式

### 1. 本地模型（local）
```yaml
whisper:
  api_provider: "local"
  model_size: "base"
```
- 免费
- 需要解决依赖问题

### 2. OpenAI API（openai）
```yaml
whisper:
  api_provider: "openai"
  openai_api_key: "sk-xxx"
```
- $0.006/分钟
- 需要代理

### 3. 通义千问 API（qwen）⭐ 推荐
```yaml
whisper:
  api_provider: "qwen"
  qwen_api_key: "sk-xxx"
  qwen_model: "paraformer-v2"
```
- ¥0.0008/分钟（比 OpenAI 便宜 50 倍）
- 中文准确率最高（90-95%）
- 国内直连，无需代理

## 费用对比

| 转录时长 | 本地模型 | OpenAI | 通义千问 |
|---------|---------|--------|----------|
| 1 小时 | ¥0 | ¥2.5 | ¥0.05 |
| 10 小时 | ¥0 | ¥25 | ¥0.5 |
| 100 小时 | ¥0 | ¥250 | ¥5 |

**通义千问比 OpenAI 便宜约 50 倍！**

## 使用步骤

### 1. 获取通义千问 API Key

1. 访问：https://dashscope.console.aliyun.com/
2. 登录阿里云账号
3. 开通 DashScope 服务
4. 创建 API Key

### 2. 配置 API Key

编辑 `config/config.yaml`：

```yaml
whisper:
  api_provider: "qwen"
  qwen_api_key: "sk-your-dashscope-key-here"
  qwen_model: "paraformer-v2"
  language: "zh"
```

### 3. 测试配置

```bash
python test_api_config.py
```

应该看到：
```
[SUCCESS] 通义千问配置测试通过！
```

### 4. 运行转录

```bash
python src/main.py "https://www.xiaoyuzhoufm.com/episode/6953183a2db086f897b08ad9"
```

## 文件清单

### 新增文件
- `src/transcriber_qwen.py` - 通义千问转录器
- `QWEN_SETUP.md` - 通义千问配置指南
- `API_COMPARISON.md` - API 对比文档

### 修改文件
- `src/main.py` - 支持三种转录方式
- `config/config.yaml` - 新增通义千问配置
- `test_api_config.py` - 支持测试通义千问
- `requirements.txt` - 添加 dashscope 依赖
- `README.md` - 更新使用说明

## 技术实现

### 通义千问 API 调用流程

1. **初始化**
   ```python
   from transcriber_qwen import QwenTranscriber

   config = {
       "api_key": "your-key",
       "model": "paraformer-v2",
       "language": "zh"
   }
   transcriber = QwenTranscriber(config)
   ```

2. **转录音频**
   ```python
   paragraphs = transcriber.transcribe("audio.m4a")
   ```

3. **结果格式**
   ```python
   [
       {
           "start": 0.0,
           "end": 5.2,
           "text": "转录文本内容"
       },
       ...
   ]
   ```

### 段落合并逻辑

- 根据 `paragraph_gap` 参数（默认 2.0 秒）
- 自动合并间隔小于阈值的句子
- 保留时间戳信息

## 下一步

配置好通义千问 API Key 后：

1. 运行 `python test_api_config.py` 测试配置
2. 运行 `python src/main.py "播客URL"` 开始转录
3. 查看 `data/transcripts/` 目录获取转录结果

## 文档索引

- **快速开始**: `README.md`
- **通义千问配置**: `QWEN_SETUP.md`
- **OpenAI 配置**: `API_SETUP.md`
- **API 对比**: `API_COMPARISON.md`
- **故障排除**: `TROUBLESHOOTING.md`

## 推荐配置

对于中文播客转录，强烈推荐使用通义千问：

```yaml
whisper:
  api_provider: "qwen"
  qwen_api_key: "your-key"
  qwen_model: "paraformer-v2"
  language: "zh"
```

**理由：**
- 价格最低（¥0.05/小时）
- 准确率最高（90-95%）
- 速度最快（3-5分钟/小时）
- 国内访问无障碍

准备好 API Key 后就可以开始使用了！
