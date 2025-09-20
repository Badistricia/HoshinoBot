import os
import re
import asyncio
from hoshino import Service
from hoshino.typing import CQEvent
from .bilibili_api import extract_video_id_async, get_video_info, get_video_subtitle, load_cookies
from .ai_summary import generate_summary

sv = Service('bilisummary', help_='B站视频解析和摘要\n自动识别B站链接（包括小程序）发送基本信息\n回复"B站解析"或"AI总结"可获取AI摘要', enable_on_default=True)

# B站链接正则表达式
BILIBILI_URL_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?(?:bilibili\.com/video/|b23\.tv/|m\.bilibili\.com/video/)(BV[A-Za-z0-9]+|av\d+)|(?:^|\s)(BV[A-Za-z0-9]+|av\d+)(?:\s|$)',
    re.IGNORECASE
)

def create_bilibili_miniapp(video_info):
    """创建B站视频信息文本"""
    title = video_info.get('title', '未知标题')
    author = video_info.get('owner', {}).get('name', '未知UP主')
    desc = video_info.get('desc', '')[:50] + '...' if len(video_info.get('desc', '')) > 50 else video_info.get('desc', '')
    bvid = video_info.get('bvid', '')
    video_url = f"https://www.bilibili.com/video/{bvid}"
    
    # 获取更多视频信息
    stat = video_info.get('stat', {})
    view = stat.get('view', 0)  # 播放量
    like = stat.get('like', 0)  # 点赞数
    coin = stat.get('coin', 0)  # 投币数
    favorite = stat.get('favorite', 0)  # 收藏数
    danmaku = stat.get('danmaku', 0)  # 弹幕数
    
    # 获取视频分区信息
    tname = video_info.get('tname', '未知分区')
    
    # 格式化数字
    def format_number(num):
        if num >= 10000:
            return f"{num/10000:.1f}万"
        return str(num)
    
    # 构建视频信息文本
    info_text = (
        f"标题：{title}\n"
        f"UP主：{author}\n"
        f"分区：{tname}\n"
        f"播放：{format_number(view)} | 点赞：{format_number(like)} | 弹幕：{format_number(danmaku)}\n"
        f"简介：{desc}\n"
        f"链接：{video_url}"
    )
    
    return info_text

# 检测QQ小程序中的B站链接
def extract_miniprogram_bilibili_url(msg):
    """从QQ小程序消息中提取B站链接"""
    # 匹配小程序格式 [CQ:json,data=...]
    json_match = re.search(r'\[CQ:json,data=([^\]]+)\]', msg)
    if not json_match:
        return None
    
    import json
    try:
        # 解析JSON数据
        json_str = json_match.group(1)
        # 处理转义字符
        json_str = json_str.replace('&amp;', '&').replace('&#44;', ',').replace('&#91;', '[').replace('&#93;', ']')
        json_data = json.loads(json_str)
        
        # 检查是否是B站小程序 - 支持多种小程序类型
        app_type = json_data.get('app', '')
        if app_type in ['com.tencent.structmsg', 'com.tencent.miniapp_01']:
            meta = json_data.get('meta', {})
            detail_1 = meta.get('detail_1', {})
            
            # 查找B站相关的URL - 优先检查qqdocurl
            qqdocurl = detail_1.get('qqdocurl', '')
            if qqdocurl and ('bilibili.com' in qqdocurl or 'b23.tv' in qqdocurl):
                sv.logger.info(f'从小程序提取到B站链接: {qqdocurl}')
                return qqdocurl
            
            # 检查url字段
            url = detail_1.get('url', '')
            if url and ('bilibili.com' in url or 'b23.tv' in url):
                sv.logger.info(f'从小程序url字段提取到B站链接: {url}')
                return url
                
            # 检查title是否包含哔哩哔哩
            title = detail_1.get('title', '')
            if title and '哔哩哔哩' in title:
                # 如果标题包含哔哩哔哩，再次检查所有字段
                for key, value in detail_1.items():
                    if isinstance(value, str) and ('bilibili.com' in value or 'b23.tv' in value):
                        sv.logger.info(f'从小程序{key}字段提取到B站链接: {value}')
                        return value
                        
    except Exception as e:
        sv.logger.error(f'解析小程序JSON失败: {str(e)}')
        sv.logger.debug(f'原始消息: {msg}')
    
    return None

