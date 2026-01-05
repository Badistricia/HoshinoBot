from hoshino import Service, priv
from hoshino.typing import CQEvent
import nonebot
from .memory import MemoryStore
from .guard import TrafficGuard
from .judge import TheJudge
from .responder import Responder
from . import config
from .manager import get_instance

sv = Service('chatsentinel', enable_on_default=False, visible=True, help_='ChatSentinel: 潜水系群聊AI\n指令：开启/关闭潜水姬')

# Shared components
judge = TheJudge()
responder = Responder()

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

from .manager import get_instance, GroupInstance, instances

async def execute_logic(bot, gid, inst: GroupInstance):
    # Double check enabled state (in case disabled during buffer wait)
    if not inst.enabled:
        inst.guard.pop_buffer() # Clear buffer anyway
        return

    # Retrieve batch
    batch_msgs = inst.guard.pop_buffer()
    # sv.logger.info(f"[ChatSentinel] Processing batch for Group {gid}...")
    
    # Judge
    try:
        decision = await judge.check(batch_msgs)
    except Exception as e:
        sv.logger.error(f"Judge Error: {e}")
        decision = False
    
    if not decision:
        return

    # sv.logger.info(f"[ChatSentinel] Judge said YES! Generating reply...")
    # Generate Reply
    # Use more context for generation, but maybe not 500 lines? 50 is fine for reply generation.
    # Responder usually only needs recent context.
    full_context = inst.memory.get_full_context_str(limit=50)
        try:
            # Pass gid to responder to use aichat's config
            reply = await responder.generate(gid, full_context)
            if reply:
                # Add Bot's reply to memory so it knows what it said
                inst.memory.add("ChatSentinel", reply)
                await bot.send_group_msg(group_id=gid, message=reply)
                
                # Cooldown
                # Reduced to 60s per user request
                inst.guard.set_cooldown(20)
        except Exception as e:
            sv.logger.error(f"Responder Error: {e}")

@sv.scheduled_job('interval', seconds=5)
async def check_timeouts():
    try:
        bot = nonebot.get_bot()
    except:
        return 

    for gid, inst in instances.items():
        # Check if enabled inside should_trigger or here?
        # should_trigger checks cooldown and buffer.
        # But if not enabled, we shouldn't trigger.
        if not inst.enabled:
            continue
            
        if inst.guard.should_trigger():
            await execute_logic(bot, gid, inst)
