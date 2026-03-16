# -*- coding: UTF-8 -*-
"""
作者艾琳有栖
版本 0.1.0 - MySQL重构版
基于 nonebot 问答
"""
import re
import random
import nonebot
from nonebot.message import Message, MessageSegment
from . import util
from . import database

import hoshino
from hoshino import Service, priv, logger

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
    name='eqa',
    use_priv=priv.NORMAL,
    manage_priv=priv.ADMIN,
    visible=True,
    enable_on_default=True,
    bundle='通用',
    help_=sv_help
)


@sv.on_fullmatch(["epa进阶用法"])
async def bangzhu(bot, ev):
    await bot.send(ev, sv_help1)


config = util.get_config()

admins = config['admins']
_superusers = hoshino.config.SUPERUSERS if hasattr(hoshino, 'config') else []
admins = set((admins if isinstance(admins, list) else [admins]) + list(_superusers))

# 初始化数据库
db = None


# 数据库在首次使用时由 ensure_db() 延迟初始化


async def ensure_db():
    """确保数据库已初始化，失败时记录详细错误"""
    global db
    if db is None:
        logger.info("[eqa] DB未初始化，尝试建立连接...")
        db_config = config.get('database', {})
        logger.info(f"[eqa] DB配置: host={db_config.get('host','localhost')}, "
                    f"port={db_config.get('port', 3306)}, "
                    f"user={db_config.get('user','root')}, "
                    f"database={db_config.get('database','hoshinoBotDB')}")
        try:
            db = await database.init_database(
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 3306),
                user=db_config.get('user', 'root'),
                password=db_config.get('password', ''),
                database=db_config.get('database', 'hoshinoBotDB')
            )
            logger.info("[eqa] 数据库连接初始化成功！")
        except Exception as e:
            logger.error(f"[eqa] 数据库连接失败: {type(e).__name__}: {e}")
            db = None
            raise
    return db


@sv.on_message('group')
async def eqa_main(*params):
    _bot = nonebot.get_bot()
    bot, ctx = (_bot, params[0]) if len(params) == 1 else params

    msg = str(ctx['message']).strip()
    group_id = ctx.get('group_id', '?')
    user_id = ctx.get('user_id', '?')
    logger.debug(f"[eqa] 收到消息 group={group_id} user={user_id} msg={msg!r}")

    # 处理设置所有人问题
    keyword = util.get_msg_keyword(config['comm']['answer_all'], msg, True)
    logger.debug(f"[eqa] answer_all 关键词={config['comm']['answer_all']!r} 匹配结果={keyword!r}")
    if keyword:
        logger.info(f"[eqa] 触发 answer_all，keyword={keyword!r}")
        try:
            result = await ask(ctx, keyword, False)
        except Exception as e:
            logger.error(f"[eqa] ask(all) 异常: {e}", exc_info=True)
            return
        if result:
            return await bot.send(ctx, result)

    # 处理设置个人问题
    keyword = util.get_msg_keyword(config['comm']['answer_me'], msg, True)
    logger.debug(f"[eqa] answer_me 关键词={config['comm']['answer_me']!r} 匹配结果={keyword!r}")
    if keyword:
        logger.info(f"[eqa] 触发 answer_me，keyword={keyword!r}")
        try:
            result = await ask(ctx, keyword, True)
        except Exception as e:
            logger.error(f"[eqa] ask(me) 异常: {e}", exc_info=True)
            return
        if result:
            return await bot.send(ctx, result)

    # 回复消息（匹配问答）
    try:
        ans = await answer(ctx)
    except Exception as e:
        logger.error(f"[eqa] answer() 异常: {e}", exc_info=True)
        return
    if isinstance(ans, list):
        return await bot.send(ctx, ans)

    # 显示全部问题
    show_target = util.get_msg_keyword(config['comm']['show_question_list'], msg, True)
    logger.debug(f"[eqa] show_question_list 匹配={show_target!r}")
    if isinstance(show_target, str):
        return await bot.send(ctx, await show_question(ctx, show_target, True))

    # 显示个人问题
    show_target = util.get_msg_keyword(config['comm']['show_question'], msg, True)
    logger.debug(f"[eqa] show_question 匹配={show_target!r}")
    if isinstance(show_target, str):
        return await bot.send(ctx, await show_question(ctx, show_target))

    # 删除问题
    del_target = util.get_msg_keyword(config['comm']['answer_delete'], msg, True)
    logger.debug(f"[eqa] answer_delete 匹配={del_target!r}")
    if del_target:
        return await bot.send(ctx, await del_question(ctx, del_target))

    # 清空问题
    del_all = util.get_msg_keyword(config['comm']['answer_delete_all'], msg, True)
    logger.debug(f"[eqa] answer_delete_all 匹配={del_all!r}")
    if del_all:
        return await bot.send(ctx, await del_question(ctx, del_all, True))


