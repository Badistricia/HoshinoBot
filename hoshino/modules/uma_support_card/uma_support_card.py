import os
import json
import asyncio
import difflib
from typing import Dict, List, Any

from hoshino import aiorequests, priv
from hoshino.typing import CQEvent
from hoshino.util import filt_message
from . import sv

# 数据存储路径
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
CARDS_DATA_PATH = os.path.join(DATA_PATH, 'cards_data.json')
EVENTS_DATA_PATH = os.path.join(DATA_PATH, 'events_data.json')

# 创建数据目录
os.makedirs(DATA_PATH, exist_ok=True)

# API链接
CARDS_API = "https://api.game.bilibili.com/game/player/tools/uma/support_cards"
CARD_DETAIL_API = "https://api.game.bilibili.com/game/player/tools/uma/support_card_detail"

# 全局变量
support_cards = []
cards_events = {}

def load_data():
    """加载本地数据"""
    global support_cards, cards_events
    
    # 加载卡片列表
    if os.path.exists(CARDS_DATA_PATH):
        with open(CARDS_DATA_PATH, 'r', encoding='utf-8') as f:
            support_cards = json.load(f)
    
    # 加载事件数据
    if os.path.exists(EVENTS_DATA_PATH):
        with open(EVENTS_DATA_PATH, 'r', encoding='utf-8') as f:
            cards_events = json.load(f)

