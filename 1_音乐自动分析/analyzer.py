import os
import json
from pathlib import Path
import librosa
import numpy as np
import re
import mutagen
import traceback
import subprocess
from config import *

def process_lyrics(input_file):
    """处理歌词文件，返回格式化歌词和音频时长"""
    # 创建输出文件路径
    output_file = OUTPUT_DIR / f"{input_file.stem}_processed.txt"
    
    # 尝试多种编码读取(包括带BOM的UTF-8)
    for encoding in ['utf-8-sig', 'gb18030', 'gbk', 'big5', 'utf-16', 'utf-16-le', 'utf-16-be']:
        try:
            with open(input_file, 'r', encoding=encoding) as f:
                lines = f.readlines()
                # 检查是否有替换字符(表示解码可能有问题)
                if any('\ufffd' in line for line in lines):
                    continue
                # 检查是否有明显乱码
                if any(not any('\u4e00' <= c <= '\u9fff' or c.isalnum() or c.isspace() or c in '，。！？、；：（）【】《》' for c in line) 
                       and any('\u4e00' <= c <= '\u9fff' for c in line) for line in lines[:10]):
                    continue
                break
        except UnicodeDecodeError:
            continue
    else:
        # 如果所有编码都失败，尝试自动检测
        with open(input_file, 'rb') as f:
            raw = f.read()
            for encoding in ['utf-8', 'gb18030', 'gbk', 'big5']:
                try:
                    lines = raw.decode(encoding).splitlines()
                    if not any('\ufffd' in line for line in lines):
                        break
                except:
                    continue
            else:
                # 最后尝试忽略错误
                lines = raw.decode('utf-8', errors='ignore').splitlines()

    # 获取音频时长
    audio_file = find_matching_audio(input_file)
    duration = get_audio_duration(audio_file) if audio_file else None

    # 处理歌词内容
    output_content = []
    if duration:
        output_content.append(f"// 音频时长: {duration}\n\n")

    lyric_index = 1
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # 匹配时间戳和歌词(支持[mm:ss.xx]和[mm:ss]格式)
        time_lyric_match = re.match(r'^(\[\d{2}:\d{2}(?:\.\d{2,3})?\])(.+)$', line)
        if time_lyric_match:
            time_stamp = time_lyric_match.group(1)
            lyric = time_lyric_match.group(2).strip()
            
            # 过滤非歌词内容(检查时间戳行和歌词内容)
            if any(kw in line for kw in FILTER_KEYWORDS) or \
               any(kw in lyric for kw in FILTER_KEYWORDS):
                i += 1
                continue
                
            # 查找结束时间
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if next_line and re.match(r'^\[\d{2}:\d{2}\.\d{2,3}\]', next_line):
                    end_time = re.match(r'^(\[\d{2}:\d{2}\.\d{2,3}\])', next_line).group(1)
                    output_content.append(f"{lyric_index}. {time_stamp}~{end_time} {lyric}\n")
                    lyric_index += 1
                    break
                j += 1
        i += 1

    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(output_content)
    
    return output_file, duration

def analyze_music(audio_file, lyrics_file):
    """分析音乐特征并生成故事板"""
    # 加载音频
    y, sr = librosa.load(audio_file, sr=DEFAULT_SAMPLE_RATE)
    
    # 节拍检测
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, tightness=BEAT_TIGHTNESS)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    # 特征提取
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)[0]
    
    # 间奏检测
    threshold = np.percentile(rms, int(INTERLUDE_THRESHOLD*100))
    low_energy = rms < threshold
    
    # 生成故事板
    duration = len(y)/sr
    storyboard = generate_storyboard(lyrics_file, {
        'tempo': float(tempo),
        'beats': [float(t) for t in beat_times],
        'chroma': chroma.tolist(),
        'dynamics': {'rms': rms.tolist()},
        'interludes': detect_interludes(low_energy, duration),
        'duration': duration
    })
    
    # 创建歌曲专属文件夹
    song_dir = OUTPUT_DIR / audio_file.stem
    song_dir.mkdir(exist_ok=True)
    
    # 保存结果到歌曲文件夹
    output_json = song_dir / "storyboard.json"
    output_md = song_dir / "report.md"
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(storyboard, f, ensure_ascii=False, indent=2)
        
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(generate_markdown_report(storyboard))
    
    return output_json, output_md

