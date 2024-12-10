import base64
import io
import json
from io import BytesIO

import requests
from logging import getLogger
from bs4 import BeautifulSoup
import re
from .AOE4_dicts import RANK

from hoshino import Service, priv
from hoshino.modules.aoe_test.AOE4_queryUserStats import  queryUserStats
from .AOE4_queryCivWinRate import queryCivWinRate

sv = Service(
    'aoe_test',
    use_priv=priv.SUPERUSER,
    enable_on_default=False,
    manage_priv=priv.SUPERUSER,
    visible=True,
    help_='aoe_test\n查询aoe4玩家 + uid\n'
)

proxies = {"http": "", "https": ""}
logger = getLogger(__name__)
session = requests.session()

request_header = {
    'User-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36'}


@sv.on_prefix('查询玩家信息')
async def getUserStats(bot, ev):
    groupid = ev.group_id
    user_id = ev.user_id
    bot_id = ev.self_id
    cmd = ev.raw_message
    content = cmd.split()
    if (len(content) < 2):
        await bot.send(ev, "请输入正确的查询内容,后接玩家名称", at_sender=True)
        return
    # 把groupid userid content等用obj包裹然后用logger发送出去
    logger.info(f"get user stats: {groupid} {user_id} {bot_id} {content}")
    queryUserStats(content[1])
    # result = await checkPlayer(content)
    # logger.info(f"result: {result}")
    # await bot.send(ev, result, at_sender=True)


@sv.on_prefix('查询aoe胜率')
async def getCivWinRate(bot, ev):
    groupid = ev.group_id
    user_id = ev.user_id
    bot_id = ev.self_id
    logger.info(f"get user stats: {groupid} {user_id} {bot_id}")
    user_input = ev.raw_message
    user_context = user_input.split();
    if (len(user_context) < 2):
        await bot.send(ev, "请输入正确的查询内容,后接段位", at_sender=True)
        return
    # 把groupid userid content等用obj包裹然后用logger发送出去
    logger.info(f"get user stats: {groupid} {user_id} {bot_id} {user_context}")
    # 判断发送的是根据elo分数来筛选还是段位来筛选 段位有青铜 白银 黄金 白金 钻石 征服者
    print(RANK.get(user_context[1]))
    elp_section_str = "=>=" + RANK.get(user_context[1])
    logger.info(f"elp_section_str: {elp_section_str}")



    fig = await queryCivWinRate(elp_section_str)

    # 将图像转换为Base64字符串
    buffer = BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    image_base64 = 'base64://' + base64.b64encode(buffer.read()).decode()

    await bot.send_group_msg(group_id=groupid, message=f'[CQ:image,file={image_base64}]')
    logger.info("done")
    # logger.info(f"result: {result}")
    # await bot.send(ev, result, at_sender=True)

