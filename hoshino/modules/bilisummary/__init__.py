import os
import re
import asyncio
from hoshino import Service
from hoshino.typing import CQEvent
from .bilibili_api import extract_video_id, get_video_info, get_video_subtitle, load_cookies
from .ai_summary import generate_summary

sv = Service('bilisummary', help_='B站视频解析和摘要\n自动识别B站链接发送小程序\n回复"总结"可获取AI摘要', enable_on_default=True)

# B站链接正则表达式
BILIBILI_URL_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?(?:bilibili\.com/video/|b23\.tv/|m\.bilibili\.com/video/)([A-Za-z0-9]+)|BV[A-Za-z0-9]+|av\d+',
    re.IGNORECASE
)

def create_bilibili_miniapp(video_info):
    """创建B站小程序卡片"""
    title = video_info.get('title', '未知标题')
    author = video_info.get('owner', {}).get('name', '未知UP主')
    pic = video_info.get('pic', '')
    desc = video_info.get('desc', '')[:50] + '...' if len(video_info.get('desc', '')) > 50 else video_info.get('desc', '')
    bvid = video_info.get('bvid', '')
    
    # 构建小程序JSON
    miniapp_json = {
        "app": "com.tencent.miniapp",
        "desc": "",
        "view": "view_8C8E89B49BE609866298ADDFF2DBABA4",
        "ver": "1.0.0.103",
        "prompt": f"[QQ小程序]哔哩哔哩",
        "appID": "",
        "sourceName": "",
        "actionData": "",
        "actionData_A": "",
        "sourceUrl": "",
        "meta": {
            "detail_1": {
                "appid": "1109937557",
                "appType": 0,
                "title": title,
                "desc": desc,
                "icon": pic,
                "preview": pic,
                "url": f"m.q.qq.com/a/s/{bvid}",
                "scene": 1036,
                "host": {
                    "appid": "1109937557",
                    "uin": 0
                },
                "shareTemplateId": "8C8E89B49BE609866298ADDFF2DBABA4",
                "shareTemplateData": {}
            }
        },
        "text": "",
        "sourceAd": "",
        "extra": ""
    }
    
    return f"[CQ:json,data={str(miniapp_json).replace(' ', '')}]"

@sv.on_rex(BILIBILI_URL_PATTERN)
async def auto_bilibili_parse(bot, ev: CQEvent):
    """自动解析B站链接并发送小程序"""
    msg = ev.message.extract_plain_text()
    
    # 提取视频ID
    video_id = extract_video_id(msg)
    if not video_id:
        return
    
    try:
        # 尝试加载cookies
        cookies = load_cookies()
        
        # 获取视频信息
        video_info = await get_video_info(video_id, cookies)
        if not video_info:
            return
        
        # 发送小程序卡片
        miniapp = create_bilibili_miniapp(video_info)
        await bot.send(ev, miniapp)
        
    except Exception as e:
        sv.logger.error(f'解析B站链接失败: {str(e)}')

@sv.on_keyword(('总结', '摘要'))
async def bilibili_summary_reply(bot, ev: CQEvent):
    """回复总结关键词时，对引用的B站链接进行AI总结"""
    # 检查是否有引用消息
    match = re.match(r"\[CQ:reply,id=(?P<id>.*)\]", str(ev.message))
    if not match:
        return
    
    # 获取被引用的消息ID
    message_id = match.group("id")
    try:
        # 获取被引用的消息内容
        reply_message = await bot.get_msg(message_id=message_id)
        reply_text = reply_message.get('message', '')
    except Exception as e:
        sv.logger.error(f'获取引用消息失败: {str(e)}')
        return
    
    # 检查引用消息是否包含B站链接
    if not BILIBILI_URL_PATTERN.search(str(reply_text)):
        return
    
    # 提取视频ID
    video_id = extract_video_id(str(reply_text))
    if not video_id:
        await bot.send(ev, '无法识别B站视频链接')
        return
    
    await bot.send(ev, '正在生成视频摘要，请稍候...')
    
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
        duration = video_info.get('duration', 0)
        view = video_info.get('stat', {}).get('view', 0)
        
        # 格式化时长
        minutes = duration // 60
        seconds = duration % 60
        duration_str = f"{minutes}:{seconds:02d}"
        
        # 格式化播放量
        if view >= 10000:
            view_str = f"{view/10000:.1f}万"
        else:
            view_str = str(view)
        
        reply = f"📺 《{title}》\n"
        reply += f"👤 UP主: {author}\n"
        reply += f"⏱️ 时长: {duration_str} | 👁️ 播放: {view_str}\n\n"
        reply += f"📝 AI摘要:\n{summary}"
        
        # 发送摘要
        await bot.send(ev, reply)
        
    except Exception as e:
        await bot.send(ev, f'生成摘要时发生错误: {str(e)}')

@sv.on_prefix(('b站摘要', 'B站摘要', '哔哩哔哩摘要', 'bili摘要'))
async def bilibili_summary_command(bot, ev: CQEvent):
    """命令式B站视频摘要"""
    msg = ev.message.extract_plain_text().strip()
    if not msg:
        await bot.send(ev, '请提供B站视频链接或BV号')
        return
    
    # 提取视频ID
    video_id = extract_video_id(msg)
    if not video_id:
        await bot.send(ev, '无法识别的视频链接或BV号')
        return
    
    await bot.send(ev, '正在生成视频摘要，请稍候...')
    
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
        duration = video_info.get('duration', 0)
        view = video_info.get('stat', {}).get('view', 0)
        
        # 格式化时长
        minutes = duration // 60
        seconds = duration % 60
        duration_str = f"{minutes}:{seconds:02d}"
        
        # 格式化播放量
        if view >= 10000:
            view_str = f"{view/10000:.1f}万"
        else:
            view_str = str(view)
        
        reply = f"📺 《{title}》\n"
        reply += f"👤 UP主: {author}\n"
        reply += f"⏱️ 时长: {duration_str} | 👁️ 播放: {view_str}\n\n"
        reply += f"📝 AI摘要:\n{summary}"
        
        # 发送摘要
        await bot.send(ev, reply)
        
    except Exception as e:
        await bot.send(ev, f'生成摘要时发生错误: {str(e)}')