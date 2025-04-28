import json
from pathlib import Path
import re
from datetime import datetime

def convert_to_timestamp(seconds):
    """将秒数转换为MM:SS格式"""
    mm = int(seconds // 60)
    ss = int(seconds % 60)
    return f"{mm:02d}:{ss:02d}"

def generate_clip_guide(storyboard_file):
    """生成剪辑指导Markdown报告"""
    with open(storyboard_file, 'r', encoding='utf-8') as f:
        storyboard = json.load(f)
    
    def parse_time(time_str):
        parts = list(map(float, reversed(time_str.split(':'))))
        return sum(y * 60**n for n, y in enumerate(parts))

    # 预处理：时间纠错和合并短片段
    # 1. 确保时间顺序正确 - 以歌词下一句的开始时间作为上一句的结束时间
    for i in range(1, len(storyboard)):
        try:
            curr_start = parse_time(storyboard[i]['timestamp'].split('-')[0])
            # 将前一句的结束时间调整为当前句的开始时间
            storyboard[i-1]['timestamp'] = f"{storyboard[i-1]['timestamp'].split('-')[0]}-{convert_to_timestamp(curr_start)}"
        except:
            continue
    
    # 2. 合并短片段
    merged_storyboard = []
    i = 0
    while i < len(storyboard):
        current = storyboard[i]
        if i < len(storyboard)-1:
            next_seg = storyboard[i+1]
            try:
                start1, end1 = map(parse_time, current['timestamp'].split('-'))
                start2, end2 = map(parse_time, next_seg['timestamp'].split('-'))
            except:
                # 如果解析失败，跳过合并
                merged_storyboard.append(current)
                i += 1
                continue
            duration = end1 - start1
            
            # 连续合并条件：片段小于4秒时持续合并
            merged_seg = current.copy()
            merge_count = 0
            
            while i + merge_count + 1 < len(storyboard):
                next_seg = storyboard[i + merge_count + 1]
                try:
                    start = parse_time(merged_seg['timestamp'].split('-')[0])
                    end = parse_time(next_seg['timestamp'].split('-')[1])
                    duration = end - start
                    
                    if duration >= 4.0:
                        break
                        
                    # 合并到下一个片段
                    merged_seg = {
                        'timestamp': f"{merged_seg['timestamp'].split('-')[0]}-{next_seg['timestamp'].split('-')[1]}",
                        'text': f"{merged_seg['text']} / {next_seg['text']}",
                        'emotion': next_seg['emotion'] if merged_seg['emotion'] == 'neutral' else merged_seg['emotion'],
                        'beat_strength': max(merged_seg['beat_strength'], next_seg['beat_strength'], key=lambda x: ['weak','medium','strong'].index(x)),
                        'dynamics': {
                            'intensity': max(merged_seg['dynamics']['intensity'], next_seg['dynamics']['intensity'], 
                                          key=lambda x: ['low','medium','high'].index(x)),
                            'brightness': next_seg['dynamics']['brightness']
                        }
                    }
                    merge_count += 1
                except:
                    break
                    
            merged_storyboard.append(merged_seg)
            i += 1 + merge_count  # 跳过已合并的片段
            continue
        merged_storyboard.append(current)
        i += 1
    
    # 解析时间范围
    time_ranges = []
    for seg in merged_storyboard:
        # 从timestamp字段解析时间范围并标准化格式
        start, end = seg['timestamp'].split('-')
        
        # 解析并标准化时间格式为MM:SS
        start_parts = start.replace('.',':').split(':')
        start = f"{start_parts[0]}:{start_parts[1]}"
        
        end_parts = end.replace('.',':').split(':') 
        end = f"{end_parts[0]}:{end_parts[1]}"
        
        time_ranges.append(f"{start}-{end}")
    
    # 生成Markdown内容
    md_content = [
        "# 动漫剪辑指导\n",
        "## 镜头切换时间表\n",
        "| 时间范围 | 切换类型 | 内容 | 情感 | 节奏强度 |\n",
        "|----------|----------|------|------|----------|\n"
    ]
    
    for i, seg in enumerate(merged_storyboard):
        # 确定切换类型
        cut_type = "节拍切换" if seg['beat_strength'] == 'strong' else "段落切换"
        if i == 0:
            cut_type = "开场镜头"
        elif '[间奏]' in seg['text'] or '[尾奏]' in seg['text']:
            cut_type = "过渡段落"
        
        # 处理内容显示
        content = seg['text']
        if len(content) > 15 and not ('[间奏]' in content or '[尾奏]' in content):
            content = content[:15] + "..."
            
        md_content.append(
            f"| {time_ranges[i]} | {cut_type} | {content} | {seg['emotion']} | {seg['beat_strength']} |\n"
        )
    
    # 添加剪辑建议
    md_content.extend([
        "\n## 剪辑建议\n",
        "- **高潮部分**: 建议使用快速剪辑(每个节拍切换)\n",
        "- **抒情段落**: 建议使用慢推镜头+溶解过渡\n",
        f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ])
    
    return "".join(md_content)

def process_all_songs():
    """处理output目录下所有歌曲"""
    output_dir = Path("output")
    for song_dir in output_dir.iterdir():
        if song_dir.is_dir():
            storyboard_file = song_dir / "storyboard.json"
            if storyboard_file.exists():
                try:
                    guide = generate_clip_guide(storyboard_file)
                    output_file = song_dir / "clip_guide.md"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(guide)
                    print(f"成功生成剪辑指导: {output_file}")
                except Exception as e:
                    print(f"无法生成 {song_dir.name} 的剪辑指导: {str(e)}")

if __name__ == "__main__":
    process_all_songs()