def save_cards_data(data: List[Dict[str, Any]]):
    """保存协助卡数据"""
    with open(CARDS_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_events_data(data: Dict[str, Dict[str, List]]):
    """保存事件数据"""
    with open(EVENTS_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def fetch_support_cards():
    """获取所有协助卡数据"""
    try:
        resp = await aiorequests.get(CARDS_API)
        data = await resp.json()
        
        if data['code'] == 0 and 'data' in data and 'support_cards' in data['data']:
            return data['data']['support_cards']
        else:
            sv.logger.error(f"获取协助卡列表失败: {data}")
            return None
    except Exception as e:
        sv.logger.error(f"获取协助卡列表异常: {e}")
        return None

async def fetch_card_detail(card_id: int):
    """获取指定协助卡的详细信息"""
    try:
        params = {'support_card_ids': card_id}
        resp = await aiorequests.get(CARD_DETAIL_API, params=params)
        data = await resp.json()
        
        if data['code'] == 0 and 'data' in data and len(data['data']) > 0:
            return data['data'][0]
        else:
            sv.logger.error(f"获取协助卡详细信息失败: {data}")
            return None
    except Exception as e:
        sv.logger.error(f"获取协助卡详细信息异常: {e}")
        return None

async def update_data():
    """更新全部协助卡和事件数据"""
    global support_cards, cards_events
    
    # 获取所有协助卡
    card_list = await fetch_support_cards()
    if not card_list:
        return False
    
    support_cards = card_list
    save_cards_data(support_cards)
    
    # 获取每张卡的详细信息及事件
    all_events = {}
    for card in support_cards:
        card_id = card['card_id']
        card_name = card['name']
        
        # 获取卡片详细信息
        detail = await fetch_card_detail(card_id)
        if not detail:
            continue
        
        # 整理事件数据
        events = {}
        
        # 分支剧情
        if 'branch_story' in detail and detail['branch_story']:
            branch_events = []
            for story in detail['branch_story']:
                branch_events.append({
                    'story_id': story['story_id'],
                    'story_name': story['story_name'],
                    'options': [opt for opt in story['select_value_list']]
                })
            events['branch_story'] = branch_events
        
        # 普通剧情
        if 'no_branch_story' in detail and detail['no_branch_story']:
            no_branch_events = []
            for story in detail['no_branch_story']:
                no_branch_events.append({
                    'story_id': story['story_id'],
                    'story_name': story['story_name'],
                    'options': [opt for opt in story['select_value_list']]
                })
            events['no_branch_story'] = no_branch_events
        
        # 比赛后剧情
        if 'after_match_story' in detail and detail['after_match_story']:
            after_match_events = []
            for story in detail['after_match_story']:
                after_match_events.append({
                    'story_id': story['story_id'],
                    'story_name': story['story_name'],
                    'options': [opt for opt in story['select_value_list']]
                })
            events['after_match_story'] = after_match_events
        
        # 连续剧情
        if 'continuous_story' in detail and detail['continuous_story']:
            continuous_events = []
            for story in detail['continuous_story']:
                continuous_events.append({
                    'story_id': story['story_id'],
                    'story_name': story['story_name'],
                    'options': [opt for opt in story['select_value_list']]
                })
            events['continuous_story'] = continuous_events
        
        # 外出剧情
        if 'trip_story' in detail and detail['trip_story']:
            trip_events = []
            for story in detail['trip_story']:
                trip_events.append({
                    'story_id': story['story_id'],
                    'story_name': story['story_name'],
                    'options': [opt for opt in story['select_value_list']]
                })
            events['trip_story'] = trip_events
            
        # 将数据保存到全局变量
        all_events[card_id] = {
            'card_name': card_name,
            'events': events
        }
        
        # 每次请求之间添加延时，避免请求过于频繁
        await asyncio.sleep(0.5)
    
    # 更新全局数据
    cards_events = all_events
    save_events_data(all_events)
    
    return True

def find_events_by_name(event_name: str):
    """根据事件名模糊搜索事件"""
    if not event_name or not cards_events:
        return None
        
    found_events = []
    
    for card_id, card_data in cards_events.items():
        card_name = card_data['card_name']
        events = card_data['events']
        
        for event_type, event_list in events.items():
            for event in event_list:
                # 使用difflib进行模糊匹配
                similarity = difflib.SequenceMatcher(None, event_name, event['story_name']).ratio()
                
                # 如果相似度大于0.4（可根据需要调整阈值）
                if similarity > 0.4 or event_name in event['story_name']:
                    found_events.append({
                        'card_id': card_id,
                        'card_name': card_name,
                        'story_name': event['story_name'],
                        'event_type': event_type,
                        'options': event['options'],
                        'similarity': similarity
                    })
    
    # 按相似度排序，取最匹配的前3个
    found_events.sort(key=lambda x: x['similarity'], reverse=True)
    return found_events[:3] if found_events else None

def format_options(options):
    """格式化选项信息"""
    result = []
    for i, opt in enumerate(options):
        if 'option' in opt and 'gain_list' in opt:
            option_text = opt['option']
            gains = opt['gain_list']
            
            result.append(f"选项{i+1}「{option_text}」:")
            for gain in gains:
                result.append(f"  {gain}")
    
    return '\n'.join(result)

def format_event_info(event):
    """格式化事件信息"""
    event_type_names = {
        'branch_story': '分支剧情',
        'no_branch_story': '普通剧情',
        'after_match_story': '比赛后剧情',
        'continuous_story': '连续剧情',
        'trip_story': '外出剧情'
    }
    
    event_type = event_type_names.get(event['event_type'], '未知剧情')
    
    msg = [
        f"协助卡「{event['card_name']}」",
        f"事件类型：{event_type}",
        f"事件名称：{event['story_name']}",
        "选项效果："
    ]
    
    options_text = format_options(event['options'])
    msg.append(options_text)
    
    return '\n'.join(msg)

@sv.on_prefix(('uma事件', '马娘事件', '赛马娘事件'))
async def query_uma_event(bot, ev: CQEvent):
    # 提取查询关键词
    keyword = filt_message(ev.message.extract_plain_text().strip())
    if not keyword:
        await bot.send(ev, '请输入要查询的协助卡事件关键词')
        return
        
    # 如果数据为空，尝试加载本地数据
    global support_cards, cards_events
    if not support_cards or not cards_events:
        load_data()
        
    # 如果还是为空，说明需要初始化数据
    if not support_cards or not cards_events:
        await bot.send(ev, '正在初始化协助卡数据，这可能需要一些时间...')
        success = await update_data()
        if not success:
            await bot.send(ev, '初始化协助卡数据失败，请联系管理员')
            return
        await bot.send(ev, '协助卡数据初始化完成')
    
    # 查找事件
    events = find_events_by_name(keyword)
    if not events:
        await bot.send(ev, f'未能找到与「{keyword}」相关的协助卡事件，请尝试其他关键词')
        return
    
    # 发送查询结果
    for event in events:
        msg = format_event_info(event)
        await bot.send(ev, msg)

@sv.on_fullmatch(('更新uma数据', '更新赛马娘数据'))
async def update_uma_data(bot, ev: CQEvent):
    # 只允许管理员更新数据
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.send(ev, '只有管理员才能执行此操作')
        return
        
    await bot.send(ev, '开始更新赛马娘协助卡数据，这可能需要一些时间...')
    success = await update_data()
    if success:
        await bot.send(ev, '赛马娘协助卡数据更新完成')
    else:
        await bot.send(ev, '赛马娘协助卡数据更新失败')

# 初始化时尝试加载数据
load_data() 