def find_matching_audio(lyric_file):
    """查找与歌词文件匹配的音频文件"""
    base_name = lyric_file.stem
    for ext in AUDIO_EXTENSIONS:
        audio_file = lyric_file.with_suffix(ext)
        if audio_file.exists():
            return audio_file
    return None

def get_audio_duration(audio_path):
    """获取音频时长"""
    try:
        audio = mutagen.File(audio_path)
        if audio is None:
            return None
        return f"{int(audio.info.length//60):02d}:{int(audio.info.length%60):02d}"
    except Exception:
        return None

def detect_interludes(low_energy, duration):
    """检测间奏时间段"""
    interlude_times = []
    in_segment = False
    start_idx = 0
    
    for i, is_low in enumerate(low_energy):
        if is_low and not in_segment:
            in_segment = True
            start_idx = i
        elif not is_low and in_segment:
            in_segment = False
            duration = (i - start_idx) * duration/len(low_energy)
            if duration > 5:  # 至少5秒
                start_time = start_idx * duration/len(low_energy)
                end_time = i * duration/len(low_energy)
                interlude_times.append({'start': start_time, 'end': end_time})
    return interlude_times

def convert_to_seconds(time_str):
    """将时间字符串(mm:ss.xx)转换为秒数"""
    if '.' in time_str:
        mm, rest = time_str.split(':')
        ss, ms = rest.split('.')
        return int(mm)*60 + float(ss) + float(ms)/100
    else:
        mm, ss = time_str.split(':')
        return int(mm)*60 + float(ss)

