import html
import json
import os
import shutil
import tempfile
from datetime import datetime

from . import config

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(MODULE_DIR, 'temp_comments')
BROWSER_CONFIG_PATH = os.path.join(os.path.dirname(MODULE_DIR), 'dailySum', 'data', 'browser_config.json')


def _format_number(num):
    try:
        num = int(num or 0)
    except (TypeError, ValueError):
        return '0'
    if num >= 10000:
        return f'{num / 10000:.1f}万'
    return str(num)


def _format_time(timestamp):
    try:
        timestamp = int(timestamp or 0)
    except (TypeError, ValueError):
        return ''
    if timestamp <= 0:
        return ''
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')


def _format_duration(duration):
    try:
        duration = int(duration or 0)
    except (TypeError, ValueError):
        duration = 0
    minutes = duration // 60
    seconds = duration % 60
    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f'{hours}:{minutes:02d}:{seconds:02d}'
    return f'{minutes}:{seconds:02d}'


def _truncate_text(text, max_length):
    text = (text or '').strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + '...'


def _load_browser_path():
    try:
        if os.path.exists(BROWSER_CONFIG_PATH):
            with open(BROWSER_CONFIG_PATH, 'r', encoding='utf-8') as f:
                browser_path = json.load(f).get('browser_path', '')
            if browser_path and os.path.exists(browser_path):
                return browser_path
    except Exception:
        return ''
    return ''


