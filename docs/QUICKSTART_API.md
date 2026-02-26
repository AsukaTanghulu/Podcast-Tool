# 快速开始 - API 模式

## 当前状态

✅ 项目已配置为使用 Whisper API 模式
✅ 音频下载功能正常
✅ 数据库功能正常
⏳ 需要配置 OpenAI API Key

## 三步开始使用

### 步骤 1：获取 API Key

访问 https://platform.openai.com/api-keys 获取 API Key

### 步骤 2：配置 API Key

编辑 `config/config.yaml`，填入你的 API Key：

```yaml
whisper:
  use_api: true
  api_key: "sk-your-actual-api-key-here"  # 替换这里
  language: "zh"
```

### 步骤 3：测试配置

```bash
# 测试 API 配置是否正确
python test_api_config.py

# 如果测试通过，运行完整流程
python src/main.py "https://www.xiaoyuzhoufm.com/episode/6953183a2db086f897b08ad9"
```

## 预期结果

程序将：
1. 下载播客音频（约 86MB）
2. 调用 Whisper API 进行转录
3. 保存转录结果到 `data/transcripts/`
4. 显示转录预览

## 费用说明

- Whisper API：$0.006/分钟
- 测试播客约 60 分钟：约 $0.36

## 需要帮助？

- API 配置详细说明：查看 `API_SETUP.md`
- 故障排除：查看 `TROUBLESHOOTING.md`
- 项目文档：查看 `README.md`

## 后续开发

转录功能完成后，下一步将实现：
- 笔记生成（规则引擎 + AI）
- Web 界面
- 更多功能优化
