import os

import nonebot
import requests
from nonebot import on_command, CommandSession

import hoshino
from hoshino import Service, HoshinoBot, R
from hoshino.config.picfinder import proxies
from hoshino.typing import CQEvent
from hoshino.util import filt_message

sv = Service('test', help_='''
test desc
'''.strip())



@sv.on_prefix('test')
async def test(bot: HoshinoBot, ev: CQEvent):
    # await bot.send(ev, "test send", at_sender=False)
    # print(ev)
    url = "https://www.twitter.com/"
    r = requests.get(url, proxies=proxies)
    print(r)
    # print(bot)
    print(hoshino.config.RES_DIR)


aliesSet = ('testc', 'commandtest', 'testCommand')


# @on_command("testCommand", aliases=aliesSet)
# async def test_command(session: CommandSession):
#     # await bot.send(ev, "testC send", at_sender=True)
#     print(session)
#     print(session.ctx)
#     print(session.current_arg_text)
#     await session.send("你干嘛", at_sender=True, ensure_private=True)
#     print(session.event)
#     print(session.bot)
#     print(session.cmd)