# 监听所有群消息，检测B站链接
@sv.on_message('group')
async def auto_bilibili_parse(bot, ev: CQEvent):
    """自动解析B站链接并发送视频基本信息（不包含AI摘要）"""
    msg = str(ev.message).strip()
    plain_msg = str(ev.message.extract_plain_text()).strip()
    
    # 移除可能的markdown格式符号
    plain_msg = plain_msg.strip('`').strip()
    
    # 检查是否包含B站链接（普通链接或小程序）
    video_id = None
    is_miniprogram = False
    
    # 先检查普通B站链接
    if BILIBILI_URL_PATTERN.search(plain_msg):
        video_id = await extract_video_id_async(plain_msg)
    
    # 如果没有找到普通链接，检查小程序
    if not video_id:
        miniprogram_url = extract_miniprogram_bilibili_url(msg)
        if miniprogram_url:
            video_id = await extract_video_id_async(miniprogram_url)
            is_miniprogram = True
    
    if not video_id:
        return
    
    try:
        # 尝试加载cookies
        cookies = load_cookies()
        if not cookies:
            # 如果没有cookies，提示用户登录
            await bot.send(ev, '检测到B站链接，但未登录B站账号。\n发送"b站设置cookie"手动设置Cookie（推荐），或发送"b站帮助"查看使用说明。')
            return
        
        # 获取视频信息
        video_info = await get_video_info(video_id, cookies)
        if not video_info:
            await bot.send(ev, '获取视频信息失败，可能需要重新登录B站账号')
            return
        
        # 获取视频基本信息
        title = video_info.get('title', '未知标题')
        author = video_info.get('owner', {}).get('name', '未知UP主')
        duration = video_info.get('duration', 0)
        desc = video_info.get('desc', '')[:50] + '...' if len(video_info.get('desc', '')) > 50 else video_info.get('desc', '')
        bvid = video_info.get('bvid', '')
        video_url = f"https://www.bilibili.com/video/{bvid}"
        
        # 获取统计信息
        stat = video_info.get('stat', {})
        view = stat.get('view', 0)  # 播放量
        like = stat.get('like', 0)  # 点赞数
        coin = stat.get('coin', 0)  # 投币数
        favorite = stat.get('favorite', 0)  # 收藏数
        danmaku = stat.get('danmaku', 0)  # 弹幕数
        
        # 获取视频分区信息
        tname = video_info.get('tname', '未知分区')
        
        # 格式化数字
        def format_number(num):
            if num >= 10000:
                return f"{num/10000:.1f}万"
            return str(num)
        
        # 转换时长格式
        minutes = duration // 60
        seconds = duration % 60
        duration_str = f"{minutes}:{seconds:02d}"
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
        
        # 构建视频基本信息文本（不包含AI摘要）
        response = f"📺 {title}\n"
        response += f"👤 UP主: {author}\n"
        response += f"📂 分区: {tname}\n"
        response += f"⏱️ 时长: {duration_str}\n"
        response += f"👀 播放: {format_number(view)} | 👍 点赞: {format_number(like)} | 💬 弹幕: {format_number(danmaku)}\n"
        if desc:
            response += f"📝 简介: {desc}\n"
        response += f"🔗 链接: {video_url}\n\n"
        response += f"💡 回复此消息并发送「B站解析」或「AI总结」可获取视频摘要"
        
        # 发送视频基本信息
        await bot.send(ev, response)
        
    except Exception as e:
        sv.logger.error(f'解析B站链接失败: {str(e)}')
        await bot.send(ev, f'解析B站链接失败: {str(e)}')

