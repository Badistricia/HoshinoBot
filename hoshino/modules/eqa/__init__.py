# -*- coding: UTF-8 -*-
"""
作者艾琳有栖
版本 0.1.0 - MySQL重构版
基于 nonebot 问答
"""
import re
import random
import nonebot
from . import util
from . import database

from hoshino import Service, priv

sv_help = '''
- [有人/大家说AA回答BB] 对所有人生效
- [我说AA回答BB] 仅仅对个人生效
- [不要回答AA] 删除某问题下的回答(优先度:自己设置的>最后设置的)
- [问答] 查看自己的回答,@别人可以看别人的
- [全部问答] 查看本群设置的回答
- 只有管理可以删别人设置的哦~~~
※进阶用法：
发送[epa进阶用法]可查看
'''.strip()
sv_help1 = '''
- [有人/大家说AA回答=BB] 
- [我说AA回答=BB] 
对于bot而言你说AA就是在说BB
示例：
我说1回答=xcwkkp 
或者
我说1回答=echo CQ码
CQ码部分
- [CQ码帮助]
'''.strip()

sv = Service(
    name='调教',
    use_priv=priv.NORMAL,
    manage_priv=priv.ADMIN,
    visible=True,
    enable_on_default=True,
    bundle='通用',
    help_=sv_help,
    aliases=('eqa', '问答')
)


@sv.on_fullmatch(["epa进阶用法"])
async def bangzhu(bot, ev):
    await bot.send(ev, sv_help1)


config = util.get_config()
_bot = nonebot.get_bot()

admins = config['admins']
admins = set((admins if isinstance(admins, list) else [admins]) + _bot.config.SUPERUSERS)

# 初始化数据库
db = None


@nonebot.on_startup
async def init_db():
    """启动时初始化数据库"""
    global db
    db_config = config.get('database', {})
    db = await database.init_database(
        host=db_config.get('host', 'localhost'),
        port=db_config.get('port', 3306),
        user=db_config.get('user', 'root'),
        password=db_config.get('password', ''),
        database=db_config.get('database', 'hoshinoBotDB')
    )


@sv.on_message('group')
async def eqa_main(*params):
    bot, ctx = (_bot, params[0]) if len(params) == 1 else params

    msg = str(ctx['message']).strip()

    # 处理回答所有人的问题
    keyword = util.get_msg_keyword(config['comm']['answer_all'], msg, True)
    if keyword:
        result = await ask(ctx, keyword, False)
        if result:
            return await bot.send(ctx, result)

    # 处理回答自己的问题
    keyword = util.get_msg_keyword(config['comm']['answer_me'], msg, True)
    if keyword:
        result = await ask(ctx, keyword, True)
        if result:
            return await bot.send(ctx, result)

    # 回复消息
    ans = await answer(ctx)
    if isinstance(ans, list):
        return await bot.send(ctx, ans)

    # 显示全部设置的问题
    show_target = util.get_msg_keyword(config['comm']['show_question_list'], msg, True)
    if isinstance(show_target, str):
        return await bot.send(ctx, await show_question(ctx, show_target, True))

    # 显示设置的问题
    show_target = util.get_msg_keyword(config['comm']['show_question'], msg, True)
    if isinstance(show_target, str):
        return await bot.send(ctx, await show_question(ctx, show_target))

    # 删除设置的问题
    del_target = util.get_msg_keyword(config['comm']['answer_delete'], msg, True)
    if del_target:
        return await bot.send(ctx, await del_question(ctx, del_target))

    # 清空设置的问题
    del_all = util.get_msg_keyword(config['comm']['answer_delete_all'], msg, True)
    if del_all:
        return await bot.send(ctx, await del_question(ctx, del_all, True))


async def ask(ctx, keyword, is_me):
    """设置问题的函数"""
    is_super_admin = ctx['user_id'] in admins
    is_admin = util.is_group_admin(ctx) or is_super_admin

    if config['rule']['only_admin_answer_all'] and not is_me and not is_admin:
        return '回答所有人的只能管理设置啦'

    question_handler = config['comm']['answer_me'] if is_me else config['comm']['answer_all']
    answer_handler = config['comm']['answer_handler']
    qa_msg = util.get_msg_keyword(answer_handler, keyword)
    if not qa_msg:
        return False
    ans, qus = qa_msg
    qus = f'{qus}'.strip()
    if not str(qus).strip():
        return '问题呢? 问题呢??'
    if not str(ans).strip():
        return '回答呢? 回答呢??'

    # 问题与回答的分割
    ans_start = util.find_ms_str_index(ctx['message'], answer_handler)

    if re.search(r'\[CQ:image,', qus):
        qus = util.get_message_str(ctx['message'][:ans_start])
        qus = util.get_msg_keyword(question_handler, qus, True).strip()

    message = []
    _once = False
    for ms in ctx['message'][ans_start:]:
        if ms['type'] == 'text':
            reg = util.get_msg_keyword(answer_handler, ms['data']['text'])
            if reg and not _once:
                _once = True
                ms = MessageSegment.text(reg[0])
        if ms['type'] == 'image':
            ms = util.ms_handler_image(ms, config['rule']['use_cq_code_image_url'], config['cache_dir'],
                                       b64=config['image_base64'])
            if not ms:
                return '图片缓存失败了啦！'
        message.append(ms)

    # 使用MySQL存储
    db = await ensure_db()
    question_id = await db.add_question(
        question=qus,
        group_id=ctx['group_id'],
        is_global=is_super_admin and not is_me
    )
    
    await db.add_answer(
        question_id=question_id,
        user_id=ctx['user_id'],
        group_id=ctx['group_id'],
        is_me=is_me,
        message=message
    )
    
    return '我学会啦 来问问我吧！'


