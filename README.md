# 播客分析工具

一款自动转录播客音频并生成结构化笔记的工具，现已支持纪录片文件上传

## 功能特性

- 🎙️ **音频获取**: 自动从页面提取并下载音频
- 🎬 **纪录片支持**: 支持上传音频/视频文件进行转录（扩展功能）
  - 支持音频格式：MP3, WAV, M4A, FLAC, AAC, OPUS
  - 支持视频格式：MP4, FLV, WEBM, MKV, AVI, MOV
  - 最大文件大小：2GB
  - 自动格式验证和错误提示
- 📝 **语音转录**: 使用通义千问 API 进行高精度转录
  - 支持中英文混合识别
  - 自动说话人分离
  - 价格低、准确率高
  - 支持多种模型选择（paraformer-v2, fun-asr 等）
- 📊 **智能分析**: 提供规则引擎和 AI 两种笔记生成模式
- 💬 **AI 对话**: 基于转录全文与 AI 进行深度对话
  - 支持通义千问和 DeepSeek
  - AI 回答基于播客实际内容
  - 帮助复习要点、深化理解、激发思考
  - 保留完整对话历史
- 💾 **数据管理**: 完整的数据存储和检索功能
- 🌐 **Web 界面**: 友好的 Web 操作界面
- 👥 **说话人管理**: 对话式布局展示，支持说话人重命名和筛选
- 📁 **栏目分类**: 支持播客栏目分类，按栏目组织文件存储
  - 自动按栏目创建文件夹
  - MD 和 PDF 文件分开存储
  - 支持按栏目筛选播客

## 快速开始

### 环境要求

- Python 3.11+
- Windows 10+
- 至少 2GB 内存

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

#### 使用通义千问 API

```bash
# 1. 在 .env 文件中配置 API Key
QWEN_API_KEY=your-qwen-api-key-here

# 2. 处理播客
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
│   ├── transcriber_qwen.py # 通义千问转录
│   ├── storage_manager.py  # 存储路径管理
│   └── web/               # Web 界面
├── data/                  # 数据存储（按栏目分类）
│   ├── audio/            # 音频文件
│   │   ├── 科技播客/
│   │   ├── 商业播客/
│   │   └── 未分类/
│   ├── transcripts/      # 转录文本
│   │   ├── 科技播客/
│   │   │   ├── md/      # Markdown 格式
│   │   │   └── pdf/     # PDF 格式
│   │   └── 未分类/
│   └── notes/            # 笔记文件
│       ├── 科技播客/
│       │   ├── md/
│       │   └── pdf/
│       └── 未分类/
├── config/               # 配置文件
│   ├── config.yaml       # 主配置
│   └── prompts.yaml      # AI Prompt 模板
├── docs/                 # 文档
├── logs/                 # 日志文件
├── requirements.txt      # 依赖清单
└── README.md            # 项目说明
```

## 配置说明

编辑 `config/config.yaml` 修改配置：

```yaml
# 通义千问转录配置
whisper:
  language: zh              # 语言：zh/en
  qwen_model: paraformer-v2 # 模型选择
  # 可选模型：
  # - paraformer-v2, paraformer-8k-v2 (0.00008元/秒)
  # - fun-asr, fun-asr-2025-11-07 (0.00022元/秒)

# 存储配置
storage:
  category_based: true      # 按栏目分类存储
  default_category: 未分类  # 默认栏目
  separate_formats: true    # MD 和 PDF 分开存储
```

## Web 界面使用

### 启动 Web 应用

```bash
python run_web.py
```

访问 http://127.0.0.1:5000

### 功能说明

1. **提交播客任务**: 输入播客链接，点击"开始分析"
2. **上传纪录片**: 切换到"纪录片上传"标签页
   - 选择音频或视频文件
   - 可选填写标题（不填则使用文件名）
   - 点击"上传并分析"
   - 实时显示上传进度
3. **重新转录**: 如果转录失败，可以点击"重新转录"按钮
   - 自动使用已下载的文件重新转录
   - 无需重新下载或上传
   - 支持播客和纪录片
4. **查看列表**: 实时显示所有播客和纪录片记录
   - 内容类型徽章区分播客和纪录片
   - 显示原始文件名（纪录片）
   - 失败状态显示"重新转录"按钮
