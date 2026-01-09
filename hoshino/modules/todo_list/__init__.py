from datetime import datetime, timedelta
import re
import time
from typing import Tuple, Optional
import base64

from hoshino import Service, priv, logger
from hoshino.typing import CQEvent, MessageSegment
from hoshino import aiorequests

try:
    import jionlp
except ImportError:
    jionlp = None
    logger.warning("jionlp not installed, time extraction will be disabled.")

from .data_manager import DataManager
from .scheduler_manager import SchedulerManager
from .render_utils import render_todo_list

# Service Definition (HoshinoBot Style)
sv = Service(
    'todo_list', 
    enable_on_default=True, 
    help_='智能待办清单：\n记 [内容] - 添加待办\n代办 - 查看列表\n完成 [ID] - 完成任务\n删除 [ID] - 删除任务'
)

# Managers
data_manager = DataManager()
scheduler_manager = SchedulerManager()

# Startup Hook to restore jobs
# Hoshino doesn't have a direct 'on_startup' hook exposed easily in modules without hacking,
# but we can run it once when module loads or use a scheduled job that runs immediately.
# However, module load happens on start.
# Let's run it immediately.
try:
    logger.info("Restoring todo list reminders...")
    all_data = data_manager.get_all_todos()
    scheduler_manager.recover_jobs(all_data)
    logger.info("Todo list reminders restored.")
except Exception as e:
    logger.error(f"Failed to restore todo jobs: {e}")

# Helper to get IDs
def get_ids(event: CQEvent) -> Tuple[str, Optional[str]]:
    user_id = str(event.user_id)
    # Hoshino event.group_id might be missing if private
    group_id = str(event.group_id) if event.detail_type == 'group' else None
    return user_id, group_id

@sv.on_prefix(('记', 'todo add', '+'))
async def add_todo(bot, ev: CQEvent):
    user_id, group_id = get_ids(ev)
    raw_content = ev.message.extract_plain_text().strip()
    
    if not raw_content:
        await bot.send(ev, "喵？主人要记什么呢？请在指令后加上内容哦~")
        return

    # Time extraction
    due_date = None
    content = raw_content
    remind_time_str = None

    if jionlp:
        try:
            # time_base is now.
            res = jionlp.ner.extract_time(raw_content, time_base=time.time())
            if res:
                # Take the first extracted time
                time_entity = res[0]
                time_str = time_entity['text']
                time_detail = time_entity['detail']
                
                # Check if valid time point extracted
                if time_detail and 'time' in time_detail and time_detail['time'] and time_detail['time'][0] != 'inf':
                    parsed_time_str = time_detail['time'][0]
                    try:
                        # jionlp returns YYYY-mm-dd HH:MM:SS format typically
                        parsed_time = datetime.strptime(parsed_time_str, "%Y-%m-%d %H:%M:%S")
                        
                        if parsed_time > datetime.now():
                            due_date = parsed_time
                            remind_time_str = parsed_time.strftime("%Y-%m-%d %H:%M:%S")
                            
                            # Remove time string from content
                            content = content.replace(time_str, "").strip()
                            # Clean up extra spaces
                            content = re.sub(r'\s+', ' ', content)
                    except ValueError:
                        pass
        except Exception as e:
            logger.error(f"Time extraction failed: {e}")

    if not content:
        content = "（无内容）"

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save to DB
    item = data_manager.add_todo(user_id, group_id, content, created_at, remind_time_str)
    
    # Add scheduler job
    if due_date:
        scheduler_manager.add_job(item["id"], due_date, user_id, group_id, content)
        reply = f"记下啦！主人，ID是 {item['id']} 喵~\n会在 {remind_time_str} 提醒你去做「{content}」哦！"
    else:
        reply = f"记下啦！主人，ID是 {item['id']} 喵~\n内容：「{content}」"
        
    await bot.send(ev, reply)

@sv.on_fullmatch(('代办', 'todo list', 'dd', '待办'))
async def list_todo(bot, ev: CQEvent):
    user_id, group_id = get_ids(ev)
    
    # User requested "未完成任务"
    todos = data_manager.get_pending_todos(user_id, group_id)
    
    # Render
    img_bytes = await render_todo_list(todos)
    
    if not img_bytes:
        await bot.send(ev, "呜呜...生成图片失败了喵...")
        return
        
    # Send image
    # HoshinoBot (Nonebot1) uses MessageSegment
    # We need to construct base64 if needed or use segment
    # Usually [CQ:image,file=base64://...]
    b64_str = base64.b64encode(img_bytes).decode('ascii')
    msg = f"[CQ:image,file=base64://{b64_str}]"
    await bot.send(ev, msg)

@sv.on_prefix(('完成', 'done'))
async def finish_todo(bot, ev: CQEvent):
    user_id, group_id = get_ids(ev)
    todo_id = ev.message.extract_plain_text().strip()
    
    if not todo_id:
        await bot.send(ev, "主人，请告诉我要完成哪个 ID 喵~")
        return

    item = data_manager.finish_todo(user_id, group_id, todo_id)
    if item:
        # Remove job
        scheduler_manager.remove_job(todo_id)
        await bot.send(ev, f"好耶！ID {todo_id} 「{item['content']}」完成啦！主人真棒喵~ 🌸")
    else:
        await bot.send(ev, f"喵？找不到 ID 为 {todo_id} 的待办事项哦...")

@sv.on_prefix(('删除', 'del', 'rm'))
async def delete_todo(bot, ev: CQEvent):
    user_id, group_id = get_ids(ev)
    todo_id = ev.message.extract_plain_text().strip()
    
    if not todo_id:
        await bot.send(ev, "主人，请告诉我要删除哪个 ID 喵~")
        return

    success = data_manager.delete_todo(user_id, group_id, todo_id)
    if success:
        scheduler_manager.remove_job(todo_id)
        await bot.send(ev, f"遵命！ID {todo_id} 已经删掉啦喵~ 🗑️")
    else:
        await bot.send(ev, f"喵？找不到 ID 为 {todo_id} 的待办事项哦...")

@sv.on_prefix(('清空代办', 'clear todo', '清除所有', '清空', 'clear all'))
async def clear_todo(bot, ev: CQEvent):
    # Require confirmation
    user_id, group_id = get_ids(ev)
    confirm = ev.message.extract_plain_text().strip()
    
    if confirm != "确认":
        await bot.send(ev, "主人真的要清空所有待办吗？😱\n如果确认，请发送「清空代办 确认」喵！")
        return
    
    # Remove all scheduled jobs for this user/group first
    todos = data_manager.get_user_todos(user_id, group_id)
    for t in todos:
        if not t['is_done']:
            scheduler_manager.remove_job(t['id'])
            
    data_manager.clear_todos(user_id, group_id)
    await bot.send(ev, "呼...所有待办都清空啦，一片空白喵~ ✨")

@sv.on_prefix(('清空已完成', 'clean done'))
async def clean_done(bot, ev: CQEvent):
    user_id, group_id = get_ids(ev)
    count = data_manager.delete_completed_todos(user_id, group_id)
    if count > 0:
        await bot.send(ev, f"好哒！已经清理了 {count} 条已完成的任务喵~ 🧹")
    else:
        await bot.send(ev, "喵？没有已完成的任务需要清理哦~")
