# Phase 4.1 讲话人识别功能实现进度

**开始时间**: 2026-02-24 16:30
**当前状态**: 🔄 进行中

---

## 已完成的工作

### 1. 需求确认 ✅
- 技术方案: pyannote.audio
- 应用场景: 可选功能（用户可选择是否启用）
- 标注格式: 支持自定义讲话人名称

### 2. 文档更新 ✅
- 更新 plan.md 到 v2.9
- 添加 Phase 4.1 详细设计文档
- 记录技术方案和实现步骤

### 3. 依赖包配置 ✅
- 更新 requirements.txt
- 添加 pyannote.audio==3.1.1
- 添加 torch>=2.0.0
- 添加 torchaudio>=2.0.0

### 4. 核心模块实现 ✅

#### 4.1 讲话人分离模块 (src/diarization.py)
```python
class SpeakerDiarizer:
    - __init__(): 初始化，加载 pyannote.audio 模型
    - _load_pipeline(): 加载 pipeline
    - diarize(): 对音频进行讲话人分离
    - merge_with_transcript(): 将讲话人信息合并到转录结果
    - _find_best_speaker(): 找到与转录片段重叠最多的讲话人
    - get_speaker_list(): 获取所有讲话人列表
```

**功能**:
- 使用 pyannote.audio 进行讲话人分离
- 返回讲话人片段列表（时间范围 + 讲话人ID）
- 将讲话人信息与转录结果合并
- 支持配置最小/最大讲话人数

#### 4.2 讲话人管理模块 (src/speaker_manager.py)
```python
class SpeakerManager:
    - __init__(): 初始化
    - save_speakers(): 保存播客的讲话人列表
    - update_speaker_name(): 更新讲话人自定义名称
    - get_speakers(): 获取播客的讲话人映射
    - get_speaker_display_name(): 获取讲话人显示名称
    - has_diarization(): 检查播客是否有讲话人信息
```

**功能**:
- 管理播客的讲话人信息
- 支持自定义讲话人名称
- 提供讲话人查询接口

### 5. 数据库扩展 ✅

#### 5.1 新增 speakers 表
```sql
CREATE TABLE speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    podcast_id TEXT NOT NULL,
    speaker_id TEXT NOT NULL,      -- SPEAKER_00, SPEAKER_01, etc.
    speaker_name TEXT,              -- 用户自定义名称
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id) ON DELETE CASCADE
);
```

#### 5.2 扩展 transcripts 表
```sql
ALTER TABLE transcripts ADD COLUMN has_diarization BOOLEAN DEFAULT 0;
```

### 6. 配置文件更新 ✅
- 添加 diarization 配置节
- 配置项包括: enabled, provider, hf_token, model, min_speakers, max_speakers
- 默认关闭讲话人识别功能

---

## 待完成的工作

### 7. 集成到转录流程 ⏳
**文件**: src/transcriber.py

**需要修改**:
1. 添加 `enable_diarization` 参数到 `transcribe()` 方法
2. 在转录完成后调用讲话人分离
3. 合并讲话人信息到转录结果
4. 保存讲话人信息到数据库

**伪代码**:
```python
def transcribe(self, audio_path: str, enable_diarization: bool = False):
    # 1. 执行转录
    paragraphs = self._transcribe_audio(audio_path)

    # 2. 如果启用讲话人识别
    if enable_diarization:
        diarizer = SpeakerDiarizer(config)
        diarization = diarizer.diarize(audio_path)
        paragraphs = diarizer.merge_with_transcript(paragraphs, diarization)

        # 保存讲话人信息
        speakers = diarizer.get_speaker_list(diarization)
        speaker_manager.save_speakers(podcast_id, speakers)

    return paragraphs
```

### 8. 更新转录输出格式 ⏳
**文件**: src/transcript_formatter.py

**需要修改**:
1. Markdown 格式添加讲话人标注
2. PDF 格式添加讲话人标注
3. 支持自定义讲话人名称显示