5. **栏目分类**:
   - 为播客设置栏目（如：科技播客、商业播客等）
   - 按栏目筛选播客列表
   - 文件自动按栏目分类存储
6. **查看详情**: 点击"查看详情"查看转录文本和笔记
7. **对话式展示**: 转录结果以对话气泡形式展示，支持说话人分离
8. **说话人管理**: 重命名说话人、按说话人筛选对话
9. **搜索功能**: 全文搜索转录内容
10. **导出功能**: 支持导出 TXT/MD/SRT 格式
11. **生成笔记**: 支持规则引擎和 AI 两种模式
   - 规则引擎：免费，基于 NLP 算法
   - AI 模式：需要 API Key，支持通义千问、DeepSeek 等
12. **AI 对话**: 基于转录内容进行深度对话
   - 选择 AI 提供商（通义千问/DeepSeek）
   - AI 回答基于播客实际内容，不编造信息
   - 支持复习要点、澄清疑惑、深化理解
   - 可清空对话历史重新开始

### API 接口

- `GET /api/podcasts` - 获取播客列表
- `GET /api/podcasts/<id>` - 获取播客详情
- `POST /api/podcasts` - 创建播客任务
- `POST /api/documentaries` - 上传纪录片文件
- `POST /api/podcasts/<id>/retry-transcription` - 重新转录
- `PUT /api/podcasts/<id>/category` - 更新播客栏目
- `POST /api/notes/generate` - 生成笔记
- `POST /api/podcasts/<id>/chat/init` - 初始化 AI 对话
- `POST /api/chat/<session_id>/message` - 发送对话消息
- `GET /api/chat/<session_id>/history` - 获取对话历史
- `POST /api/chat/<session_id>/clear` - 清空对话历史
- `GET /api/transcripts/<id>/speakers` - 获取说话人列表
- `PUT /api/transcripts/<id>/speakers/rename` - 重命名说话人
- `POST /api/transcripts/<id>/export` - 导出转录

## 笔记生成功能

### 规则引擎模式（免费）

- 关键词提取（TF-IDF）
- 关键句提取（TextRank）
- 金句摘录
- 5W1H 分析
- 时间轴生成

### AI 模式（需要 API Key）

支持的 AI 提供商：
- **通义千问**（推荐，性价比高）✅
- **DeepSeek** ✅
- **OpenAI** ✅
- **豆包**（字节跳动）✅
- ~~Claude~~（暂不支持，API 不兼容）

配置方法：在 `.env` 文件中配置 API Key

```env
# 通义千问 API Key
QWEN_API_KEY=your-qwen-api-key-here

# DeepSeek API Key
DEEPSEEK_API_KEY=your-deepseek-api-key-here

# OpenAI API Key (可选)
OPENAI_API_KEY=your-openai-api-key-here

# 豆包 API Key (可选)
DOUBAO_API_KEY=your-doubao-api-key-here
```

**注意**：
- Base URL 已在代码中配置，无需在 config.yaml 中添加
- 详细说明请查看 [docs/AI_NOTE_PROVIDERS.md](docs/AI_NOTE_PROVIDERS.md)

## 说话人分离功能

详细使用说明请查看 [docs/SPEAKER_DIARIZATION.md](docs/SPEAKER_DIARIZATION.md)

### 主要特性

- 自动识别不同说话人
- 对话式气泡布局展示
- 说话人重命名
- 按说话人筛选对话
- 全文搜索
- 导出 TXT/MD/SRT 格式

## 注意事项

1. 转录速度取决于音频长度和网络状况
2. 仅供个人学习使用，请尊重版权
3. API 调用会产生费用，请注意控制成本

## 许可证

MIT License

## 更新日志

### v3.7.1 (2026-02-27)
- ✅ 修复重命名 bug：文件名现在使用播客名称而不是 podcast_id
- ✅ 添加 audio_file_path 字段到数据库，准确追踪音频文件
- ✅ 优化文件查找逻辑，支持多次重命名
- ✅ 确认栏目迁移功能正常工作
- ✅ 音频文件不按栏目分类（保持在根目录）
- ✅ 转录文件和笔记文件按栏目自动迁移

