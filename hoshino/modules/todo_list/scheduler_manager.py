from datetime import datetime
from typing import Optional
import nonebot
from nonebot import get_bot
from hoshino import logger

# Try to get scheduler from nonebot (Nonebot1 standard)
try:
    from nonebot import scheduler
except ImportError:
    # Fallback: try to create a local scheduler if nonebot doesn't provide one
    # This happens if HoshinoBot is not using the standard scheduler plugin
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler()
        scheduler.start()
        logger.info("Created local AsyncIOScheduler for todo_list")
    except ImportError:
        logger.error("APScheduler not found. Todo reminders will not work.")
        scheduler = None

async def send_reminder(user_id: str, group_id: Optional[str], content: str):
    try:
        bot = get_bot()
        msg = f"⏰ 提醒：[CQ:at,qq={user_id}] 该去 {content} 了！"
        # HoshinoBot (Nonebot1) API
        if group_id:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        else:
            await bot.send_private_msg(user_id=int(user_id), message=msg)
    except Exception as e:
        logger.error(f"Failed to send reminder for user {user_id}: {e}")

class SchedulerManager:
    def add_job(self, todo_id: str, run_date: datetime, user_id: str, group_id: Optional[str], content: str):
        if not scheduler:
            logger.warning("Scheduler not available, skipping job addition.")
            return

        try:
            scheduler.add_job(
                send_reminder,
                "date",
                run_date=run_date,
                args=[user_id, group_id, content],
                id=f"todo_{todo_id}",
                replace_existing=True
            )
            logger.info(f"Added reminder job: todo_{todo_id} at {run_date}")
        except Exception as e:
            logger.error(f"Failed to add job todo_{todo_id}: {e}")

    def remove_job(self, todo_id: str):
        if not scheduler:
            return
            
        job_id = f"todo_{todo_id}"
        try:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                logger.info(f"Removed reminder job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")

    def recover_jobs(self, all_data: dict):
        """
        Recover jobs from data on startup.
        all_data structure: { "group_x_user_y": [ { "id": "...", "due_date": "...", "is_done": false } ] }
        """
        if not scheduler:
            return

        count = 0
        now = datetime.now()
        
        for key, todos in all_data.items():
            # Parse key to get context
            # key format: "group_{gid}_user_{uid}" or "user_{uid}"
            parts = key.split('_')
            group_id = None
            user_id = None
            
            if key.startswith("group_"):
                # group_{gid}_user_{uid}
                # Find 'user' index to split
                try:
                    user_idx = parts.index("user")
                    group_id = "_".join(parts[1:user_idx])
                    user_id = "_".join(parts[user_idx+1:])
                except ValueError:
                    continue
            elif key.startswith("user_"):
                user_id = "_".join(parts[1:])
            
            if not user_id:
                continue

            for todo in todos:
                if todo.get("is_done"):
                    continue
                
                due_date_str = todo.get("due_date")
                if not due_date_str:
                    continue

                try:
                    # Assume ISO format or similar standard format stored in JSON
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M:%S")
                    
                    if due_date > now:
                        self.add_job(
                            todo["id"],
                            due_date,
                            user_id,
                            group_id,
                            todo["content"]
                        )
                        count += 1
                except ValueError:
                    logger.error(f"Invalid date format for todo {todo['id']}: {due_date_str}")
        
        logger.info(f"Recovered {count} pending reminders.")
