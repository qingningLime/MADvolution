import re
import os
import subprocess
from pathlib import Path

def parse_time(time_str):
    """将mm:ss.ms格式转换为HH:MM:SS.ms格式"""
    mm_ss, ms = time_str.split('.')
    return f"00:{mm_ss}.{ms}"

def parse_markdown(md_file):
    """解析Markdown文件，提取剪辑信息"""
    pattern = re.compile(r'第(\d+)集 (\d+:\d+\.\d+)~(\d+:\d+\.\d+)')
    clips = []
    in_table = False
    
    with open(md_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '|--------' in line:
                in_table = True
                continue
            if not in_table:
                continue
                
            # 匹配表格行中的时间码
            match = pattern.search(line)
            if match:
                ep_num = int(match.group(1))
                start_time = match.group(2)
                end_time = match.group(3)
                clips.append((ep_num, start_time, end_time))
    return clips

def find_video_file(episode):
    """精确匹配视频文件"""
    video_dir = Path("番剧原片")
    # 优先使用精确匹配
    exact_file = video_dir / f"[SVFI] BanG Dream! It's MyGO!!!!! [{episode:02d}][2160p BD HEVC Main10 FLAC].mkv"
    if exact_file.exists():
        return str(exact_file)
    
    # 保留原有模糊匹配作为后备
    for file in video_dir.glob(f"*[{episode:02d}]*.mkv"):
        return str(file)
    return None

def generate_output_filename(index, ep_num, start, end, description):
    """生成输出文件名"""
    # 转换时间为mm_ss_ms格式
    start_mm, start_rest = start.split(':')
    start_ss, start_ms = start_rest.split('.')
    end_mm, end_rest = end.split(':')
    end_ss, end_ms = end_rest.split('.')
    return f"{index:03d}_{ep_num}_{start_mm}_{start_ss}{start_ms}-{end_mm}_{end_ss}{end_ms}_{description}.mp4"

def get_frame_rate(video_file):
    """获取视频帧率"""
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
           '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', video_file]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    try:
        return float(eval(result.stdout.strip()))  # 处理分数形式的帧率
    except:
        return 24.0  # 默认帧率

def find_nearest_keyframe(video_file, timestamp):
    """查找最近的关键帧(优先向后偏移)"""
    MAX_OFFSET = 1.0  # 最大允许偏差1秒
    cmd = [
        'ffprobe', '-read_intervals', f'{max(0,timestamp-1)}%+2',
        '-show_frames', '-select_streams', 'v',
        '-print_format', 'csv', '-show_entries', 'frame=key_frame,pkt_pts_time',
        video_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    
    # 获取所有关键帧时间点
    keyframes = [float(line.split(',')[1]) for line in result.stdout.splitlines()
               if line.startswith('frame,') and line.split(',')[0] == '1']
    
    if not keyframes:
        return timestamp
    
    # 优先选择后面的关键帧
    later_frames = [kf for kf in keyframes if kf >= timestamp]
    if later_frames:
        nearest = min(later_frames, key=lambda x: abs(x - timestamp))
        if abs(nearest - timestamp) <= MAX_OFFSET:
            return nearest
    
    # 如果没有合适的后向关键帧，选择最接近的
    nearest = min(keyframes, key=lambda x: abs(x - timestamp))
    return nearest if abs(nearest - timestamp) <= MAX_OFFSET else timestamp

def cut_video_copy(input_file, output_file, start, end):
    """快速复制模式(保留原质量)"""
    cmd = [
        'ffmpeg',
        '-ss', parse_time(start),
        '-to', parse_time(end),
        '-i', input_file,
        '-c', 'copy',
        '-avoid_negative_ts', '1',
        str(output_file)
    ]
    subprocess.run(cmd, check=True)

def check_gpu_support():
    """检查GPU支持情况"""
    try:
        result = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], 
                              capture_output=True, text=True)
        return 'h264_nvenc' in result.stdout or 'h264_amf' in result.stdout
    except:
        return False

def cut_video_reencode(input_file, output_file, start, end):
    """处理10-bit视频的AMD加速方案"""
    if check_gpu_support():
        try:
            # 先尝试HEVC编码
            cmd = [
                'ffmpeg',
                '-hwaccel', 'cuda',
                '-hwaccel_device', '1',
                '-ss', parse_time(start),
                '-to', parse_time(end),
                '-i', input_file,
                '-c:v', 'hevc_amf',
                '-quality', 'balanced',
                '-rc', 'cqp',
                '-qp_i', '18',
                '-qp_p', '18',
                '-c:a', 'aac',
                '-b:a', '192k',
                str(output_file)
            ]
            print("使用HEVC_AMF 10-bit编码")
            subprocess.run(cmd, check=True)
            return
        except subprocess.CalledProcessError:
            # HEVC失败则回退到8-bit H264
            print("HEVC编码失败，转用8-bit H264")
            cmd = [
                'ffmpeg',
                '-hwaccel', 'auto',
                '-hwaccel_device', '1',
                '-ss', parse_time(start),
                '-to', parse_time(end),
                '-i', input_file,
                '-pix_fmt', 'yuv420p',
                '-c:v', 'h264_amf',
                '-quality', 'balanced',
                '-rc', 'cqp',
                '-qp_i', '18',
                '-qp_p', '18',
                '-c:a', 'aac',
                '-b:a', '192k',
                str(output_file)
            ]
    else:
        # CPU回退方案
        cmd = [
            'ffmpeg',
            '-ss', parse_time(start),
            '-to', parse_time(end),
            '-i', input_file,
            '-c:v', 'libx264',
            '-crf', '18',
            '-preset', 'fast',
            '-c:a', 'aac',
            '-b:a', '192k',
            str(output_file)
        ]
        print("使用CPU渲染(未检测到AMD GPU支持)")
    
    subprocess.run(cmd, check=True)

def cut_video(input_file, output_file, start, end):
    """强制使用渲染模式切割"""
    print("使用渲染模式 (强制所有片段精确切割)")
    cut_video_reencode(input_file, output_file, start, end)

def main():
    # 扫描ai输出内容目录下的所有md文件
    md_dir = Path("ai输出内容")
    md_files = list(md_dir.glob("*.md"))
    
    if not md_files:
        print("未找到任何.md文件")
        return
    
    for md_file in md_files:
        print(f"\n处理文件: {md_file.name}")
        # 从md文件名获取项目名(不带扩展名)
        project_name = md_file.stem
        output_dir = Path("output") / project_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        clips = parse_markdown(str(md_file))
        for i, (ep_num, start, end) in enumerate(clips, 1):
            video_file = find_video_file(ep_num)
            if not video_file:
                print(f"未找到第{ep_num}集视频文件")
                continue
            
            # 简单使用序号作为描述（实际可从Markdown提取）
            output_file = output_dir / generate_output_filename(
                i, ep_num, start, end, f"clip_{i}")
                
            print(f"处理片段{i}: 第{ep_num}集 {start}-{end}")
            cut_video(video_file, output_file, start, end)
            print(f"已保存到: {output_file}")

if __name__ == "__main__":
    main()
