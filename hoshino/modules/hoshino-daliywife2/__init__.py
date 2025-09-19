import random
import datetime
from typing import Set, Dict, Any, Union, List

from hoshino import Service, priv
from hoshino.typing import CQEvent
from aiocqhttp.exceptions import ActionFailed

from .config import Config
from .record import get_group_record, save_group_record, construct_waifu_msg, clear_group_record, \
    construct_change_waifu_msg
    
waifu_config: Config = Config()

sv_help = '''
随机抓取群友作为老婆！
[今日老婆]  随机抽取群友作为老婆。当天已经抽取过回复相同老婆
[换老婆]    重新抽取老婆
※群管理员可用※
[(刷新/重置)今日老婆]  清空今日本群老婆数据
[(开启/关闭)换老婆]  开启/关闭本群换老婆功能
[设置换老婆次数 (数字)]  设置本群换老婆最大次数
'''.strip()

sv = Service(
    name="今日老婆",  # 功能名
    visible=True,  # 可见性
    enable_on_default=True,  # 默认启用
    bundle="娱乐",  # 分组归类
    help_=sv_help,  # 帮助说明
)

plugin_aliases: List[str] = waifu_config.today_waifu_aliases
ban_id: Set[int] = waifu_config.today_waifu_ban_id_list
default_allow_change_waifu: bool = waifu_config.today_waifu_default_change_waifu
default_limit_times: int = waifu_config.today_waifu_default_limit_times


@sv.on_fullmatch('开启换老婆','关闭换老婆')
async def today_waifu_set_allow_change(bot, event: CQEvent):
    # 判断权限，只有用户为群管理员或为bot设置的超级管理员才能使用
    u_priv = priv.get_user_priv(event)
    if u_priv < sv.manage_priv:
        return
    gid = str(event.group_id)
    group_record: Dict[str, Union[bool, Dict[str, Dict[str, int]]]] = get_group_record(gid)  # 获取本群记录字典
    val: str = event.raw_message
    if val == '开启换老婆':
        group_record['allow_change_waifu'] = True
    elif val == '关闭换老婆':
        group_record['allow_change_waifu'] = False
    save_group_record(gid, group_record)
    await bot.send(event, f'本群设置为{val}')


@sv.on_prefix('设置换老婆次数')
async def today_waifu_set_limit_times(bot, event: CQEvent):
    # 判断权限，只有用户为群管理员或为bot设置的超级管理员才能使用
    u_priv = priv.get_user_priv(event)
    if u_priv < sv.manage_priv:
        return
    limit_times: str = event.message.extract_plain_text().strip()
    try:
        limit_times_num = int(limit_times)
    except ValueError:
        await bot.send(event, '换老婆次数应为整数')
        return
    gid = str(event.group_id)
    group_record: Dict[str, Union[int, Dict[str, Dict[str, int]]]] = get_group_record(gid)  # 获取本群记录字典
    group_record['limit_times'] = limit_times_num
    save_group_record(gid, group_record)
    await bot.send(event, f'已将本群换老婆次数设置为{limit_times_num}次')


