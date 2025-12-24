import asyncio
import os
import sys
import shutil
import importlib.util

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 动态加载 video_downloader.py，避免触发包的 __init__.py 导致的 HoshinoBot 初始化检查
try:
    module_path = os.path.join(current_dir, "video_downloader.py")
    spec = importlib.util.spec_from_file_location("video_downloader_standalone", module_path)
    if spec and spec.loader:
        video_downloader = importlib.util.module_from_spec(spec)
        sys.modules["video_downloader_standalone"] = video_downloader
        spec.loader.exec_module(video_downloader)
        VideoDownloader = video_downloader.VideoDownloader
    else:
        raise ImportError("无法加载模块")
except Exception as e:
    print(f"❌ 无法导入 VideoDownloader 模块: {e}")
    print("请确保 video_downloader.py 文件在当前目录下。")
    sys.exit(1)

async def main():
    print("=" * 50)
    print("🎬 视频下载功能测试工具 (yt-dlp版)")
    print("=" * 50)
    
    downloader = VideoDownloader()
    
    print("\n[1/3] 正在检查必要工具...")
    tools = downloader.check_tools()
    
    print(f"  - BBDown: {'✅ 已安装' if tools['bbdown'] else '❌ 未找到'}")
    print(f"  - yt-dlp: {'✅ 已安装' if tools['ytdlp'] else '❌ 未找到'}")
    print(f"  - FFmpeg: {'✅ 已安装' if tools['ffmpeg'] else '❌ 未找到'}")
    
    # 尝试手动查找 yt-dlp 如果自动查找失败
    if not tools['ytdlp']:
        print("  Checking common pip install locations...")
        python_scripts = os.path.join(os.path.dirname(sys.executable), 'Scripts')
        possible_ytdlp = os.path.join(python_scripts, 'yt-dlp.exe')
        if os.path.exists(possible_ytdlp):
            print(f"  ! Found yt-dlp at: {possible_ytdlp}")
            downloader.ytdlp_path = possible_ytdlp
            tools['ytdlp'] = True
    
    if not (tools['bbdown'] or tools['ytdlp']):
        print("\n❌ 错误：未找到任何下载工具！")
        print("请运行 'pip install yt-dlp' 安装 yt-dlp。")
        return

    if not tools['ffmpeg']:
        print("\n❌ 错误：未找到 FFmpeg！")
        print("请安装 FFmpeg 并将其添加到系统环境变量 PATH 中。")
        return
        
    print("\n✅ 工具检查通过！")
    
    while True:
        print("\n" + "-" * 30)
        video_input = input("请输入B站视频链接或BV号 (直接回车退出): ").strip()
        
        if not video_input:
            break
            
        # 简单的ID提取
        video_id = video_input
        if 'bilibili.com' in video_input or 'b23.tv' in video_input:
            # 这里简单处理，提取 BV 号
            import re
            match = re.search(r'(BV[A-Za-z0-9]+)', video_input)
            if match:
                video_id = match.group(1)
            else:
                print("⚠️ 无法从链接中提取BV号，尝试直接使用输入内容...")
        
        print(f"\n[2/3] 准备下载视频: {video_id}")
        output_dir = os.path.join(current_dir, 'download_test')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"  - 创建测试输出目录: {output_dir}")
            
        print("  - 开始下载... (这可能需要几秒到几分钟)")
        
        try:
            # 测试下载
            # 注意：cookies_path 默认为空，如果需要 cookies 可以在这里添加
            file_path = await downloader.download_video(video_id, output_dir)
            
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                print(f"\n✅ [3/3] 下载成功！")
                print(f"  - 文件路径: {file_path}")
                print(f"  - 文件大小: {file_size:.2f} MB")
                
                # 询问是否压缩
                if file_size > 10:
                    choice = input("\n文件超过10MB，是否测试压缩功能? (y/n): ").lower()
                    if choice == 'y':
                        print("\n[附加] 正在测试压缩...")
                        compressed_path = os.path.join(output_dir, f"compressed_{os.path.basename(file_path)}")
                        success = await downloader.compress_video(file_path, compressed_path, target_size_mb=10)
                        
                        if success and os.path.exists(compressed_path):
                            new_size = os.path.getsize(compressed_path) / (1024 * 1024)
                            print(f"✅ 压缩成功！")
                            print(f"  - 新文件路径: {compressed_path}")
                            print(f"  - 新文件大小: {new_size:.2f} MB")
                        else:
                            print("❌ 压缩失败")
            else:
                print("\n❌ 下载失败。请检查视频ID是否正确，或网络是否通畅。")
                print("提示：如果是大会员视频或需要登录，可能因为没有设置Cookies而失败。")
                
        except Exception as e:
            print(f"\n❌ 发生异常: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n测试结束，再见！")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断操作")
