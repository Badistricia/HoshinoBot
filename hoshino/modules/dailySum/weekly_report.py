"""
周报生成模块
使用Gemini直接生成完整HTML的周报
"""
import os
import json
import asyncio
import base64
from datetime import datetime, timedelta
from .logger_helper import log_info, log_debug, log_warning, log_error_msg, logged
from .config import DATA_DIR, GEMINI_WEEKLY_PROMPT, PLAYWRIGHT_AVAILABLE
from .test_html_report_2 import init_playwright, html_to_screenshot

# 生成周报HTML（使用Gemini）
@logged
async def generate_weekly_html(gemini_client, group_id, date_range, chat_logs):
    """
    使用Gemini生成周报HTML
    :param gemini_client: Gemini客户端实例
    :param group_id: 群号
    :param date_range: 日期范围字符串，如"2025-11-10 至 2025-11-16"
    :param chat_logs: 聊天记录文本
    :return: HTML字符串
    """
    if not gemini_client:
        log_error_msg("Gemini客户端未初始化，无法生成周报")
        return None
    
    log_info(f"开始为群 {group_id} 生成周报HTML，日期范围: {date_range}")
    
    try:
        # 构建提示词
        prompt = GEMINI_WEEKLY_PROMPT.format(
            group_name=group_id,
            date_range=date_range,
            chat_log=chat_logs
        )
        
        log_info(f"提示词长度: {len(prompt)} 字符")
        
        # 调用Gemini生成HTML
        html_content = await gemini_client.generate_html(prompt)
        
        if html_content:
            log_info(f"Gemini成功生成周报HTML，长度: {len(html_content)} 字符")
            return html_content
        else:
            log_error_msg("Gemini生成HTML失败")
            return None
    
    except Exception as e:
        log_error_msg(f"生成周报HTML出错: {str(e)}")
        import traceback
        log_error_msg(traceback.format_exc())
        return None

# 将HTML转换为图片
@logged
async def html_to_image_screenshot(html_content, group_id, date_str):
    """
    将HTML内容转换为图片
    :param html_content: HTML字符串
    :param group_id: 群号
    :param date_str: 日期字符串
    :return: 图片二进制数据
    """
    if not PLAYWRIGHT_AVAILABLE:
        log_warning("Playwright未安装，无法生成图片")
        return None
    
    try:
        # 保存HTML到临时文件
        import time
        timestamp = str(int(time.time() * 1000))
        file_suffix = f"{group_id}_weekly_{timestamp}"
        temp_html_path = os.path.join(DATA_DIR, f"weekly_{file_suffix}.html")
        
        with open(temp_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        log_info(f"HTML已保存到: {temp_html_path}")
        
        # 初始化Playwright
        if not await init_playwright():
            log_warning("初始化Playwright失败")
            return None
        
        # 转换为图片
        temp_img_path = os.path.join(DATA_DIR, f"weekly_{file_suffix}.png")
        
        if await html_to_screenshot(os.path.abspath(temp_html_path), temp_img_path):
            # 读取图片数据
            if os.path.exists(temp_img_path):
                file_size = os.path.getsize(temp_img_path)
                log_info(f"图片生成成功，大小: {file_size / 1024:.2f} KB")
                
                if file_size < 5000:
                    log_warning(f"图片文件过小: {file_size} 字节，可能生成失败")
                    return None
                
                with open(temp_img_path, 'rb') as f:
                    image_data = f.read()
                
                # 清理临时文件
                try:
                    os.remove(temp_html_path)
                    os.remove(temp_img_path)
                    log_info("临时文件已清理")
                except Exception as e:
                    log_warning(f"清理临时文件失败: {str(e)}")
                
                return image_data
            else:
                log_warning("图片文件不存在")
                return None
        else:
            log_warning("HTML转图片失败")
            return None
    
    except Exception as e:
        log_error_msg(f"HTML转图片出错: {str(e)}")
        import traceback
        log_error_msg(traceback.format_exc())
        return None

# 生成周报
@logged
async def generate_weekly_report(gemini_client, bot, group_id, current_group_id=None):
    """
    生成并发送周报
    :param gemini_client: Gemini客户端实例
    :param bot: 机器人实例
    :param group_id: 目标群号（要生成周报的群）
    :param current_group_id: 当前群号（接收周报的群），为None时发送到target_group
    :return: 是否成功
    """
    if not gemini_client:
        log_error_msg("Gemini客户端未初始化")
        return False
    
    # 如果未指定接收群，则发送到目标群
    if current_group_id is None:
        current_group_id = group_id
    
    log_info(f"开始生成群 {group_id} 的周报，将发送到群 {current_group_id}")
    
    try:
        # 计算日期范围（过去7天）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        date_range = f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
        
        # 收集过去7天的聊天记录
        log_info("开始收集过去7天的聊天记录...")
        all_messages = []
        
        for day_offset in range(7):
            date = end_date - timedelta(days=day_offset)
            date_str = date.strftime('%Y-%m-%d')
            log_file = os.path.join(DATA_DIR, f"{group_id}_{date_str}.json")
            
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                        all_messages.extend(messages)
                        log_info(f"加载 {date_str} 的记录，共 {len(messages)} 条")
                except Exception as e:
                    log_warning(f"加载 {date_str} 的记录失败: {str(e)}")
        
        if not all_messages:
            log_warning(f"群 {group_id} 过去7天没有聊天记录")
            return False
        
        log_info(f"共收集到 {len(all_messages)} 条消息")
        
        # 简化聊天记录格式
        from .dailysum import optimize_chat_format
        chat_log = optimize_chat_format(all_messages)
        
        # 如果记录太长，截断
        MAX_LENGTH = 80000
        if len(chat_log) > MAX_LENGTH:
            log_warning(f"聊天记录过长({len(chat_log)}字符)，截断到{MAX_LENGTH}字符")
            chat_log = chat_log[:MAX_LENGTH] + "\n\n[由于长度限制，部分记录被省略]"
        
        log_info(f"优化后的聊天记录长度: {len(chat_log)} 字符")
        
        # 生成HTML
        html_content = await generate_weekly_html(gemini_client, group_id, date_range, chat_log)
        
        if not html_content:
            log_error_msg("HTML生成失败")
            return False
        
        # 转换为图片
        image_data = await html_to_image_screenshot(html_content, group_id, end_date.strftime('%Y-%m-%d'))
        
        if not image_data or len(image_data) < 1000:
            log_warning("图片生成失败或过小，尝试发送HTML文本预览")
            # 可以考虑发送纯文本版本或HTML预览
            return False
        
        # 发送周报
        try:
            from nonebot.message import MessageSegment
            
            # 发送标题
            await bot.send_group_msg(
                group_id=int(current_group_id),
                message=f"【群 {group_id} 周报】\n{date_range}"
            )
            
            # 发送图片
            b64_str = base64.b64encode(image_data).decode()
            await bot.send_group_msg(
                group_id=int(current_group_id),
                message=MessageSegment.image(f'base64://{b64_str}')
            )
            
            log_info(f"成功向群 {current_group_id} 发送群 {group_id} 的周报")
            return True
        
        except Exception as e:
            log_error_msg(f"发送周报失败: {str(e)}")
            import traceback
            log_error_msg(traceback.format_exc())
            return False
    
    except Exception as e:
        log_error_msg(f"生成周报出错: {str(e)}")
        import traceback
        log_error_msg(traceback.format_exc())
        return False