@sv.on_fullmatch('换老婆')
async def today_waifu_change(bot, event: CQEvent):
    gid = str(event.group_id)
    uid = str(event.user_id)
    today = str(datetime.date.today())
    group_record: Dict[str, Union[int, bool, Dict[str, Dict[str, int]]]] = get_group_record(gid)  # 获取本群记录字典
    limit_times: int = group_record.setdefault('limit_times', default_limit_times)
    allow_change_waifu: bool = group_record.setdefault('allow_change_waifu', default_allow_change_waifu)
    if today not in group_record.keys() or uid not in group_record[today].keys():
        await bot.send(event, '换老婆前请先娶个老婆哦，渣男→_→', at_sender=True)
        return
    if not allow_change_waifu:
        await bot.send(event, '请专一的对待自己的老婆哦，不许花心！', at_sender=True)
        return
    group_today_record: Dict[str, Dict[str, int]] = group_record[today]  # 获取本群今日字典
    old_waifu_id: int = group_today_record[uid].get('waifu_id', 1234567)
    old_times: int = group_today_record[uid].setdefault('times', 0)
    if old_times >= limit_times or old_waifu_id == int(event.self_id):
        new_waifu_id = -1
        old_times = limit_times
    else:
        all_member: list = await bot.get_group_member_list(group_id=gid)
        id_set: Set[int] = set(i['user_id'] for i in all_member) - set(
            i['waifu_id'] for i in group_today_record.values()) - ban_id
        id_set.discard(int(uid))
        if id_set:
            new_waifu_id: int = random.choice(list(id_set))
        else:
            # 如果剩余群员列表为空，默认机器人作为老婆
            new_waifu_id: int = int(event.self_id)
    group_today_record[uid] = {
        'waifu_id': new_waifu_id,
        'times': old_times + 1
    }
    save_group_record(gid, group_record)
    try:
        member_info = await bot.get_group_member_info(group_id=gid, user_id=new_waifu_id)
    except ActionFailed:
        # 群员已经退群情况
        member_info = {}
    message = await construct_change_waifu_msg(member_info, new_waifu_id, int(event.self_id), old_times, limit_times)
    await bot.send(event, message, at_sender=True)


@sv.on_fullmatch('今日老婆')
async def today_waifu(bot, event: CQEvent):
    gid = str(event.group_id)
    uid = str(event.user_id)
    today = str(datetime.date.today())
    group_record: Dict[str, Union[int, bool, Dict[str, Dict[str, int]]]] = get_group_record(gid)  # 获取本群记录字典
    limit_times: int = group_record.setdefault('limit_times', default_limit_times)
    allow_change_waifu: bool = group_record.setdefault('allow_change_waifu', default_allow_change_waifu)
    save = False  # 保存标记，是否将记录写入到本地文件
    is_first: bool  # 是否已经存在老婆标记
    waifu_id: int  # 老婆id
    if today not in group_record.keys():
        # 如果不存在今天的记录，清空本群记录字典，并添加今天的记录，保存标记置为真
        group_record.clear()
        group_record['limit_times'] = limit_times
        group_record['allow_change_waifu'] = allow_change_waifu
        group_record[today] = {}
        save = True
    group_today_record: Dict[str, Dict[str, int]] = group_record[today]  # 获取本群今日字典
    if uid in group_today_record.keys():
        # 如果用户在今天已经有老婆记录，记录已经存在老婆 同时 记录老婆id
        waifu_id: int = group_today_record[uid].get('waifu_id', 1234567)
        is_first = False
    else:
        # 如果用户在今天无老婆记录，随机从群友中抓取一位作为老婆，同时保证别人的老婆不会被抓（NTR禁止）
        all_member: list = await bot.get_group_member_list(group_id=gid)
        id_set: Set[int] = set(i['user_id'] for i in all_member) - set(
            i['waifu_id'] for i in group_today_record.values()) - ban_id
        id_set.discard(int(uid))
        if id_set:
            waifu_id: int = random.choice(list(id_set))
        else:
            # 如果剩余群员列表为空，默认机器人作为老婆
            waifu_id: int = int(event.self_id)
        group_today_record[uid] = {
            'waifu_id': waifu_id,
            'times': 0,
        }
        save = True
        is_first = True
    if save:
        save_group_record(gid, group_record)
    try:
        member_info = await bot.get_group_member_info(group_id=gid, user_id=waifu_id)
    except ActionFailed:
        # 群员已经退群情况
        member_info = {}
    message = await construct_waifu_msg(member_info, waifu_id, int(event.self_id), is_first)
    await bot.send(event, message, at_sender=True)


@sv.on_fullmatch('刷新今日老婆','重置今日老婆')
async def today_waifu_refresh(bot, event: CQEvent):
    # 判断权限，只有用户为群管理员或为bot设置的超级管理员才能使用
    u_priv = priv.get_user_priv(event)
    if u_priv < sv.manage_priv:
        return
    clear_group_record(str(event.group_id))
    await bot.send(event, '今日老婆已刷新！')