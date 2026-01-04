from hoshino import Service, priv
from hoshino.typing import CQEvent
import nonebot
from .memory import MemoryStore
from .guard import TrafficGuard
from .judge import TheJudge
from .responder import Responder
from . import config

sv = Service('chatsentinel', enable_on_default=False, visible=True, help_='ChatSentinel: 潜水系群聊AI\n指令：开启/关闭潜水姬')

class GroupInstance:
    def __init__(self):
        self.memory = MemoryStore(maxlen=config.HISTORY_LEN)
        self.guard = TrafficGuard()
        self.enabled = False # Default disabled per request

# Shared components
judge = TheJudge()
responder = Responder()
instances = {}

def get_instance(group_id) -> GroupInstance:
    if group_id not in instances:
        instances[group_id] = GroupInstance()
    return instances[group_id]

@sv.on_fullmatch(('开启潜水姬', '启用潜水姬', '开启潜水AI', 'enable_chatsentinel'))
async def enable_service(bot, ev: CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '只有管理员可以开启哦~')
    
    gid = ev.group_id
    inst = get_instance(gid)
    inst.enabled = True
    await bot.send(ev, '潜水姬已开启！我会默默观察大家的喵~ 😺')

@sv.on_fullmatch(('关闭潜水姬', '禁用潜水姬', '关闭潜水AI', 'disable_chatsentinel'))
async def disable_service(bot, ev: CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '只有管理员可以关闭哦~')
        
    gid = ev.group_id
    inst = get_instance(gid)
    inst.enabled = False
    await bot.send(ev, '潜水姬已关闭！我去休息啦~ 💤')

@sv.on_message('group')
async def handle_msg(bot, ev: CQEvent):
    gid = ev.group_id
    text = str(ev.message).strip()
    
    # Ignore own messages (prevent loops if not handled by framework)
    if ev.user_id == ev.self_id:
        return

    sender = ev.sender.get('card') or ev.sender.get('nickname') or str(ev.user_id)
    
    inst = get_instance(gid)
    
    # 1. Record to memory (always, even if disabled, to maintain context for when enabled)
    inst.memory.add(sender, text)
    
    # Check if enabled
    if not inst.enabled:
        return

    # 2. Add to buffer (filter applied inside)
    # Note: Only add to buffer if it's a "user" message suitable for judging
    inst.guard.add_to_buffer(text)
    
    # 3. Trigger check
    if inst.guard.should_trigger():
        await execute_logic(bot, gid, inst)

async def execute_logic(bot, gid, inst: GroupInstance):
    # Double check enabled state (in case disabled during buffer wait)
    if not inst.enabled:
        inst.guard.pop_buffer() # Clear buffer anyway
        return

    # Retrieve batch
    batch_msgs = inst.guard.pop_buffer()
    sv.logger.info(f"[ChatSentinel] Processing batch for Group {gid}...")
    
    # Judge
    try:
        decision = await judge.check(batch_msgs)
    except Exception as e:
        sv.logger.error(f"Judge Error: {e}")
        decision = False
    
    if decision:
        sv.logger.info(f"[ChatSentinel] Judge said YES! Generating reply...")
        # Generate Reply
        full_context = inst.memory.get_full_context_str()
        try:
            # Pass gid to responder to use aichat's config
            reply = await responder.generate(gid, full_context)
            if reply:
                # Add Bot's reply to memory so it knows what it said
                inst.memory.add("ChatSentinel", reply)
                await bot.send_group_msg(group_id=gid, message=reply)
                
                # Cooldown
                inst.guard.set_cooldown(120)
        except Exception as e:
            sv.logger.error(f"Responder Error: {e}")

@sv.scheduled_job('interval', seconds=5)
async def check_timeouts():
    try:
        bot = nonebot.get_bot()
    except:
        return 

    for gid, inst in instances.items():
        if inst.guard.should_trigger():
            await execute_logic(bot, gid, inst)