def convert_to_timestamp(seconds):
    """将秒数转换为时间字符串(mm:ss.xx)"""
    mm = int(seconds // 60)
    ss = seconds % 60
    return f"{mm:02d}:{ss:06.3f}"

def analyze_emotion(text):
    """分析歌词情感"""
    if '流泪' in text or '黄昏' in text:
        return 'melancholy'
    elif '时间' in text or '人生' in text:
        return 'reflective'
    elif '希望' in text or '感谢' in text:
        return 'hopeful'
    return 'neutral'

def generate_storyboard(lyrics_file, audio_features):
    """生成故事板"""
    storyboard = []
    lyrics_segments = []
    
    # 首先处理歌词内容，收集所有歌词段落
    with open(lyrics_file, 'r', encoding='utf-8') as f:
        for line in f:
            # 匹配处理后的格式: 1. [00:00.00]~[00:05.10] 歌词内容
            match = re.match(r'^\d+\. (\[[^\]]+\])~(\[[^\]]+\]) (.+)$', line)
            if not match:
                print(f"跳过无法匹配的行: {line.strip()}")
                continue
                
            start_time = match.group(1)[1:-1]  # 去掉方括号
            end_time = match.group(2)[1:-1]
            lyric = match.group(3).strip()
            
            # 转换为秒数
            start_sec = convert_to_seconds(start_time)
            end_sec = convert_to_seconds(end_time)
            
            lyrics_segments.append({
                'start': start_sec,
                'end': end_sec,
                'text': lyric,
                'timestamp': f"{start_time}-{end_time}"
            })
    
    # 添加前奏段落（严格匹配第一句歌词开始时间）
    first_seg = lyrics_segments[0] if lyrics_segments else None
    if first_seg and first_seg['start'] > 1.0:  # 至少1秒才认为是前奏
        # 确保前奏结束时间严格等于第一句歌词开始时间
        intro_end = first_seg['start']
        if intro_end > 0:
            storyboard.append({
                'timestamp': f"00:00.000-{convert_to_timestamp(intro_end - 0.1)}",  # 减去100毫秒确保无重叠
                'text': '[前奏]',
                'emotion': 'neutral',
                'dynamics': {'intensity': 'low', 'brightness': 'normal'},
                'beat_strength': 'weak'
            })
    
    # 添加间奏和歌词段落
    last_end = 0.0 if not storyboard else first_seg['start']
    for seg in lyrics_segments:
        # 检查是否有间奏(严格匹配下一句歌词开始时间)
        if seg['start'] > last_end + 1.0:  # 至少1秒间隔才认为是间奏
            # 确保间奏结束时间严格等于下一句歌词开始时间
            interlude_end = seg['start']
            storyboard.append({
                'timestamp': f"{convert_to_timestamp(last_end)}-{convert_to_timestamp(interlude_end - 0.1)}",  # 减去100毫秒确保无重叠
                'text': '[间奏]',
                'emotion': 'neutral',
                'dynamics': {'intensity': 'low', 'brightness': 'normal'},
                'beat_strength': 'weak'
            })
        
        # 添加歌词段落
        storyboard.append({
            'timestamp': seg['timestamp'],
            'text': seg['text'],
            'emotion': analyze_emotion(seg['text']),
            'dynamics': {
                'intensity': 'high' if audio_features['dynamics']['rms'][int(seg['start']*20)] > 0.5 else 'medium',
                'brightness': 'normal'
            },
            'beat_strength': 'strong' if any(abs(t-seg['start']) < 0.1 for t in audio_features['beats']) else 'medium'
        })
        last_end = seg['end']
    
    # 添加尾奏段落（如果有）
    if last_end < audio_features['duration'] - 3.0:  # 至少3秒才认为是尾奏
        storyboard.append({
            'timestamp': f"{convert_to_timestamp(last_end)}-{convert_to_timestamp(audio_features['duration'])}",
            'text': '[尾奏]',
            'emotion': 'neutral',
            'dynamics': {'intensity': 'low', 'brightness': 'normal'},
            'beat_strength': 'weak'
        })
    return storyboard

def generate_markdown_report(storyboard):
    """生成Markdown格式报告"""
    # 生成段落表格
    md = [
        "# 音乐分析报告",
        "## 歌曲结构分析",
        "| 时间 | 段落类型 | 内容 | 情感 | 动态特征 | 节拍强度 |",
        "|------|----------|------|------|----------|----------|"
    ]
    
    # 情感统计
    emotion_stats = {
        'neutral': 0,
        'melancholy': 0, 
        'reflective': 0,
        'hopeful': 0
    }
    
    # 处理每个段落
    for i, seg in enumerate(storyboard):
        # 确定段落类型
        seg_type = 'verse'
        if '[间奏]' in seg['text'] or '[尾奏]' in seg['text']:
            seg_type = 'interlude'
            
        # 统一格式化时间戳
        if '-' in seg['timestamp']:
            # 已经是时间范围格式
            time_range = seg['timestamp']
        else:
            # 单个时间点格式
            if i+1 < len(storyboard):
                time_range = f"{seg['timestamp']}-{storyboard[i+1]['timestamp']}"
            else:
                time_range = seg['timestamp']
        
        # 处理内容显示
        text = seg['text']
        if seg_type == 'interlude':
            text = '[间奏]' if '[间奏]' in text else '[尾奏]'
        else:
            text = text[:20] + "..." if len(text) > 20 else text
            
        # 更新情感统计
        emotion_stats[seg['emotion']] += 1
        
        md.append(f"| {time_range} | {seg_type} | {text} | {seg['emotion']} | {seg['dynamics']['intensity']} | {seg['beat_strength']} |")
    
    # 添加统计部分
    md.extend([
        "",
        "## 歌曲特征统计",
        f"- 总段落数: {len(storyboard)}",
        "- 情感分布:",
        f"  - 中性: {emotion_stats['neutral']}",
        f"  - 忧郁: {emotion_stats['melancholy']}",
        f"  - 反思: {emotion_stats['reflective']}",
        f"  - 希望: {emotion_stats['hopeful']}"
    ])
    
    return "\n".join(md)

def main():
    """主程序入口"""
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # 处理input目录中的所有文件
    for file in INPUT_DIR.iterdir():
        if file.suffix.lower() in LYRIC_EXTENSIONS:
            print(f"处理文件: {file.name}")
            try:
                # 处理歌词并生成processed.txt
                lyrics_file, duration = process_lyrics(file)
                
                # 查找匹配的音频文件
                audio_file = find_matching_audio(file)
                if audio_file:
                    # 使用processed.txt进行情感分析
                    processed_file = OUTPUT_DIR / f"{file.stem}_processed.txt"
                    analyze_music(audio_file, processed_file)
                    print(f"成功处理: {file.name}")
                else:
                    print(f"警告: 未找到匹配的音频文件")
            except Exception as e:
                print(f"处理 {file.name} 时出错:")
                traceback.print_exc()

if __name__ == "__main__":
    main()
    # 运行剪辑指南模板脚本
    template_path = OUTPUT_DIR / "clip_guide_template.py"
    if template_path.exists():
        subprocess.run(["python", str(template_path)])