@sv.on_keyword(('B站解析', 'b站解析', 'AI总结', 'ai总结', '总结', '摘要'))
async def bilibili_summary_reply(bot, ev: CQEvent):
    """回复B站解析或AI总结关键词时，对引用的B站链接进行AI总结"""
    msg = str(ev.message)
    plain_msg = str(ev.message.extract_plain_text()).strip()
    
    # 检查是否有引用消息
    reply_match = re.search(r'\[CQ:reply,id=(\d+)\]', msg)
    if not reply_match:
        return
    
    try:
        # 获取被引用的消息
        reply_id = reply_match.group(1)
        reply_msg = await bot.get_msg(message_id=int(reply_id))
        reply_content = str(reply_msg['message'])
        reply_plain_content = reply_msg.get('raw_message', '')
        
        # 检查引用的消息是否包含B站链接（普通链接或小程序）
        video_id = None
        
        # 先检查普通B站链接
        if BILIBILI_URL_PATTERN.search(reply_plain_content):
            video_id = await extract_video_id_async(reply_plain_content)
        
        # 如果没有找到普通链接，检查小程序
        if not video_id:
            miniprogram_url = extract_miniprogram_bilibili_url(reply_content)
            if miniprogram_url:
                video_id = await extract_video_id_async(miniprogram_url)
        
        if not video_id:
            return
        
        await bot.send(ev, '正在生成视频摘要，请稍候...')
        
        # 尝试加载cookies
        cookies = load_cookies()
        
        # 获取视频信息和字幕
        video_info = await get_video_info(video_id, cookies)
        if not video_info:
            await bot.send(ev, '获取视频信息失败')
            return
        
        subtitle_text = await get_video_subtitle(video_id, cookies)
        
        # 生成摘要
        summary = await generate_summary(video_info, subtitle_text)
        
        if summary:
            # 格式化输出
            title = video_info.get('title', '未知标题')
            author = video_info.get('owner', {}).get('name', '未知UP主')
            duration = video_info.get('duration', 0)
            
            # 转换时长格式
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            
            response = f"📺 {title}\n"
            response += f"👤 UP主: {author}\n"
            response += f"⏱️ 时长: {duration_str}\n\n"
            response += f"📝 AI摘要:\n{summary}"
            
            await bot.send(ev, response)
        else:
            await bot.send(ev, '生成摘要失败，可能是视频没有字幕或字幕获取失败')
            
    except Exception as e:
        sv.logger.error(f'生成摘要失败: {str(e)}')
        await bot.send(ev, f'生成摘要失败: {str(e)}')

@sv.on_prefix(('b站摘要', 'B站摘要', '哔哩哔哩摘要', 'bili摘要'))
async def bilibili_summary_command(bot, ev: CQEvent):
    """命令式B站视频摘要"""
    url = str(ev.message.extract_plain_text()).strip()
    
    if not url:
        await bot.send(ev, '请提供B站视频链接\n用法: b站摘要 [视频链接]')
        return
    
    # 提取视频ID
    video_id = await extract_video_id_async(url)
    if not video_id:
        await bot.send(ev, '无法识别的B站链接格式')
        return
    
    try:
        await bot.send(ev, '正在获取视频信息和生成摘要，请稍候...')
        
        # 尝试加载cookies
        cookies = load_cookies()
        if not cookies:
            await bot.send(ev, '未登录B站账号，发送"b站设置cookie"手动设置Cookie（推荐）')
            return
        
        # 获取视频信息
        video_info = await get_video_info(video_id, cookies)
        if not video_info:
            await bot.send(ev, '获取视频信息失败，请检查链接是否正确或重新登录B站账号')
            return
        
        # 获取字幕
        subtitle_text = await get_video_subtitle(video_id, cookies)
        
        # 生成摘要
        summary = await generate_summary(video_info, subtitle_text)
        
        if summary:
            # 格式化输出
            title = video_info.get('title', '未知标题')
            author = video_info.get('owner', {}).get('name', '未知UP主')
            duration = video_info.get('duration', 0)
            view_count = video_info.get('stat', {}).get('view', 0)
            like_count = video_info.get('stat', {}).get('like', 0)
            
            # 转换时长格式
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            
            response = f"📺 {title}\n"
            response += f"👤 UP主: {author}\n"
            response += f"⏱️ 时长: {duration_str}\n"
            response += f"👀 播放: {view_count:,} | 👍 点赞: {like_count:,}\n\n"
            response += f"📝 AI摘要:\n{summary}"
            
            await bot.send(ev, response)
        else:
            await bot.send(ev, '生成摘要失败，可能是视频没有字幕或字幕获取失败')
            
    except Exception as e:
        sv.logger.error(f'生成摘要失败: {str(e)}')
        await bot.send(ev, f'生成摘要时发生错误: {str(e)}')

