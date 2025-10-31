import os
import asyncio
import subprocess
import tempfile
import shutil
from pathlib import Path
import json
import re
from typing import Optional, Tuple, Dict, Any


class VideoDownloader:
    """视频下载和压缩工具类"""
    
    def __init__(self):
        self.temp_dir = None
        self.bbdown_path = None
        self.ffmpeg_path = None
    
    def find_bbdown(self) -> Optional[str]:
        """查找BBDown可执行文件"""
        # 常见的BBDown安装路径
        possible_paths = [
            'BBDown.exe',
            'bbdown.exe',
            'BBDown',
            'bbdown',
            os.path.expanduser('~/BBDown/BBDown.exe'),
            os.path.expanduser('~/bbdown/bbdown.exe'),
            'C:/Program Files/BBDown/BBDown.exe',
            'C:/BBDown/BBDown.exe',
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                return path
        
        return None
    
    def find_ffmpeg(self) -> Optional[str]:
        """查找FFmpeg可执行文件"""
        return shutil.which('ffmpeg') or shutil.which('ffmpeg.exe')
    
    def check_tools(self) -> Dict[str, bool]:
        """检查必要工具是否可用"""
        self.bbdown_path = self.find_bbdown()
        self.ffmpeg_path = self.find_ffmpeg()
        
        return {
            'bbdown': self.bbdown_path is not None,
            'ffmpeg': self.ffmpeg_path is not None
        }
    
    def get_installation_guide(self) -> str:
        """获取工具安装指南"""
        return """视频下载功能需要安装以下工具：

1. BBDown (B站视频下载工具)
   下载地址：https://github.com/nilaoda/BBDown/releases
   安装方法：下载后解压到任意目录，并将目录添加到系统PATH环境变量

2. FFmpeg (视频处理工具)
   下载地址：https://ffmpeg.org/download.html
   安装方法：下载后解压到任意目录，并将bin目录添加到系统PATH环境变量

安装完成后重启机器人即可使用视频下载功能。"""
    
    async def get_video_duration(self, video_path: str) -> Optional[float]:
        """获取视频时长（秒）"""
        if not self.ffmpeg_path:
            return None
        
        try:
            cmd = [
                self.ffmpeg_path, '-i', video_path,
                '-f', 'null', '-',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0'
            ]
            
            # 使用ffprobe获取更准确的时长信息
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
            if shutil.which(ffprobe_path):
                cmd = [
                    ffprobe_path, '-v', 'quiet',
                    '-show_entries', 'format=duration',
                    '-of', 'csv=p=0',
                    video_path
                ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                duration_str = stdout.decode().strip()
                return float(duration_str)
            
        except Exception as e:
            print(f"获取视频时长失败: {e}")
        
        return None
    
    def is_short_video(self, duration: float) -> bool:
        """判断是否为短视频（5分钟以内）"""
        return duration <= 300  # 5分钟 = 300秒
    
    async def download_video(self, video_id: str, output_dir: str, cookies_path: Optional[str] = None) -> Optional[str]:
        """使用BBDown下载视频（最低画质）"""
        if not self.bbdown_path:
            return None
        
        try:
            # BBDown命令参数
            cmd = [
                self.bbdown_path,
                f"https://www.bilibili.com/video/{video_id}",
                '--work-dir', output_dir,
                '--use-mp4-box-api',  # 使用mp4格式
                '--encoding-priority', 'hevc,av1,avc',  # 编码优先级
                '--dfn-priority', '16,32,64,80,112',  # 画质优先级（最低画质优先）
                '--audio-only', 'false',
                '--video-only', 'false',
                '--debug', 'false',
                '--skip-mux', 'false'
            ]
            
            # 如果有cookies文件，添加cookies参数
            if cookies_path and os.path.exists(cookies_path):
                cmd.extend(['--cookie', cookies_path])
            
            print(f"执行BBDown命令: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=output_dir
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # 查找下载的文件
                for file in os.listdir(output_dir):
                    if file.endswith(('.mp4', '.mkv', '.flv')):
                        return os.path.join(output_dir, file)
            else:
                print(f"BBDown下载失败: {stderr.decode()}")
            
        except Exception as e:
            print(f"下载视频失败: {e}")
        
        return None
    
    async def compress_video(self, input_path: str, output_path: str, target_size_mb: int = 10) -> bool:
        """使用FFmpeg压缩视频"""
        if not self.ffmpeg_path:
            return False
        
        try:
            # 获取原视频信息
            duration = await self.get_video_duration(input_path)
            if not duration:
                return False
            
            # 计算目标比特率 (kbps)
            # 目标大小(MB) * 8 * 1024 / 时长(秒) * 0.9 (留10%余量)
            target_bitrate = int(target_size_mb * 8 * 1024 / duration * 0.9)
            
            # 设置最小比特率限制
            target_bitrate = max(target_bitrate, 200)  # 最低200kbps
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-c:v', 'libx264',  # 使用H.264编码
                '-crf', '28',  # 质量参数，28为较高压缩
                '-preset', 'medium',  # 编码速度预设
                '-c:a', 'aac',  # 音频编码
                '-b:a', '64k',  # 音频比特率64kbps
                '-ac', '2',  # 双声道
                '-ar', '44100',  # 采样率
                '-vf', 'scale=640:-2',  # 缩放到640px宽度，高度自适应
                '-b:v', f'{target_bitrate}k',  # 视频比特率
                '-maxrate', f'{int(target_bitrate * 1.2)}k',  # 最大比特率
                '-bufsize', f'{int(target_bitrate * 2)}k',  # 缓冲区大小
                '-movflags', '+faststart',  # 优化网络播放
                '-y',  # 覆盖输出文件
                output_path
            ]
            
            print(f"执行FFmpeg压缩命令: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # 检查压缩后的文件大小
                if os.path.exists(output_path):
                    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    print(f"压缩完成，文件大小: {file_size_mb:.2f}MB")
                    
                    # 如果文件仍然太大，进行更激进的压缩
                    if file_size_mb > target_size_mb * 1.2:
                        print("文件仍然过大，进行二次压缩...")
                        return await self._aggressive_compress(input_path, output_path, target_size_mb)
                    
                    return True
            else:
                print(f"FFmpeg压缩失败: {stderr.decode()}")
            
        except Exception as e:
            print(f"压缩视频失败: {e}")
        
        return False
    
    async def _aggressive_compress(self, input_path: str, output_path: str, target_size_mb: int) -> bool:
        """更激进的压缩策略"""
        try:
            duration = await self.get_video_duration(input_path)
            if not duration:
                return False
            
            # 更低的比特率
            target_bitrate = int(target_size_mb * 8 * 1024 / duration * 0.8)
            target_bitrate = max(target_bitrate, 150)  # 最低150kbps
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-c:v', 'libx264',
                '-crf', '32',  # 更高的压缩率
                '-preset', 'slow',  # 更慢但更高效的编码
                '-c:a', 'aac',
                '-b:a', '48k',  # 更低的音频比特率
                '-ac', '2',
                '-ar', '22050',  # 更低的采样率
                '-vf', 'scale=480:-2',  # 更小的分辨率
                '-b:v', f'{target_bitrate}k',
                '-maxrate', f'{int(target_bitrate * 1.1)}k',
                '-bufsize', f'{target_bitrate}k',
                '-movflags', '+faststart',
                '-y',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            print(f"激进压缩失败: {e}")
            return False
    
    def cleanup_temp_files(self, temp_dir: str):
        """清理临时文件"""
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"清理临时目录: {temp_dir}")
        except Exception as e:
            print(f"清理临时文件失败: {e}")
    
    async def process_short_video(self, video_id: str, target_size_mb: int = 10, cookies_path: Optional[str] = None) -> Tuple[Optional[str], str]:
        """处理短视频：下载并压缩"""
        # 检查工具可用性
        tools = self.check_tools()
        if not tools['bbdown']:
            return None, "BBDown未安装或未找到"
        if not tools['ffmpeg']:
            return None, "FFmpeg未安装或未找到"
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix='bilibili_video_')
        
        try:
            # 下载视频
            print(f"开始下载视频: {video_id}")
            downloaded_file = await self.download_video(video_id, temp_dir, cookies_path)
            
            if not downloaded_file:
                return None, "视频下载失败"
            
            # 检查视频时长
            duration = await self.get_video_duration(downloaded_file)
            if duration and not self.is_short_video(duration):
                return None, f"视频时长 {duration/60:.1f} 分钟，超过5分钟限制"
            
            # 压缩视频
            compressed_file = os.path.join(temp_dir, f"compressed_{video_id}.mp4")
            print(f"开始压缩视频，目标大小: {target_size_mb}MB")
            
            if await self.compress_video(downloaded_file, compressed_file, target_size_mb):
                # 检查最终文件大小
                file_size_mb = os.path.getsize(compressed_file) / (1024 * 1024)
                
                if file_size_mb <= 50:  # QQ群文件大小限制通常是50MB
                    return compressed_file, f"视频处理完成，文件大小: {file_size_mb:.2f}MB"
                else:
                    return None, f"压缩后文件仍然过大: {file_size_mb:.2f}MB"
            else:
                return None, "视频压缩失败"
        
        except Exception as e:
            print(f"处理视频失败: {e}")
            return None, f"处理失败: {str(e)}"
        
        finally:
            # 注意：不在这里清理临时文件，让调用者决定何时清理
            pass