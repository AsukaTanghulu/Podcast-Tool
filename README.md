# 播客分析工具

一款自动转录播客音频并生成结构化笔记的工具

## 功能特性

- 🎙️ **音频获取**: 自动从页面提取并下载音频
- 📝 **语音转录**: 支持三种转录方式
  - 本地模型（Whisper）
  - OpenAI Whisper API
  - 通义千问 API（推荐，价格低、准确率高）
- 📊 **智能分析**: 提供规则引擎和 AI 两种笔记生成模式
- 💾 **数据管理**: 完整的数据存储和检索功能
- 🌐 **Web 界面**: 友好的 Web 操作界面（开发中）

## 快速开始

### 环境要求

- Python 3.11+
- Windows 10+
- 至少 4GB 内存

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API Keys（重要！）

**为了安全，本项目使用环境变量管理 API Keys，不在配置文件中存储明文密钥。**

1. 复制环境变量示例文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的 API Keys：
```env
QWEN_API_KEY=your-qwen-api-key-here
DEEPSEEK_API_KEY=your-deepseek-api-key-here
```

3. `.env` 文件已在 `.gitignore` 中，不会被提交到 Git

详细配置说明请查看 [SECURITY.md](SECURITY.md)

### 基础使用

#### 方式 1：使用通义千问 API（推荐）

```bash
# 1. 在 .env 文件中配置 API Key
QWEN_API_KEY=your-qwen-api-key-here

# 2. 处理播客
python src/main.py "https://www.xiaoyuzhoufm.com/episode/xxxxx"
```

#### 方式 2：使用 OpenAI API

```bash
# 配置 OpenAI API Key
whisper:
  api_provider: "openai"
  openai_api_key: "your-key"

python src/main.py "https://www.xiaoyuzhoufm.com/episode/xxxxx"
```

详细配置：查看 `API_SETUP.md`

#### 方式 3：使用本地模型

```bash
# 需要先解决依赖问题（见 TROUBLESHOOTING.md）
whisper:
  api_provider: "local"
  model_size: "base"

python src/main.py "https://www.xiaoyuzhoufm.com/episode/xxxxx"
```

## 项目结构

```
podcast-analyzer/
├── src/                    # 源代码
│   ├── main.py            # 主程序入口
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库操作
│   ├── audio_fetcher.py   # 音频获取
│   ├── transcriber.py     # 语音识别
│   └── web/               # Web 界面（开发中）
├── data/                  # 数据存储
│   ├── audio/            # 音频文件
│   ├── transcripts/      # 转录文本
│   └── notes/            # 笔记文件
├── config/               # 配置文件
│   ├── config.yaml       # 主配置
│   └── prompts.yaml      # AI Prompt 模板
├── logs/                 # 日志文件
├── models/               # Whisper 模型
├── requirements.txt      # 依赖清单
└── plan.md              # 开发计划

```

## 配置说明

编辑 `config/config.yaml` 修改配置：

```yaml
# Whisper 模型配置
whisper:
  model_size: "medium"  # 可选: tiny, base, small, medium, large
  device: "cpu"
  compute_type: "int8"
  language: "zh"
```

## 开发计划

- [x] Phase 1: 音频下载 + 转录
- [x] Phase 2: 笔记生成（规则引擎 + AI）
- [x] Phase 3: Web 界面（基础版）
- [ ] Phase 4: 优化与扩展

详见 [plan.md](plan.md)

## Web 界面使用

### 启动 Web 应用

```bash
python run_web.py
```

访问 http://127.0.0.1:5000

### 功能说明

1. **提交播客任务**: 输入播客链接，点击"开始分析"
2. **查看播客列表**: 实时显示所有播客记录和处理状态
3. **查看详情**: 点击"查看详情"查看转录文本和笔记
4. **生成笔记**: 支持规则引擎和 AI 两种模式
   - 规则引擎：免费，基于 NLP 算法
   - AI 模式：需要 API Key，支持通义千问、DeepSeek 等

### API 接口

- `GET /api/podcasts` - 获取播客列表
- `GET /api/podcasts/<id>` - 获取播客详情
- `POST /api/podcasts` - 创建播客任务
- `POST /api/notes/generate` - 生成笔记
- `GET /api/files/<path>` - 下载文件

## 笔记生成功能

### 规则引擎模式（免费）

- 关键词提取（TF-IDF）
- 关键句提取（TextRank）
- 金句摘录
- 5W1H 分析
- 时间轴生成

### AI 模式（需要 API Key）

支持的 AI 提供商：
- 通义千问（推荐，性价比高）
- DeepSeek
- OpenAI
- 豆包（字节跳动）
- Claude

配置方法：编辑 `config/config.yaml`

```yaml
ai:
  default_provider: "qwen"
  qwen_api_key: "your-key"
  qwen_model: "qwen-plus"
```

## 注意事项

1. 首次运行会自动下载 Whisper 模型（约 1.5GB）
2. 转录速度取决于 CPU 性能，1 小时音频约需 10-20 分钟
3. 仅供个人学习使用，请尊重版权

## 许可证

MIT License

## 更新日志

### v2.6.0 (2026-02-24)
- ✅ 完成 Web 端功能全面测试
- ✅ 所有核心 API 测试通过
- ✅ 规则引擎笔记生成测试通过
- ✅ AI 笔记生成测试通过（通义千问）
- ✅ 修复 run_web.py 导入路径问题
- ✅ 生成完整测试报告（WEB_TEST_REPORT.md）

### v2.5.0 (2026-02-24)
- ✅ 完成 Phase 3 Web 界面开发
- ✅ 实现 Flask 后端 API
- ✅ 实现前端页面和交互
- ✅ 支持 Web 界面生成笔记

### v2.4.0 (2026-02-24)
- ✅ 添加豆包和通义千问 AI 笔记支持
- ✅ 测试通义千问 API 成功

### v2.3.0 (2026-02-24)
- ✅ 完成 Phase 2 笔记生成功能
- ✅ 实现规则引擎笔记生成
- ✅ 实现 AI 笔记生成框架

### v2.2.0 (2026-02-24)
- ✅ 移除 JSON 格式转录输出
- ✅ 直接生成 Markdown 和 PDF 格式

### v1.0.0 (2026-02-24)
- 初始版本
- 实现音频获取和转录功能