@sv.on_fullmatch(('b站登录', 'B站登录', '哔哩哔哩登录', 'bili登录'))
async def bilibili_login_command(bot, ev: CQEvent):
    """B站登录命令"""
    try:
        from .bilibili_api import login_with_qrcode
        
        await bot.send(ev, '正在生成B站登录二维码，请稍候...')
        
        # 调用登录函数
        result = await login_with_qrcode()
        
        if result:
            await bot.send(ev, 'B站登录成功！现在可以正常使用B站相关功能了。')
        else:
            await bot.send(ev, 'B站登录失败或已取消，请重试。')
            
    except Exception as e:
        sv.logger.error(f'B站登录失败: {str(e)}')
        await bot.send(ev, f'B站登录时发生错误: {str(e)}')

@sv.on_prefix(('b站设置cookie', 'B站设置cookie', '设置b站cookie'))
async def bilibili_set_cookie_command(bot, ev: CQEvent):
    """手动设置B站cookies"""
    cookie_str = str(ev.message.extract_plain_text()).strip()
    
    if not cookie_str:
        help_msg = """🍪 手动设置B站Cookie

📋 使用方法：
b站设置cookie [cookie字符串]

🔑 获取Cookie步骤：
1. 登录 bilibili.com
2. 按F12打开开发者工具
3. 切换到Network标签
4. 刷新页面
5. 找到任意请求，查看Request Headers
6. 复制Cookie字段的完整内容

💡 示例：
b站设置cookie SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx

⚠️ 注意：Cookie包含敏感信息，请在私聊中使用此命令"""
        
        await bot.send(ev, help_msg)
        return
    
    try:
        from .bilibili_api import save_cookies
        
        # 解析cookie字符串
        cookies = {}
        for item in cookie_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key.strip()] = value.strip()
        
        # 检查必要的cookie字段
        required_fields = ['SESSDATA', 'bili_jct', 'DedeUserID']
        missing_fields = [field for field in required_fields if field not in cookies]
        
        if missing_fields:
            await bot.send(ev, f'Cookie缺少必要字段: {", ".join(missing_fields)}\n请确保包含SESSDATA、bili_jct、DedeUserID等关键字段')
            return
        
        # 保存cookies
        if save_cookies(cookies):
            await bot.send(ev, '✅ B站Cookie设置成功！现在可以正常使用B站相关功能了。')
        else:
            await bot.send(ev, '❌ Cookie保存失败，请检查格式是否正确')
            
    except Exception as e:
        sv.logger.error(f'设置B站Cookie失败: {str(e)}')
        await bot.send(ev, f'设置Cookie时发生错误: {str(e)}')

@sv.on_fullmatch(('b站帮助', 'B站帮助', '哔哩哔哩帮助', 'bili帮助'))
async def bilibili_help_command(bot, ev: CQEvent):
    """B站插件帮助信息"""
    help_text = """📺 B站视频解析和摘要插件

🔧 功能说明：
• 自动识别群内B站链接（包括QQ小程序分享）并发送基本信息
• 回复包含B站链接的消息并发送"B站解析"、"AI总结"、"总结"或"摘要"获取AI摘要
• 使用命令直接获取视频摘要

📋 命令列表：
• b站登录 - 获取B站登录二维码（可能不稳定）
• b站设置cookie - 手动设置B站Cookie（推荐）
• b站摘要 [链接] - 直接获取视频摘要
• b站帮助 - 显示此帮助信息

🍪 Cookie设置方法（推荐）：
1. 浏览器登录 bilibili.com
2. 按F12打开开发者工具
3. 切换到Network标签，刷新页面
4. 找到任意请求，复制Cookie字段
5. 私聊发送：b站设置cookie [完整cookie]

⚠️ 注意事项：
• 首次使用需要登录B站账号
• 推荐使用手动设置Cookie方式
• Cookie包含敏感信息，请在私聊中设置
• 如果功能异常，请尝试重新设置Cookie

💡 使用提示：
• 直接发送B站链接或小程序分享即可自动解析基本信息
• 回复视频消息并发送"B站解析"或"AI总结"获取详细摘要
• 支持BV号、AV号和各种B站链接格式
• 支持QQ小程序分享的B站视频链接"""
    
    await bot.send(ev, help_text)