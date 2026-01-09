from os import urandom
from PIL import Image, ImageSequence
import requests
import re
import os
from io import BytesIO

import nonebot
from hoshino import Service, priv

sv_help = '''
- [倒放 xx] xx为gif图
'''.strip()

sv = Service(
    name = 'GIF倒放',  #功能名
    use_priv = priv.NORMAL, #使用权限   
    manage_priv = priv.ADMIN, #管理权限
    visible = True, #是否可见
    enable_on_default = True, #是否默认启用
    bundle = '通用', #属于哪一类
    help_ = sv_help #帮助文本
    )

@sv.on_fullmatch(["帮助GIF倒放"])
async def bangzhu(bot, ev):
    await bot.send(ev, sv_help, at_sender=True)
    

headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "zh-cn"
           }
fd = os.path.dirname(__file__)


@sv.on_keyword("倒放")
async def revgif(bot, ev):
    message_id = None
    # 情况1，用户对需要倒放的gif进行回复
    match = re.match(r"\[CQ:reply,id=(?P<id>.*)\]\[CQ:", str(ev.message))
    if match is not None:
        message_id = match.group("id")
        pre_message = await bot.get_msg(message_id=message_id)
        pre_raw_message = pre_message["message"]
        await match_revgif(bot, ev, custom=pre_raw_message)
    else:
        await match_revgif(bot, ev)


async def match_revgif(bot, ev, custom=None):
    if custom is not None:
        ev.message = str(custom)
    # 情况2，用户直接发送“倒放+GIF图片”
    match = re.match(r"(.*)\[CQ:image(.*?)url=(?P<url>.*)\]", str(ev.message))
    if match is not None:
        image_url = match.group("url")
        await do_revgif(bot, ev, image_url)
    else:
        await bot.finish(ev, "未找到图片信息，请尝试重新发送图片")


async def do_revgif(bot, ev, image_url):
    print("正在准备图片")
    try:
        response = requests.get(image_url, headers=headers)
        response.raise_for_status() # Check for HTTP errors
        
        # Check content type if possible
        content_type = response.headers.get('Content-Type', '')
        if 'image' not in content_type and 'application/octet-stream' not in content_type:
             # Some CDNs return application/octet-stream for images
             await bot.finish(ev, f"下载的不是图片喵？(Content-Type: {content_type})")

        image = Image.open(BytesIO(response.content))
        print(f"frames:{getattr(image, 'n_frames', 1)}, mode:{image.mode}") # Safe getattr

        if getattr(image, 'n_frames', 1) <= 1:
            await bot.finish(ev, "并非GIF图片或者只有一帧喵~")
        if image.n_frames > 200:
            await bot.finish(ev, "GIF帧数太多了，懒得倒放[CQ:face,id=13]")

        sequence = []
        for f in ImageSequence.Iterator(image):
            sequence.append(f.copy())
        if len(sequence) > 30:
            await bot.send(ev, "ℹ正在翻转图片序列，请稍候")
        sequence.reverse()
        gif_path = os.path.join(fd, f"{ev.user_id}.gif")
        sequence[0].save(gif_path, save_all=True,
                         append_images=sequence[1:], disposal=1, loop=0)

        if os.path.exists(gif_path):
            await bot.send(ev, f"[CQ:image,file=file:///{gif_path}]")
            os.remove(gif_path)
        else:
            await bot.finish(ev, "写入文件时发生未知错误")
            
    except requests.exceptions.RequestException as e:
        await bot.finish(ev, f"下载图片失败了喵: {e}")
    except (IOError, SyntaxError) as e: # PIL errors
        await bot.finish(ev, f"图片无法识别，可能不是有效的图片格式喵: {e}")
    except Exception as e:
        await bot.finish(ev, f"发生未知错误: {e}")
