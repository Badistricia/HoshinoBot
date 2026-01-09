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
    # This ensures that even if we trigger immediately, the current message is in the context.
    inst.memory.add(sender, str(ev.user_id), text)
    
    # Check if enabled
    if not inst.enabled:
        return

    # 2. Add to buffer (filter applied inside)
    # The buffer is for "batching" triggers, but context comes from memory.
    inst.guard.add_to_buffer(text)
    
    # 3. Trigger check
    # Check for keywords for immediate response
    keywords = ['凯留', '臭鼬', '接头霸王', '黑猫', '佩可', '可可萝']
    is_urgent = any(k in text for k in keywords)
    
    should_run = False
    if is_urgent:
        # Urgent messages trigger immediately if limits allow
        if inst.guard.check_limits():
            should_run = True
    elif inst.guard.should_trigger():
        # Normal batch trigger
        should_run = True
        
    if should_run:
        await execute_logic(bot, gid, inst)

from .manager import get_instance, GroupInstance, instances

async def execute_logic(bot, gid, inst: GroupInstance):
    # Double check enabled state (in case disabled during buffer wait)
    if not inst.enabled:
        inst.guard.pop_buffer() # Clear buffer anyway
        return

    # Retrieve batch
    # We still pop buffer to clear it and reset counter, even if we don't use the raw string for judging
    _ = inst.guard.pop_buffer()
    
    # Judge
    if force_reply:
        decision = True
        sv.logger.info(f"[ChatSentinel] Urgent keyword detected. Skipping judge.")
    else:
        # Use memory for better context (Sender + ID + History) as requested
        # Increased context limit to 60 as per user request (was 20)
        context_for_judge = inst.memory.get_full_context_str(limit=60)
        
        try:
            decision = await judge.check(context_for_judge)
        except Exception as e:
            sv.logger.error(f"Judge Error: {e}")
            decision = False
    
    if decision:
        # sv.logger.info(f"[ChatSentinel] Judge said YES! Generating reply...")
        # Generate Reply
        # Use more context for generation, but maybe not 500 lines? 50 is fine for reply generation.
        # Responder usually only needs recent context.
        # But we must ensure the 'text' (latest msg) is included if it hasn't been added to memory yet?
        # Actually memory.add is called before this.
        
        full_context = inst.memory.get_full_context_str(limit=50)
        try:
            # Pass gid to responder to use aichat's config
            reply = await responder.generate(gid, full_context)
            if reply:
                # Add Bot's reply to memory so it knows what it said
                # Use "凯留" as sender name to be consistent with Persona
                inst.memory.add("凯留", "Bot", reply)
                await bot.send_group_msg(group_id=gid, message=reply)
                
                # Cooldown
                # Reduced to 60s per user request
                inst.guard.set_cooldown(60)
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
