import os
import subprocess
from pathlib import Path

def extract_song_name(audio_path):
    """从音频文件名中提取歌曲名（去掉序号和歌手）"""
    stem = audio_path.stem
    return stem.split('-')[-1].strip()

# 自动获取最新素材文件夹和音乐文件
def get_latest_video_dir():
   素材根目录 = Path("切割后的视频素材")
   所有文件夹 = [d for d in 素材根目录.iterdir() if d.is_dir()]
   if not 所有文件夹:
       raise FileNotFoundError(f"未找到任何素材文件夹，请检查目录：{素材根目录}")
   return max(所有文件夹, key=lambda x: x.stat().st_mtime)

def get_latest_music_file():
   音乐目录 = Path("mad音乐")
   所有音乐 = list(音乐目录.glob("*.flac")) + list(音乐目录.glob("*.mp3"))
   if not 所有音乐:
       raise FileNotFoundError(f"未找到任何音乐文件，请检查目录：{音乐目录}")
   return max(所有音乐, key=lambda x: x.stat().st_mtime)

video_dir = get_latest_video_dir()
audio_file = get_latest_music_file()
song_name = extract_song_name(audio_file)
output_dir = Path("output") / song_name
output_dir.mkdir(parents=True, exist_ok=True)

# 改进的文件排序逻辑（支持多种命名格式）
def extract_number(filename):
    """从文件名中提取开头的数字序号"""
    import re
    match = re.match(r'^(\d+)', filename.stem)
    if not match:
        raise ValueError(f"文件名格式错误：{filename} 缺少开头的数字序号")
    return int(match.group(1))

# 获取并排序视频文件
try:
    video_files = sorted(
        video_dir.glob("*.mp4"),
        key=extract_number
    )
    print(f"已找到 {len(video_files)} 个视频文件，最新文件：{video_files[-1].name}")
except ValueError as e:
    print("错误：视频文件命名不符合规范！")
    print("要求：文件名必须以数字开头，例如：'001_...' 或 '01_场景描述.mp4'")
    raise

# 生成FFmpeg文件列表
list_file = output_dir / "concat_list.txt"
with open(list_file, "w", encoding="utf-8") as f:
    for file in video_files:
        f.write(f"file '{file.resolve()}'\n")

# 合并视频（不重新编码）
merged_video = output_dir / f"{song_name}_合并.mp4"
subprocess.run([
    "ffmpeg",
    "-f", "concat",
    "-safe", "0",
    "-i", str(list_file),
    "-c", "copy",
    str(merged_video)
], check=True)

# 获取音乐时长
probe = subprocess.run([
    "ffprobe",
    "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    str(audio_file)
], capture_output=True, text=True, check=True)
music_duration = float(probe.stdout.strip())

# 截取与音乐等长的视频
trimmed_video = output_dir / f"{song_name}_剪辑.mp4"
subprocess.run([
    "ffmpeg",
    "-i", str(merged_video),
    "-t", str(music_duration),
    "-c", "copy",
    str(trimmed_video)
], check=True)

# 混合背景音乐（仅淡入）
final_output = output_dir / f"{song_name}_最终版.mp4"
subprocess.run([
    "ffmpeg",
    "-i", str(trimmed_video),
    "-i", str(audio_file),
    "-filter_complex",
    "[1:a]volume=0.8,adelay=0:all=1,afade=t=in:st=0:d=2[bgm]",
    "-map", "0:v",
    "-map", "[bgm]",
    "-an",
    "-c:v", "copy",
    "-c:a", "aac",
    "-b:a", "192k",
    "-t", str(music_duration),
    str(final_output)
], check=True)

# 清理临时文件
list_file.unlink()
merged_video.unlink(missing_ok=True)

print(f"处理完成！最终视频已保存至：{final_output}")
