import os
import asyncio
from hoshino import Service
from .bilibili_api import extract_video_id, get_video_info, get_video_subtitle, load_cookies
from .ai_summary import generate_summary

sv = Service('bilisummary', help_='B站视频摘要')

@sv.on_prefix(('b站摘要', 'B站摘要', '哔哩哔哩摘要', 'bili摘要'))
async def bilibili_summary(bot, ev):
    msg = ev.message.extract_plain_text().strip()
    if not msg:
        await bot.send(ev, '请提供B站视频链接或BV号')
        return
    
    # 提取视频ID
    video_id = extract_video_id(msg)
    if not video_id:
        await bot.send(ev, '无法识别的视频链接或BV号')
        return
    
    await bot.send(ev, f'正在获取视频信息和生成摘要，请稍候...')
    
    try:
        # 尝试加载cookies
        cookies = load_cookies()
        
        # 获取视频信息
        video_info = await get_video_info(video_id, cookies)
        if not video_info:
            await bot.send(ev, '获取视频信息失败')
            return
        
        # 获取字幕
        subtitle = await get_video_subtitle(video_id, cookies)
        
        # 生成摘要
        summary = await generate_summary(video_info, subtitle)
        
        # 构建回复消息
        title = video_info.get('title', '未知标题')
        author = video_info.get('owner', {}).get('name', '未知UP主')
        
        reply = f"《{title}》 - UP主: {author}\n\n{summary}"
        
        # 发送摘要
        await bot.send(ev, reply)
        
    except Exception as e:
        await bot.send(ev, f'生成摘要时发生错误: {str(e)}')