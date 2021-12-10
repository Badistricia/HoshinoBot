from hoshino import Service, R
from hoshino.util import FreqLimiter
from hoshino.typing import CQEvent, HoshinoBot

sv = Service('anti-lex', help_='买药提醒')
lmt = FreqLimiter(3600)


@sv.scheduled_job('cron', hour='*/8')
async def hour_call():
    pic = R.img("lexbiss.jpg").cqcode
    msg = f'{pic}\n共创和谐环境人人有责 拿出行动天天打卡🍒Σ打卡帖bbs.nga.cn/read.php?tid=29790467'
    await sv.broadcast(msg, 'anti-lex')


@sv.on_keyword('蕾皇', 'lex')
async def keyword_anti(bot: HoshinoBot, ev: CQEvent):
    pic = R.img("lexbiss.jpg").cqcode
    if lmt.check(ev.group_id):
        await bot.send(ev, pic)
        lmt.start_cd(ev.group_id)
