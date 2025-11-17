import os
import json
import re
import asyncio
from hoshino import Service, priv
from .dailysum import handle_daily_report_cmd, start_scheduler, PLAYWRIGHT_AVAILABLE, init_dailysum_playwright, gemini_client
from .logger_helper import log_info, log_warning, log_error_msg
from .weekly_report import generate_weekly_report

sv = Service('dailysum', enable_on_default=False, help_='群聊日报功能')

# 创建必要的目录
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 日报相关命令处理
@sv.on_prefix(('日报', 'ribaogn', 'rb'))
async def handle_dailysum(bot, ev):
    msg = ev.message.extract_plain_text().strip()
    await handle_daily_report_cmd(bot, ev, msg)

# 周报相关命令处理
@sv.on_prefix(('周报', 'zhoubao', 'zb'))
async def handle_weekly_report(bot, ev):
    """处理周报相关命令"""
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.send(ev, '抱歉，只有管理员才能使用周报功能')
        return
    
    if not gemini_client:
        await bot.send(ev, 'Gemini API未配置，无法生成周报。请在config.py中设置GEMINI_API_KEY')
        return
    
    current_group_id = str(ev['group_id'])
    msg = ev.message.extract_plain_text().strip()
    
    log_info(f"用户在群 {current_group_id} 触发周报生成，命令: {msg}")
    
    # 解析命令，检查是否指定了群号
    parts = msg.split()
    if len(parts) >= 1 and parts[0].isdigit():
        # 格式：周报 群号
        target_group = parts[0]
        await bot.send(ev, f"正在生成群 {target_group} 的周报，请稍候...")
        success = await generate_weekly_report(gemini_client, bot, target_group, current_group_id)
    else:
        # 格式：周报（生成本群周报）
        await bot.send(ev, f"正在生成本群周报，请稍候...")
        success = await generate_weekly_report(gemini_client, bot, current_group_id)
    
    if not success:
        await bot.send(ev, "周报生成失败，请查看日志了解详情")

# 初始化定时任务
scheduler_started = False
def init():
    global scheduler_started
    if not scheduler_started:
        # 启动定时器
        start_scheduler()
        scheduler_started = True
        
        # 异步初始化Playwright
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(init_dailysum_playwright())
        else:
            loop.run_until_complete(init_dailysum_playwright())

# 自动初始化
init()