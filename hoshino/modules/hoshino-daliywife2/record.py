import json
import hashlib
from typing import Union, Any
from pathlib import Path
import base64

import httpx
from nonebot import on_startup

from .config import Config

waifu_config: Config = Config()
record_dir: Path = waifu_config.today_waifu_record_dir

TodayWaifuRecord = {}


@on_startup
async def today_waifu_init() -> None:
    """
    在驱动加载时初始化记录(Record)
    将 ./record 文件夹内json文件读入内存
    """
    if not record_dir.exists():
        record_dir.mkdir(parents=True, exist_ok=True)
    for file in record_dir.glob('*.json'):
        TodayWaifuRecord[file.stem] = load_json(file)


def save_json(data, json_file_path: Union[str, Path]) -> None:
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, sort_keys=False, indent=2)


def load_json(json_file_path: Union[str, Path]) -> Any:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def clear_group_record(gid: str) -> None:
    """
    清空群号为 gid 在内存中与本地的记录(record)
    """
    if gid not in TodayWaifuRecord:
        return
    TodayWaifuRecord[gid].clear()
    save_group_record(gid, TodayWaifuRecord[gid])


def get_group_record(gid: str) -> dict:
    """
    获取群组记录字典对象
    优先从内存中获取，若内存中不存在则尝试从记录文件夹查找本地文件，若本地文件不存在则新建空文件 并返回相应对象
    """
    if gid in TodayWaifuRecord:
        return TodayWaifuRecord[gid]
    filename = record_dir / f'{gid}.json'
    if not filename.exists():
        save_json({}, filename)
    record = load_json(filename)
    TodayWaifuRecord[gid] = record
    return record


def save_group_record(gid: str, record: dict) -> None:
    """
    保存群组记录到本地json文件
    """
    record_file_path = record_dir / f'{gid}.json'
    save_json(record, record_file_path)


async def construct_change_waifu_msg(member_info: dict, new_waifu_id: int, bot_id: int, times: int,
                                     limit_times: int):
    if new_waifu_id == -1:
        return f'\n渣男！你今天没老婆了！'
    member_name = (member_info.get("card") or member_info.get("nickname") or new_waifu_id)
    img = await download_avatar(str(new_waifu_id))
    base64_str = base64.b64encode(img).decode()
    avatar =  'base64://' + base64_str
    if new_waifu_id == bot_id:
        result = f'''\n你今天的群友老婆是我哦~
如果你这个渣男敢抛弃我的话，你今天就没老婆了哦
[CQ:image,file={avatar}]'''
        return result
    msg = ''
    if times == limit_times - 1:
        msg = f'\n渣男，再换你今天就没老婆了！'
    result = msg + f'''\n你今天的群友老婆是：[CQ:image,file={avatar}]{member_name}({new_waifu_id})'''
    return result


async def construct_waifu_msg(member_info: dict, waifu_id: int, bot_id: int, is_first: bool):
    """
    构造发送信息
    """
    if waifu_id == -1:
        return f'\n渣男，你今天没老婆了！'
    member_name = (member_info.get("card") or member_info.get("nickname") or waifu_id)
    img = await download_avatar(str(waifu_id))
    base64_str = base64.b64encode(img).decode()
    avatar =  'base64://' + base64_str
    if waifu_id == bot_id:
        if is_first:
            result = f'''\n你今天的群友老婆是我哦~[CQ:image,file={avatar}]'''
            return result
        else:
            result = f'''\n你今天已经有老婆了，是我哦，不可以再有别人了呢~[CQ:image,file={avatar}]'''
            return result

    if is_first:
        result =  f'''\n你今天的群友老婆是：[CQ:image,file={avatar}]{member_name}({waifu_id})'''
        return result
    return f'''\n你今天已经有老婆了，要好好对待她哦~[CQ:image,file={avatar}]{member_name}({waifu_id})'''

async def download_avatar(uid: str) -> bytes:
    """
    根据 qq号 获取头像
    """
    url = f"http://q1.qlogo.cn/g?b=qq&nk={uid}&s=640"
    data = await download_url(url)
    if not data or hashlib.md5(data).hexdigest() == "acef72340ac0e914090bd35799f5594e":
        url = f"http://q1.qlogo.cn/g?b=qq&nk={uid}&s=100"
        data = await download_url(url)
    return data


async def download_url(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        for i in range(3):
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                return resp.content
            except Exception as e:
                print(f"Error downloading {url}, retry {i}/3: {str(e)}")