**Markdown 格式示例**:
```markdown
## 段落 1 [00:00:00 - 00:00:15]

**[张三]**: 大家好，欢迎来到我们的播客。

## 段落 2 [00:00:15 - 00:00:30]

**[李四]**: 今天我们要讨论的话题是...
```

### 9. Web API 扩展 ⏳
**文件**: src/web/app.py

**新增接口**:
```python
# 获取讲话人列表
@app.route('/api/podcasts/<podcast_id>/speakers', methods=['GET'])
def get_speakers(podcast_id):
    """返回讲话人列表和自定义名称"""

# 更新讲话人名称
@app.route('/api/podcasts/<podcast_id>/speakers/<speaker_id>', methods=['PUT'])
def update_speaker_name(podcast_id, speaker_id):
    """更新讲话人自定义名称"""

# 重新生成带讲话人的转录
@app.route('/api/podcasts/<podcast_id>/regenerate-transcript', methods=['POST'])
def regenerate_transcript(podcast_id):
    """重新生成转录，可选择是否启用讲话人识别"""
```

### 10. 前端界面实现 ⏳
**文件**: src/web/static/js/main.js, src/web/templates/index.html

**新增功能**:
1. 在转录时添加"启用讲话人识别"复选框
2. 在播客详情页显示讲话人列表
3. 提供重命名讲话人的界面
4. 显示带讲话人标注的转录预览

**UI 设计**:
```
播客详情页
├── 基本信息
├── 转录记录
│   └── [预览] [下载] [重新生成]
├── 讲话人管理 (新增)
│   ├── 讲话人1: [输入框] [保存]
│   ├── 讲话人2: [输入框] [保存]
│   └── ...
└── 笔记记录
```

### 11. 测试和优化 ⏳
**测试内容**:
1. 讲话人分离准确度测试
2. 转录与讲话人合并测试
3. 自定义名称功能测试
4. 性能测试（处理时间、内存占用）
5. 边界情况测试（单人、多人、噪音）

**优化方向**:
1. 缓存讲话人分离结果
2. 支持 GPU 加速
3. 优化合并算法
4. 添加进度显示

---

## 技术要点

### pyannote.audio 使用说明

1. **安装依赖**:
```bash
pip install pyannote.audio torch torchaudio
```

2. **获取 HuggingFace Token**:
- 访问 https://huggingface.co/
- 注册账号并登录
- 访问 Settings -> Access Tokens
- 创建新的 token（需要 read 权限）
- 接受模型使用协议: https://huggingface.co/pyannote/speaker-diarization-3.1

3. **基本使用**:
```python
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token="YOUR_HF_TOKEN"
)

diarization = pipeline("audio.wav")

for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"{turn.start:.1f}s - {turn.end:.1f}s: {speaker}")
```

### 性能考虑

1. **处理时间**:
   - 讲话人分离约为音频时长的 0.5-1 倍
   - 1小时音频约需 30-60 分钟处理

2. **内存占用**:
   - 模型大小约 1GB
   - 运行时内存约 2-4GB

3. **GPU 加速**:
   - 支持 CUDA
   - GPU 可将处理速度提升 5-10 倍

---

## 下一步计划

1. **立即执行**: 集成到转录流程（步骤 7）
2. **然后**: 更新转录输出格式（步骤 8）
3. **接着**: 实现 Web API（步骤 9）
4. **最后**: 实现前端界面（步骤 10）
5. **完成**: 测试和优化（步骤 11）

---

## 注意事项

1. **HuggingFace Token**: 用户需要自行申请，不能硬编码在代码中
2. **模型下载**: 首次使用需要下载约 1GB 模型，需要提示用户
3. **处理时间**: 讲话人识别会显著增加处理时间，需要明确告知用户
4. **准确度**: 讲话人识别准确度受音频质量影响，需要设置合理预期
5. **可选功能**: 默认关闭，避免影响现有用户体验

---

**更新时间**: 2026-02-24 16:40
**完成进度**: 60% (6/10 步骤完成)