def _build_comment_html(video_info, comments, comment_status=''):
    title = html.escape(video_info.get('title') or '未知标题')
    author = html.escape((video_info.get('owner') or {}).get('name') or '未知UP主')
    bvid = html.escape(video_info.get('bvid') or '')
    cover = html.escape(video_info.get('pic') or '')
    tname = html.escape(video_info.get('tname') or '未知分区')
    duration = html.escape(_format_duration(video_info.get('duration')))
    desc = html.escape(_truncate_text(video_info.get('desc') or '', 96))
    video_url = html.escape(f"https://www.bilibili.com/video/{video_info.get('bvid') or ''}")
    stat = video_info.get('stat') or {}
    view = _format_number(stat.get('view'))
    like = _format_number(stat.get('like'))
    coin = _format_number(stat.get('coin'))
    favorite = _format_number(stat.get('favorite'))
    danmaku = _format_number(stat.get('danmaku'))
    reply = _format_number(stat.get('reply'))
    width = int(getattr(config, 'HOT_COMMENTS_RENDER_WIDTH', 760))
    max_text_length = int(getattr(config, 'HOT_COMMENTS_MAX_TEXT_LENGTH', 280))

    cover_html = f'<img class="cover" src="{cover}" alt="">' if cover else '<div class="cover cover-fallback">Bilibili</div>'

    comment_items = []
    for index, comment in enumerate(comments, start=1):
        uname = html.escape(comment.get('uname') or '未知用户')
        message = html.escape(_truncate_text(comment.get('message'), max_text_length)).replace('\n', '<br>')
        avatar = html.escape(comment.get('avatar') or '')
        like = _format_number(comment.get('like'))
        reply_count = _format_number(comment.get('reply_count'))
        ctime = _format_time(comment.get('ctime'))
        child_items = []
        for child in (comment.get('replies') or [])[:2]:
            child_uname = html.escape(child.get('uname') or '未知用户')
            child_message = html.escape(_truncate_text(child.get('message'), 120)).replace('\n', '<br>')
            child_like = _format_number(child.get('like'))
            if child_message:
                child_items.append(f"""
              <div class="child-reply">
                <span class="child-name">{child_uname}</span>
                <span class="child-message">{child_message}</span>
                <span class="child-meta">赞 {child_like}</span>
              </div>
                """)
        children_html = f'<div class="child-replies">{"".join(child_items)}</div>' if child_items else ''

        if avatar:
            avatar_html = f'<img class="avatar" src="{avatar}" alt="">'
        else:
            avatar_html = '<div class="avatar avatar-fallback">B</div>'

        meta_parts = [f'<span>{ctime}</span>' if ctime else '', f'<span>赞 {like}</span>', f'<span>回复 {reply_count}</span>']
        meta = ''.join(part for part in meta_parts if part)

        comment_items.append(f"""
        <article class="comment">
          <div class="rank">#{index}</div>
          {avatar_html}
          <div class="body">
            <div class="row">
              <div class="name">{uname}</div>
              <div class="meta">{meta}</div>
            </div>
            <div class="message">{message}</div>
            {children_html}
          </div>
        </article>
        """)

    if comment_items:
        comments_html = '\n'.join(comment_items)
        comments_title = f'热门评论 Top {len(comments)}'
    else:
        status = html.escape(comment_status or '暂无可展示评论')
        comments_title = '热门评论'
        comments_html = f'<div class="empty-comments">{status}</div>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      padding: 24px;
      width: {width}px;
      background: #f5f7fb;
      color: #222;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
      letter-spacing: 0;
    }}
    .comments-shell {{
      width: 100%;
      background: #fff;
      border: 1px solid #e7e9f0;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(22, 28, 45, 0.08);
    }}
    .header {{
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 20px;
      padding: 22px 24px;
      border-bottom: 1px solid #edf0f5;
      background: #fbfcff;
    }}
    .cover {{
      width: 220px;
      height: 138px;
      border-radius: 8px;
      object-fit: cover;
      background: #edf0f5;
      border: 1px solid #e5e7ee;
    }}
    .cover-fallback {{
      display: grid;
      place-items: center;
      color: #fff;
      background: #00a1d6;
      font-weight: 800;
      font-size: 20px;
    }}
    .video-info {{
      min-width: 0;
    }}
    .eyebrow {{
      font-size: 13px;
      color: #fb7299;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .title {{
      font-size: 22px;
      line-height: 1.35;
      font-weight: 800;
      color: #171a21;
      margin-bottom: 10px;
      overflow-wrap: anywhere;
    }}
    .desc {{
      color: #697386;
      font-size: 13px;
      line-height: 1.5;
      margin: 8px 0 12px;
      overflow-wrap: anywhere;
    }}
    .sub {{
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      font-size: 13px;
      color: #697386;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-top: 14px;
    }}
    .stat {{
      min-width: 0;
      padding: 9px 10px;
      border: 1px solid #edf0f5;
      border-radius: 8px;
      background: #fff;
    }}
    .stat-label {{
      color: #8a93a6;
      font-size: 12px;
      margin-bottom: 3px;
    }}
    .stat-value {{
      color: #171a21;
      font-weight: 800;
      font-size: 15px;
    }}
    .section-title {{
      padding: 16px 24px 8px;
      font-size: 16px;
      font-weight: 800;
      color: #171a21;
    }}
    .list {{
      padding: 6px 0;
    }}
    .empty-comments {{
      margin: 14px 24px 22px;
      padding: 22px;
      border: 1px dashed #d8ddea;
      border-radius: 8px;
      color: #8a93a6;
      background: #fbfcff;
      text-align: center;
      font-size: 14px;
    }}
    .comment {{
      display: grid;
      grid-template-columns: 42px 46px 1fr;
      gap: 14px;
      padding: 18px 24px;
      border-bottom: 1px solid #edf0f5;
    }}
    .comment:last-child {{
      border-bottom: 0;
    }}
    .rank {{
      font-size: 14px;
      color: #fb7299;
      font-weight: 800;
      padding-top: 5px;
    }}
    .avatar {{
      width: 46px;
      height: 46px;
      border-radius: 50%;
      object-fit: cover;
      background: #edf0f5;
      border: 1px solid #e5e7ee;
    }}
    .avatar-fallback {{
      display: grid;
      place-items: center;
      color: #fff;
      background: #00a1d6;
      font-weight: 800;
      font-size: 18px;
    }}
    .body {{
      min-width: 0;
    }}
    .row {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 7px;
    }}
    .name {{
      min-width: 0;
      max-width: 330px;
      color: #2f3542;
      font-weight: 700;
      font-size: 15px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .meta {{
      flex: 0 0 auto;
      display: flex;
      gap: 10px;
      font-size: 12px;
      color: #8a93a6;
    }}
    .message {{
      font-size: 16px;
      line-height: 1.62;
      color: #2b2f38;
      overflow-wrap: anywhere;
      white-space: normal;
    }}
    .child-replies {{
      display: grid;
      gap: 6px;
      margin-top: 10px;
      padding: 9px 12px;
      border-radius: 8px;
      background: #f7f9fc;
      border: 1px solid #edf0f5;
    }}
    .child-reply {{
      display: grid;
      grid-template-columns: minmax(72px, 120px) 1fr auto;
      gap: 8px;
      align-items: start;
      color: #586176;
      font-size: 13px;
      line-height: 1.45;
    }}
    .child-name {{
      color: #44506a;
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .child-message {{
      overflow-wrap: anywhere;
    }}
    .child-meta {{
      color: #9aa3b5;
      white-space: nowrap;
    }}
    .footer {{
      padding: 12px 24px 16px;
      color: #9aa3b5;
      font-size: 12px;
      background: #fbfcff;
      border-top: 1px solid #edf0f5;
    }}
  </style>
</head>
<body>
  <main class="comments-shell">
    <section class="header">
      {cover_html}
      <div class="video-info">
        <div class="eyebrow">Bilibili 视频解析</div>
        <div class="title">{title}</div>
        <div class="sub">
          <span>UP 主：{author}</span>
          <span>分区：{tname}</span>
          <span>时长：{duration}</span>
          <span>{bvid}</span>
        </div>
        <div class="desc">{desc}</div>
        <div class="stats">
          <div class="stat"><div class="stat-label">播放</div><div class="stat-value">{view}</div></div>
          <div class="stat"><div class="stat-label">点赞</div><div class="stat-value">{like}</div></div>
          <div class="stat"><div class="stat-label">评论</div><div class="stat-value">{reply}</div></div>
          <div class="stat"><div class="stat-label">弹幕</div><div class="stat-value">{danmaku}</div></div>
          <div class="stat"><div class="stat-label">投币</div><div class="stat-value">{coin}</div></div>
          <div class="stat"><div class="stat-label">收藏</div><div class="stat-value">{favorite}</div></div>
        </div>
      </div>
    </section>
    <section class="section-title">{comments_title}</section>
    <section class="list">
      {comments_html}
    </section>
    <section class="footer">{video_url} · 评论来自 bilibili 视频评论区，按接口热门排序展示</section>
  </main>
</body>
</html>"""


async def render_hot_comments_image(video_info, comments, comment_status=''):
    """把视频信息和热门评论渲染为图片，成功返回图片路径，失败返回None。"""
    if not PLAYWRIGHT_AVAILABLE:
        return None

    os.makedirs(TEMP_DIR, exist_ok=True)
    work_dir = tempfile.mkdtemp(prefix='hot_comments_', dir=TEMP_DIR)
    html_path = os.path.join(work_dir, 'comments.html')
    image_path = os.path.join(work_dir, 'comments.png')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(_build_comment_html(video_info, comments, comment_status=comment_status))

    browser_path = _load_browser_path()
    browser = None
    try:
        async with async_playwright() as p:
            launch_options = {
                'args': ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
            }
            if browser_path:
                launch_options['executable_path'] = browser_path

            browser = await p.chromium.launch(**launch_options)
            page = await browser.new_page(
                viewport={'width': int(getattr(config, 'HOT_COMMENTS_RENDER_WIDTH', 760)), 'height': 1200},
                device_scale_factor=1,
            )
            await page.goto(f"file:///{html_path.replace(os.sep, '/')}", wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(800)
            container = await page.query_selector('.comments-shell')
            if container:
                await container.screenshot(path=image_path)
            else:
                await page.screenshot(path=image_path, full_page=True)
            await browser.close()

        if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
            return image_path
        shutil.rmtree(work_dir, ignore_errors=True)
        return None
    except Exception:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        shutil.rmtree(work_dir, ignore_errors=True)
        return None
