import asyncio
import sys
import os

# 添加当前目录到sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bilibili_api import extract_video_id, get_video_info, get_video_subtitle, load_cookies, save_cookies, login_with_qrcode
from manual_login import manual_login
from ai_summary import generate_summary

async def test_video_summary(video_url, use_login=False):
    """测试视频摘要生成流程"""
    print(f"开始处理视频: {video_url}")
    
    # 提取视频ID
    video_id = extract_video_id(video_url)
    if not video_id:
        print("无法提取视频ID")
        return
    
    print(f"视频ID: {video_id}")
    
    # 获取cookies（如果需要登录）
    cookies = None
    if use_login:
        cookies = load_cookies()
        if not cookies:
            print("未找到已保存的cookies，需要扫码登录")
            cookies = await login_with_qrcode()
            if cookies:
                save_cookies(cookies)
                print("登录成功并保存cookies")
            else:
                print("登录失败，将使用未登录状态继续")
    
    # 获取视频信息
    print("正在获取视频信息...")
    video_info = await get_video_info(video_id, cookies)
    if not video_info:
        print("获取视频信息失败")
        return
    
    print(f"视频标题: {video_info.get('title')}")
    print(f"UP主: {video_info.get('owner', {}).get('name')}")
    
    # 获取字幕
    print("正在获取视频字幕...")
    subtitle = await get_video_subtitle(video_id, cookies)
    if subtitle:
        print(f"获取到字幕，长度: {len(subtitle)} 字符")
    else:
        print("未获取到字幕或视频没有字幕")
        # 如果未登录且获取字幕失败，尝试登录后再获取
        if not cookies:
            print("检测到未登录状态，尝试登录后重新获取字幕...")
            cookies = await login_with_qrcode()
            if cookies:
                save_cookies(cookies)
                print("登录成功，重新获取字幕...")
                subtitle = await get_video_subtitle(video_id, cookies)
                if subtitle:
                    print(f"登录后成功获取字幕，长度: {len(subtitle)} 字符")
                else:
                    print("登录后仍无法获取字幕，可能该视频确实没有字幕")
            else:
                print("登录失败，将继续使用未登录状态")
    
    # 生成摘要
    print("正在生成视频摘要...")
    summary = await generate_summary(video_info, subtitle)
    
    print("\n========= 视频摘要 =========")
    print(summary)
    print("============================\n")
    
    return summary

async def async_main_with_manual_login(url):
    """处理手动登录流程的异步函数"""
    cookies = await manual_login()
    if cookies:
        save_cookies(cookies)
        print("手动登录成功并保存cookies")
        await test_video_summary(url, True)
    else:
        print("手动登录失败或取消")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='测试B站视频摘要生成')
    parser.add_argument('--url', type=str, default="https://www.bilibili.com/video/BV1GJ411x7h7", 
                        help='B站视频URL')
    parser.add_argument('--login', action='store_true', help='是否使用登录模式')
    parser.add_argument('--manual-login', action='store_true', help='使用手动输入cookies方式登录')
    args = parser.parse_args()
    
    # 如果指定了手动登录，则使用manual_login函数
    if args.manual_login:
        asyncio.run(async_main_with_manual_login(args.url))
    else:
        asyncio.run(test_video_summary(args.url, args.login))