# 讲话人识别功能使用指南

## 快速开始

### 步骤 1: 安装 pyannote.audio

```bash
python install_pyannote.py
```

或者手动安装：
```bash
pip install pyannote.audio==3.1.1
```

### 步骤 2: 配置 HuggingFace Token

```bash
python configure_hf_token.py
```

按照提示输入你的 HuggingFace token。

**如何获取 Token**:
1. 访问 https://huggingface.co/
2. 注册并登录
3. 进入 Settings -> Access Tokens
4. 创建新的 token（需要 read 权限）
5. 接受模型使用协议: https://huggingface.co/pyannote/speaker-diarization-3.1

### 步骤 3: 测试功能

```bash
python test_diarization_with_model.py
```

这将：
- 检查配置
- 加载模型（首次运行会下载约 1GB）
- 对测试音频进行讲话人识别
- 显示识别结果

---

## 手动配置

如果你不想使用脚本，可以手动编辑配置文件：

**编辑 `config/config.yaml`**:
```yaml
diarization:
  enabled: false  # 改为 true 启用
  provider: "pyannote"
  hf_token: "YOUR_TOKEN_HERE"  # 填入你的 token
  model: "pyannote/speaker-diarization-3.1"
  min_speakers: 1
  max_speakers: 10
```

---

## 使用示例

### 基本使用

```python
from diarization import SpeakerDiarizer

# 初始化
diarizer = SpeakerDiarizer({
    'hf_token': 'YOUR_TOKEN',
    'model': 'pyannote/speaker-diarization-3.1',
    'min_speakers': 1,
    'max_speakers': 10
})

# 执行讲话人识别
diarization = diarizer.diarize('audio.wav')

# 结果格式
# [
#     {"start": 0.0, "end": 5.2, "speaker": "SPEAKER_00"},
#     {"start": 5.2, "end": 10.5, "speaker": "SPEAKER_01"},
#     ...
# ]
```

### 与转录结果合并

```python
# 转录结果
transcript = [
    {"start": 0.0, "end": 5.0, "text": "Hello everyone"},
    {"start": 5.0, "end": 10.0, "text": "Welcome to our podcast"},
]

# 合并
merged = diarizer.merge_with_transcript(transcript, diarization)

# 结果格式
# [
#     {"start": 0.0, "end": 5.0, "text": "Hello everyone", "speaker": "SPEAKER_00"},
#     {"start": 5.0, "end": 10.0, "text": "Welcome to our podcast", "speaker": "SPEAKER_01"},
# ]
```

### 管理讲话人名称

```python
from speaker_manager import SpeakerManager

manager = SpeakerManager(db)

# 保存讲话人列表
manager.save_speakers('podcast_id', ['SPEAKER_00', 'SPEAKER_01'])

# 更新讲话人名称
manager.update_speaker_name('podcast_id', 'SPEAKER_00', '张三')
manager.update_speaker_name('podcast_id', 'SPEAKER_01', '李四')

# 获取显示名称
name = manager.get_speaker_display_name('podcast_id', 'SPEAKER_00')
# 返回: "张三"
```

---

## 性能说明

### 处理时间

- **CPU**: 约为音频时长的 0.5-1 倍
  - 1小时音频 → 30-60 分钟处理
- **GPU**: 约为音频时长的 0.1-0.2 倍
  - 1小时音频 → 6-12 分钟处理

### 内存占用

- **模型大小**: 约 1GB
- **运行时内存**: 2-4GB
- **建议**: 至少 8GB RAM

### 首次使用

- 首次运行会下载模型文件（约 1GB）
- 下载时间取决于网络速度
- 模型会缓存到本地，后续使用无需重新下载

---

## 常见问题

### Q1: 提示 "HuggingFace token not configured"

**解决方法**:
```bash
python configure_hf_token.py
```

### Q2: 提示 "pyannote.audio not installed"

**解决方法**:
```bash
python install_pyannote.py
```

### Q3: 提示 "You need to accept the model license"

**解决方法**:
1. 访问 https://huggingface.co/pyannote/speaker-diarization-3.1
2. 登录你的账号
3. 点击 "Agree and access repository"

### Q4: 下载模型很慢

**解决方法**:
- 使用稳定的网络连接
- 考虑使用代理
- 或者手动下载模型文件

### Q5: 内存不足

**解决方法**:
- 关闭其他程序释放内存
- 处理较短的音频片段
- 使用更小的模型（如果可用）

### Q6: 识别准确度不高

**可能原因**:
- 音频质量差（噪音、回声）
- 讲话人声音相似
- 频繁切换讲话人

**改进方法**:
- 使用高质量音频
- 调整 min_speakers 和 max_speakers 参数
- 考虑音频预处理（降噪等）

---

## 技术细节

### 模型信息

- **模型**: pyannote/speaker-diarization-3.1
- **提供商**: pyannote.audio
- **许可证**: MIT License
- **论文**: https://arxiv.org/abs/2012.01952

### 算法流程

1. **语音活动检测** (VAD): 检测音频中的语音片段
2. **说话人嵌入提取**: 为每个语音片段提取特征向量
3. **聚类**: 将相似的特征向量聚类为同一讲话人
4. **后处理**: 平滑和优化讲话人边界

### 输出格式

```python
{
    "start": float,      # 开始时间（秒）
    "end": float,        # 结束时间（秒）
    "speaker": str       # 讲话人ID（SPEAKER_00, SPEAKER_01, ...）
}
```

---

## 下一步

完成基础测试后，可以：

1. **集成到转录流程**: 在转录时自动进行讲话人识别
2. **更新输出格式**: 在转录文本中标注讲话人
3. **实现 Web 界面**: 提供可视化的讲话人管理
4. **优化性能**: 使用 GPU 加速、缓存结果等

---

## 参考资源

- pyannote.audio 文档: https://github.com/pyannote/pyannote-audio
- HuggingFace 模型页: https://huggingface.co/pyannote/speaker-diarization-3.1
- 论文: https://arxiv.org/abs/2012.01952

---

**更新时间**: 2026-02-24
**版本**: 1.0