async def ensure_db():
    """确保数据库已初始化"""
    global db
    if db is None:
        db_config = config.get('database', {})
        db = await database.init_database(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 3306),
            user=db_config.get('user', 'root'),
            password=db_config.get('password', ''),
            database=db_config.get('database', 'hoshinoBotDB')
        )
    return db


async def answer(ctx):
    """回复的函数"""
    msg = util.get_message_str(ctx['message']).strip()
    
    db = await ensure_db()
    is_super_admin = ctx['user_id'] in admins
    
    ans = await db.get_answer_for_user(
        question=msg,
        group_id=ctx['group_id'],
        user_id=ctx['user_id'],
        is_super_admin=is_super_admin and config['rule']['super_admin_is_all_group'],
        priority_self=config['rule']['priority_self_answer']
    )
    
    if not ans:
        return False

    # 判断是否是自己设置的回复
    if ans['is_me'] and ans['user_id'] != ctx['user_id']:
        return False

    msg_content = ans['answer_content']
    
    # 处理命令前缀
    if len(msg_content) == 1:
        _msg = msg_content[0]
        if _msg['type'] == 'text' and _msg['data']['text'][:1] == config['str']['cmd_head_str']:
            ctx['raw_message'] = _msg['data']['text'][1:]
            ctx['message'] = Message(ctx['raw_message'])
            _bot.on_message(ctx)
            return False

    # 如果使用了base64 那么需要把信息里的图片转换一下
    if config['image_base64']:
        msg_content = util.message_image2base64(msg_content)

    return msg_content


async def show_question(ctx, target, show_all=False):
    """显示问题的函数"""
    print_all_split = config['str']['print_all_split'] or " | "

    is_super_admin = ctx['user_id'] in admins
    is_admin = util.is_group_admin(ctx) or is_super_admin
    group_id = ctx['group_id']

    if not show_all:
        # 如果只显示个人
        target = list(int(i) for i in re.findall(r'\[CQ:at,qq=(\d+)]', target.strip()))
        is_at = bool(target)

        # 如果关了群友查询别人的选项
        if not config['rule']['member_can_show_other'] and target and not is_admin:
            return '不能看别人设置的问题啦'

        # 如果跟着@人对象 就显示@人的  没有就显示自己的
        target = target if is_at else [ctx['user_id']]
    else:
        # 显示全部
        target = [ctx['user_id']]
        is_at = False

    db = await ensure_db()
    msg = ''
    
    for qq in target:
        head = ''
        
        if is_at:
            name = await util.get_group_member_name(group_id, qq)
            head = f'{name} :\n'

        # 获取问答列表
        answers = await db.get_question_answers_by_user(
            group_id=group_id,
            user_id=qq if not show_all else None,
            is_super_admin=is_super_admin
        )
        
        if not answers:
            msg += f"{head}还没有设置过问题呢\n"
            continue

        # 分类显示
        all_questions = []
        personal_questions = []
        
        for ans in answers:
            q_text = ans['question']
            if ans['is_me']:
                personal_questions.append(q_text)
            else:
                all_questions.append(q_text)
        
        # 去重
        all_questions = list(set(all_questions))
        personal_questions = list(set(personal_questions))
        
        # 转换CQ码
        all_questions = await util.cq_msg2str(all_questions, group_id=group_id)
        personal_questions = await util.cq_msg2str(personal_questions, group_id=group_id)

        if show_all:
            msg_context = f'全体问答:\n{print_all_split.join(all_questions)}' if all_questions else '无'
            priority_msg = f"\n个人问答:\n{print_all_split.join(personal_questions)}" if personal_questions else ''
            msg = f"{msg}{head}{msg_context}{priority_msg}\n"
        else:
            all_q = all_questions + personal_questions
            msg = f"{msg}{head}{chr(10).join(all_q)}\n"

    return msg


async def del_question(ctx, target, clear=False):
    """删除问题的函数"""
    target = util.get_message_str(target).strip()
    
    db = await ensure_db()
    is_super_admin = ctx['user_id'] in admins
    is_group_admin = util.is_group_admin(ctx) if config['rule']['only_admin_can_delete'] else True
    is_admin = is_group_admin or is_super_admin

    # 如果直接清空
    if clear:
        if is_super_admin:
            # 获取问题ID
            question = await db.get_question(target, ctx['group_id'])
            if question:
                await db.delete_question(question['id'])
                return '清空成功~'
        return '木有权限啦~~'

    # 查找要删除的回答
    answer_id = await db.find_answer_to_delete(
        question=target,
        group_id=ctx['group_id'],
        user_id=ctx['user_id'],
        is_admin=is_admin,
        is_super_admin=is_super_admin,
        can_delete_super=config['rule']['can_delete_super_admin_qa']
    )
    
    if answer_id:
        await db.delete_answer(answer_id)
        return '删除成功啦'
    
    return '删除失败 可能木有权限'