### v3.7.0 (2026-02-27)
- ✅ 实现说话人分离功能（对话式布局）
- ✅ 修改 MD 文件生成逻辑，使用对话式布局（方案 2）
- ✅ 添加 JSON 格式转录文件，支持 Web 界面对话式展示
- ✅ 转录文件包含说话人信息（speaker_id）
- ✅ Web 界面对话气泡式布局（左右交替，不同颜色）
- ✅ 说话人重命名功能
- ✅ 按说话人筛选对话
- ✅ 全文搜索功能
- ✅ 导出功能支持说话人标注（TXT/MD/SRT）

### v3.6.1 (2026-02-27)
- ✅ 修复笔记生成 API Key 加载问题
- ✅ 修复环境变量映射被覆盖的 bug（QWEN_API_KEY 未正确加载到 ai.qwen_api_key）
- ✅ AI 对话功能默认使用 DeepSeek
- ✅ AI 对话 Prompt 移至 prompts.yaml，方便用户配置
- ✅ 前端界面优化，明确区分笔记生成和 AI 对话功能

### v3.6.0 (2026-02-27)
- ✅ 修复栏目设置后文件不迁移的问题
- ✅ 实现文件自动迁移到新栏目文件夹
- ✅ 修复预览文件找不到的问题
- ✅ 改进音频文件重命名功能
- ✅ 重命名播客时音频文件自动改名为播客名称
- ✅ 支持多次重命名（不再依赖文件名包含 podcast_id）
- ✅ 从数据库获取文件路径，更准确可靠
- ✅ 笔记文件命名规范化：`{播客名称}_{模型类型}_笔记.md`
- ✅ 修复文件预览路径转义问题（Windows 反斜杠问题）
- ✅ 移除不兼容的 Claude AI 支持
- ✅ 确认支持 4 个 AI 提供商：qwen, deepseek, openai, doubao

### v3.5.0 (2026-02-27)
- ✅ 添加 AI 对话功能
- ✅ 基于转录全文进行深度对话
- ✅ 支持通义千问和 DeepSeek
- ✅ AI 回答立足于播客实际内容
- ✅ 支持对话历史管理
- ✅ 帮助用户复习和深化理解

### v3.4.0 (2026-02-27)
- ✅ 添加手动重新转录功能
- ✅ 转录失败时显示"重新转录"按钮
- ✅ 自动查找已下载的音频文件
- ✅ 支持播客和纪录片重新转录
- ✅ 更新或创建转录记录

### v3.3.0 (2026-02-27)
- ✅ 添加纪录片文件上传功能
- ✅ 支持音频和视频文件格式验证
- ✅ 实现文件上传进度显示
- ✅ 添加内容类型区分（播客/纪录片）
- ✅ 支持本地文件转录

### v3.2.0 (2026-02-27)
- ✅ 添加播客栏目分类功能
- ✅ 实现按栏目分类存储文件
- ✅ MD 和 PDF 文件分开存储
- ✅ 支持按栏目筛选播客
- ✅ 未分类播客自动归入"未分类"文件夹
- ✅ 修复模型配置不生效的问题

### v3.1.0 (2026-02-27)
- ✅ 添加播客栏目字段
- ✅ 实现栏目设置和重命名功能
- ✅ 在列表和详情页显示栏目徽章

### v3.0.0 (2026-02-27)
- ✅ 实现说话人分离功能
- ✅ 添加对话式布局展示
- ✅ 支持说话人重命名和筛选
- ✅ 添加搜索和导出功能
- ✅ 简化项目结构，仅保留通义千问 API

### v2.6.0 (2026-02-24)
- ✅ 完成 Web 端功能全面测试
- ✅ 所有核心 API 测试通过
- ✅ 规则引擎笔记生成测试通过
- ✅ AI 笔记生成测试通过（通义千问）

### v2.5.0 (2026-02-24)
- ✅ 完成 Phase 3 Web 界面开发
- ✅ 实现 Flask 后端 API
- ✅ 实现前端页面和交互

### v1.0.0 (2026-02-24)
- 初始版本
- 实现音频获取和转录功能
