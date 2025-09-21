import hoshino, random, os, re, filetype
from hoshino import Service, R, priv, aiorequests
from hoshino.config import RES_DIR
from hoshino.typing import CQEvent
from hoshino.util import DailyNumberLimiter
from .config import get_food_list

sv_help = '''
[今天吃什么] 看看今天吃啥
[早上吃什么] 推荐早餐
[中午吃什么] 推荐午餐
[晚上吃什么] 推荐晚餐
[吃小吃] 推荐小吃
'''.strip()

sv = Service(
    name = '今天吃什么',  #功能名
    use_priv = priv.NORMAL, #使用权限   
    manage_priv = priv.ADMIN, #管理权限
    visible = True, #可见性
    enable_on_default = True, #默认启用
    bundle = '娱乐', #分组归类
    help_ = sv_help #帮助说明
    )

_lmt = DailyNumberLimiter(5)
imgpath = os.path.join(os.path.expanduser(RES_DIR), 'img', 'foods')

def get_food_type_and_message(time_str):
    """根据时间字符串确定食物类型和回复消息"""
    if time_str in ['早上', '早餐', '早饭']:
        return 'breakfast', time_str + '去吃'
    elif time_str in ['中午', '午餐', '午饭']:
        return 'lunch', time_str + '去吃'
    elif time_str in ['晚上', '晚餐', '晚饭', '夜宵']:
        return 'dinner', time_str + '去吃'
    else:
        # 默认随机选择一种类型
        food_types = ['breakfast', 'lunch', 'dinner', 'snack']
        return random.choice(food_types), time_str + '去吃'

@sv.on_rex(r'^(今天|[早中午晚][上饭餐午]|夜宵)吃(什么|啥|点啥)')
async def what_to_eat(bot, ev: CQEvent):
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.finish(ev, '你今天吃的已经够多的了！', at_sender=True)
    
    match = ev['match']
    time = match.group(1).strip()
    
    # 根据时间确定食物类型
    food_type, message_prefix = get_food_type_and_message(time)
    
    # 从配置文件获取对应类型的食物列表
    food_list = get_food_list(food_type)
    
    if not food_list:
        # 如果配置文件中没有对应类型的食物，则从文件夹中随机选择
        if os.path.exists(imgpath) and os.listdir(imgpath):
            food = random.choice(os.listdir(imgpath))
        else:
            await bot.send(ev, '暂时没有美食图片哦~', at_sender=True)
            return
    else:
        # 从配置的食物列表中随机选择
        food = random.choice(food_list)
    
    name = food.split('.')[0]
    to_eat = message_prefix + name + '吧~\n'
    
    try:
        foodimg = R.img('foods/' + food).cqcode
        to_eat += str(foodimg)
    except Exception as e:
        hoshino.logger.error('读取食物图片时发生错误' + str(type(e)))
        to_eat = message_prefix + name + '吧~\n[图片加载失败]'
    
    await bot.send(ev, to_eat, at_sender=True)
    _lmt.increase(uid)

@sv.on_rex(r'^(吃小吃|小吃|来点小吃)')
async def eat_snack(bot, ev: CQEvent):
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.finish(ev, '你今天吃的已经够多的了！', at_sender=True)
    
    # 获取小吃列表
    snack_list = get_food_list('snack')
    
    if not snack_list:
        await bot.send(ev, '暂时没有小吃推荐哦~', at_sender=True)
        return
    
    # 随机选择一个小吃
    food = random.choice(snack_list)
    name = food.split('.')[0]
    to_eat = '来点' + name + '吧~\n'
    
    try:
        foodimg = R.img('foods/' + food).cqcode
        to_eat += str(foodimg)
    except Exception as e:
        hoshino.logger.error('读取食物图片时发生错误' + str(type(e)))
        to_eat = '来点' + name + '吧~\n[图片加载失败]'
    
    await bot.send(ev, to_eat, at_sender=True)
    _lmt.increase(uid)

async def download_async(url, name):
    resp= await aiorequests.get(url, stream=True)
    if resp.status_code == 404:
        raise ValueError('文件不存在')
    content = await resp.content
    try:
        extension = filetype.guess_mime(content).split('/')[1]
    except:
        raise ValueError('不是有效文件类型')
    abs_path = os.path.join(imgpath, name + '.' + extension)
    with open(abs_path, 'wb') as f:
        f.write(content)

@sv.on_prefix(('添菜','添加菜品'))
@sv.on_suffix(('添菜','添加菜品'))
async def add_food(bot,ev:CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    food = ev.message.extract_plain_text().strip()
    ret = re.search(r"\[CQ:image,file=(.*)?,url=(.*)\]", str(ev.message))
    if not ret:
        await bot.send(ev,'请附带美食图片~')
        return
    url = ret.group(2)
    await download_async(url, food)
    await bot.send(ev,'食谱已增加~')
