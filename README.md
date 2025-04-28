# 🎬 MADvolution_剪辑进化
> 一款基于AI的自动视频剪辑工具，10分钟即可完成传统48小时的工作量

## 📖 目录
- [✨ 核心特性](#-核心特性)
- [⚙️ 系统要求](#️-系统要求)
- [🚀 快速开始](#-快速开始)
- [🎵 音乐分析模块](#-音乐分析模块配置-1_音乐自动分析)
- [🤖 AI集成使用](#-ai大模型集成使用)
- [✂️ 视频切割模块](#️-视频切割模块配置-2_mad素材切割)
- [🎞️ 视频拼接模块](#️-视频拼接模块配置-3_mad素材拼接)
- [❓ 常见问题](#-常见问题)
- [🤝 贡献指南](#-贡献指南)
- [📜 开源协议](#-开源协议)

## ✨ 核心特性

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)

✅ **极速剪辑** - AI自动处理，10分钟完成传统48小时工作量  
✅ **全流程解决方案** - 从音乐分析到视频拼接一站式完成  
✅ **智能节奏匹配** - 基于音乐节拍的精准画面同步  
✅ **模块化架构** - 灵活配置满足不同剪辑需求  
✅ **完全开源** - MIT协议自由使用与二次开发

## ⚙️ 系统要求
| 组件 | 要求 |
|------|------|
| Python | 3.8+ |
| FFmpeg | 最新版 |
| 内存 | 8GB+ |
| 显卡 | 支持CUDA(可选) |

## 🚀 快速开始
```bash
# 克隆仓库
git clone https://github.com/your-repo/MAD-editor.git
cd MAD-editor

# 安装依赖
pip install -r requirements.txt
```

## 🎵 音乐分析模块配置 (1_音乐自动分析)

### 环境配置
```bash
# 安装Python依赖
pip install librosa==0.10.1 pydub==0.25.1 matplotlib==3.8.2 numpy==1.26.0

# 安装音频处理工具
# Windows安装ffmpeg
winget install Gyan.FFmpeg
# Linux安装
sudo apt install ffmpeg
```

### 输入文件规范
- 支持格式: .flac/.mp3/.wav
- 采样率: 推荐44100Hz或48000Hz
- 比特率: 不低于192kbps

### 配置文件详解
```python
# config.py 完整配置
ANALYSIS_SETTINGS = {
    'bpm_detection': True,     # 启用BPM检测
    'beat_sensitivity': 0.8,   # 节拍敏感度(0-1)
    'segment_length': 15,      # 分段长度(秒)
    'sample_rate': 44100,      # 重采样率
    'hop_length': 512,         # 分析帧间隔
    'n_fft': 2048              # FFT窗口大小
}

# 歌词文件处理
LYRIC_SETTINGS = {
    'max_line_chars': 20,      # 单行最大字符数
    'min_duration': 2.5        # 最小显示时长(秒)
}
```

### 输出文件说明
- clip_guide_template.py: 自动生成的剪辑指导模板
- beat_timeline.json: 节拍时间轴数据
- analysis_report.html: 可视化分析报告

## 🤖 AI大模型集成使用

### 模型配置
```python
# config.py 新增AI配置
AI_SETTINGS = {
    'model_name': 'gpt-4-turbo',  # 使用模型
    'temperature': 0.7,          # 创意度(0-1)
    'max_tokens': 4096,          # 最大输出长度
    'prompt_version': 'v2.3'     # 提示词版本
}
```

### 提示词工程
```markdown
# 标准提示词结构
1. **角色设定**：明确AI作为MAD专家的身份
2. **输入规范**：要求提供音乐分析文件和字幕文件
3. **输出要求**：
   - 严格遵循`第X集 mm:ss.ms~mm:ss.ms`时间格式
   - 重复歌词差异化处理
   - 按三幕剧结构分配剧情
4. **错误防御**：
   - 禁止省略任何歌词对应分镜
   - 禁止使用未标注的素材
```

### 工作流程
1. 预处理：
   ```bash
   python prepare_input.py --music 音乐文件 --subtitle 字幕文件
   ```
2. AI生成脚本：
   ```bash
   python generate_script.py --input 分析结果.json --output 分镜脚本.md
   ```
3. 后处理验证：
   ```bash
   python validate_script.py --script 分镜脚本.md
   ```

### 输出示例
```markdown
| 时间段 | 歌词内容 | 集数+时间码 | 画面对应内容 |
|--------|----------|----------------|--------------|
| 00:29-00:37 | 电视一直闪... | 第3集 10:48.03~10:55.03 | 灯独自看电视的侧脸 |
| 00:37-00:44 | 你待我的好... | 第5集 15:20.10~15:27.10 | 乐队练习室争吵场景 |
```

## ✂️ 视频切割模块配置 (2_mad素材切割)

### 环境要求
```bash
# 安装OpenCV和视频处理依赖
pip install opencv-python==4.8.0 numpy==1.26.0

# 安装FFmpeg (如果尚未安装)
winget install Gyan.FFmpeg  # Windows
sudo apt install ffmpeg     # Linux
```

### 输入视频规范
- 格式: MP4/MOV
- 分辨率: 建议1080p或以上
- 帧率: 23.976/24/25/29.97/30/50/60fps
- 编码: H.264/H.265

### 配置文件参数
```python
# auto_cut_video.py 关键参数
CUT_SETTINGS = {
    'min_scene_duration': 2.0,    # 最小场景时长(秒)
    'threshold': 30.0,            # 场景变化阈值
    'fade_duration': 0.5,         # 淡入淡出时长
    'output_codec': 'libx264',    # 输出编码格式
    'output_preset': 'fast'       # 编码预设
}
```

### 使用说明
```bash
# 基本用法
python 2_mad素材切割/auto_cut_video.py --input 番剧原片/ --output output/

# 高级选项
python 2_mad素材切割/auto_cut_video.py \
    --input 番剧原片/ \
    --output output/ \
    --min-duration 2.0 \
    --threshold 25.0 \
    --fade 0.3
```

### 输出文件说明
- 文件名格式: {序号}_{时间码}.mp4
- 元数据文件: cuts_metadata.json

## 🎞️ 视频拼接模块配置 (3_mad素材拼接)

### FFmpeg环境配置
```bash
# Windows安装FFmpeg
winget install Gyan.FFmpeg

# Linux安装
sudo apt install ffmpeg

# 验证安装
ffmpeg -version
```

### 核心功能配置
```python
# video_editor.py 关键参数
EDITOR_CONFIG = {
    'transition_style': 'crossfade',  # 转场效果
    'min_clip_duration': 2.0,        # 最小片段时长
    'max_clip_duration': 5.0,        # 最大片段时长
    'output_resolution': (1920, 1080) # 输出分辨率
}
```

### 文件命名规范
- 视频素材文件名必须以数字开头 (如: "001_场景.mp4")
- 音乐文件格式支持: .flac/.mp3
- 输出目录自动创建

### 音频处理参数
```python
# 音频淡入效果参数
audio_params = {
    'fade_in_duration': 2.0,  # 淡入时长(秒)
    'volume': 0.8,           # 背景音乐音量(0-1)
    'delay': 0               # 音频延迟(秒)
}
```

## 📝 常见问题
❓ **音乐分析不准确**
- 确保输入音频质量良好
- 调整config.py中的敏感度参数

❓ **视频拼接不同步**
- 检查素材帧率是否一致
- 重新生成时间轴标记

## 🤝 贡献指南
1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 发起Pull Request

## 📜 开源协议
MIT License - 详见 [LICENSE](LICENSE) 文件

## 其他
该项目的潜力不止于此，只需要稍微修改，便可以使用ai用于减轻剪辑时的压力。
在商业项目中可以通过使用ai字幕工具提取不需要的空白内容，提取碎片化的片段。
亦可以在剪辑过程中，您可以让ai裁剪素材并输出合并的内容，为您的剪辑提供灵感，或者轻度剪辑，减轻您的难度。

非常感谢您看到这里，如果您对这个项目感兴趣，欢迎您为我点个⭐，不管怎样，谢谢您！