async def ask(ctx, keyword, is_me):
    """设置问题的函数"""
    is_super_admin = ctx['user_id'] in admins
    is_admin = util.is_group_admin(ctx) or is_super_admin
    logger.debug(f"[eqa] ask() is_me={is_me} is_admin={is_admin} keyword={keyword!r}")

    if config['rule']['only_admin_answer_all'] and not is_me and not is_admin:
        return '回答所有人的只能管理设置啦'

    question_handler = config['comm']['answer_me'] if is_me else config['comm']['answer_all']
    answer_handler = config['comm']['answer_handler']
    logger.debug(f"[eqa] ask() answer_handler={answer_handler!r}")
    qa_msg = util.get_msg_keyword(answer_handler, keyword)
    logger.debug(f"[eqa] ask() qa_msg={qa_msg!r}")
    if not qa_msg:
        logger.warning(f"[eqa] ask() 未能从 keyword={keyword!r} 中提取问答分割，answer_handler={answer_handler!r}")
        return False
    ans, qus = qa_msg
    qus = f'{qus}'.strip()
    logger.info(f"[eqa] ask() 问题={qus!r} 回答={str(ans)[:50]!r}")
    if not str(qus).strip():
        return '问题呢? 问题呢??'
    if not str(ans).strip():
        return '回答呢? 回答呢??'

    # 问题与回答的分割
    ans_start = util.find_ms_str_index(ctx['message'], answer_handler)
    logger.debug(f"[eqa] ask() ans_start={ans_start}")

    if re.search(r'\[CQ:image,', qus):
        qus = util.get_message_str(ctx['message'][:ans_start])
        qus = util.get_msg_keyword(question_handler, qus, True).strip()
        logger.debug(f"[eqa] ask() 图片问题，重新提取 qus={qus!r}")

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

    logger.debug(f"[eqa] ask() message segments={len(message)}")
    logger.info(f"[eqa] 准备写入DB: group={ctx['group_id']} user={ctx['user_id']} qus={qus!r}")

    # 使用MySQL存储
    try:
        db = await ensure_db()
        question_id = await db.add_question(
            question=qus,
            group_id=ctx['group_id'],
            is_global=is_super_admin and not is_me
        )
        logger.info(f"[eqa] 问题已写入，question_id={question_id}")

        await db.add_answer(
            question_id=question_id,
            user_id=ctx['user_id'],
            group_id=ctx['group_id'],
            is_me=is_me,
            message=message
        )
        logger.info(f"[eqa] 回答已写入 question_id={question_id}")
    except Exception as e:
        logger.error(f"[eqa] ask() DB操作失败: {type(e).__name__}: {e}", exc_info=True)
        return f'保存失败了啦，数据库错误: {type(e).__name__}'

    return '我学会啦 来问问我吧！'


# ensure_db 已在上方定义，请勿重复


async def answer(ctx):
    """回复的函数"""
    msg = util.get_message_str(ctx['message']).strip()
    
    logger.debug(f"[eqa] 正在为群 {ctx['group_id']} 匹配关键词: {msg}")

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
        logger.debug(f"[eqa] 未找到匹配的关键词: {msg}")
        return False

    logger.info(f"[eqa] 成功匹配到回答 ID: {ans['id']}")

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
            nonebot.get_bot().on_message(ctx)
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
