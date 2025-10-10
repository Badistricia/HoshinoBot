from hoshino import Service, priv, config
from hoshino.typing import CQEvent
import httpx
import hashlib
import base64
import os
import json
import datetime
import random
from random import choice

sv = Service(
    name="今日老婆",  # 功能名
    visible=True,  # 可见性
    enable_on_default=True,  # 默认启用
    bundle="娱乐",  # 分组归类
    help_="发送【今日老婆】随机抓取群友作为老婆\n发送【换老婆】可以更换今天的老婆",  # 帮助说明

)

# 萌属性列表及其描述
MOEMOE_TRAITS = {
    "傲娇": "明明喜欢你却口是心非的",
    "病娇": "爱到疯狂的",
    "元气": "活力四射的",
    "天然呆": "天然迷糊的",
    "腹黑": "表面温柔内心黑暗的",
    "三无": "无表情无情感无欲望的",
    "中二": "有着奇妙幻想的",
    "女王": "高高在上命令你的",
    "大和抚子": "温柔贤惠的",
    "萝莉控": "喜欢小萝莉的",
    "御姐": "成熟魅力的",
    "伪娘": "可爱到让人怀疑性别的",
    "电波": "思维跳跃的",
    "宅女": "足不出户的",
    "吃货": "无时无刻不在想吃的",
    "工口": "略带色气的",
    "毒舌": "说话扎心的",
    "女仆": "温顺服侍你的",
    "学妹": "崇拜学长的",
    "双马尾": "留着可爱双马尾的"
}

def get_member_list(all_list):
    id_list = []
    for member_list in all_list:
        id_list.append(member_list['user_id'])
    return id_list

async def download_avatar(user_id: str) -> bytes:
    url = f"http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
    data = await download_url(url)
    if not data or hashlib.md5(data).hexdigest() == "acef72340ac0e914090bd35799f5594e":
        url = f"http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=100"
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

async def get_wife_info(member_info, qqid, moe_trait=""):  
    img = await download_avatar(qqid)
    base64_str = base64.b64encode(img).decode()
    avatar =  'base64://' + base64_str
    member_name = (member_info["card"] or member_info["nickname"])
    
    # 直接在老婆名称前加上萌属性
    if moe_trait:
        member_name = f"{moe_trait}的{member_name}"
    
    result = f'''\n你今天的群友老婆是:
[CQ:image,file={avatar}]
{member_name}({qqid})'''
    return result

def load_group_config(group_id: str) -> int:
    filename = os.path.join(os.path.dirname(__file__), 'config', f'{group_id}.json')
    try:
        with open(filename, encoding='utf8') as f:
            config = json.load(f)
            return config
    except:
        return None

def write_group_config(group_id: str, link_id:str, wife_id:str, date:str, config, change_count=0, moe_trait="") -> int:
    config_file = os.path.join(os.path.dirname(__file__), 'config', f'{group_id}.json')
    if config != None:    
        config[link_id] = [wife_id, date, change_count, moe_trait]
    else:
        config = {link_id:[wife_id, date, change_count, moe_trait]}
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)

@sv.on_fullmatch('今日老婆')
async def dailywife(bot, ev: CQEvent):
    groupid = ev.group_id
    user_id = ev.user_id
    bot_id = ev.self_id
    wife_id = None
    today = str(datetime.date.today())
    config = load_group_config(groupid)
    change_count = 0
    moe_trait = ""
    if config != None:
        if str(user_id) in list(config):
            if config[str(user_id)][1] == today:
                wife_id = config[str(user_id)][0]
                # 获取换老婆次数
                if len(config[str(user_id)]) > 2:
                    change_count = config[str(user_id)][2]
                # 获取萌属性
                if len(config[str(user_id)]) > 3:
                    moe_trait = config[str(user_id)][3]
            else:
                del config[str(user_id)]
    
    if wife_id is None:
        all_list = await bot.get_group_member_list(group_id=groupid)
        id_list = get_member_list(all_list)
        id_list.remove(bot_id)
        id_list.remove(user_id)
        if config != None:
            for record_id in list(config):
                if config[record_id][1] != today:
                    del config[record_id]
                else:
                    try:
                        id_list.remove(int(config[record_id][0]))
                    except:
                        del config[record_id]
        wife_id = choice(id_list)
        # 随机选择一个萌属性
        moe_trait = random.choice(list(MOEMOE_TRAITS.keys()))

    write_group_config(groupid, str(user_id), wife_id, today, config, change_count, moe_trait)
    member_info = await bot.get_group_member_info(group_id=groupid, user_id=wife_id)
    result = await get_wife_info(member_info, wife_id, moe_trait)   
    await bot.send(ev, result, at_sender=True)

@sv.on_fullmatch('换老婆')
async def change_wife(bot, ev: CQEvent):
    groupid = ev.group_id
    user_id = ev.user_id
    bot_id = ev.self_id
    today = str(datetime.date.today())
    config = load_group_config(groupid)
    
    # 检查用户是否已有老婆
    if config is None or str(user_id) not in list(config) or config[str(user_id)][1] != today:
        await bot.send(ev, "你今天还没有老婆，请先发送【今日老婆】获取一位吧~", at_sender=True)
        return
    
    # 检查换老婆次数限制
    change_count = 0
    if len(config[str(user_id)]) > 2:
        change_count = config[str(user_id)][2]
    
    if change_count >= 2:
        await bot.send(ev, "你今天已经换了两次老婆了，请珍惜当前的老婆吧~", at_sender=True)
        return
    
    # 获取新老婆
    all_list = await bot.get_group_member_list(group_id=groupid)
    id_list = get_member_list(all_list)
    
    # 安全移除机器人和用户自己
    if bot_id in id_list:
        id_list.remove(bot_id)
    if user_id in id_list:
        id_list.remove(user_id)
    
    # 移除当前老婆（如果在群内）
    current_wife = int(config[str(user_id)][0])
    if current_wife in id_list:
        id_list.remove(current_wife)
    
    for record_id in list(config):
        if record_id != str(user_id) and config[record_id][1] == today:
            try:
                id_list.remove(int(config[record_id][0]))
            except:
                pass
    
    # 如果没有可选的老婆了
    if not id_list:
        await bot.send(ev, "群里已经没有可选的老婆了，请珍惜当前的老婆吧~", at_sender=True)
        return
    
    # 随机选择新老婆
    new_wife_id = choice(id_list)
    change_count += 1
    
    # 随机选择一个萌属性
    moe_trait = random.choice(list(MOEMOE_TRAITS.keys()))
    
    # 更新配置
    write_group_config(groupid, str(user_id), new_wife_id, today, config, change_count, moe_trait)
    
    # 获取新老婆信息
    member_info = await bot.get_group_member_info(group_id=groupid, user_id=new_wife_id)
    result = await get_wife_info(member_info, new_wife_id, moe_trait)
    
    # 根据换老婆次数选择不同的提示词
    if change_count == 1:
        prefix = "今日老婆不合心意？你这个挑剔的家伙！新老婆是"
    else:  # change_count == 2
        prefix = "哇！又换老婆？你这个渣男！最后一个老婆是"
    
    await bot.send(ev, f"{prefix}{result}", at_sender=True)
    
