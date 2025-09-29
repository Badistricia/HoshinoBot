import re
import json
import aiohttp
import time
import hashlib
import random
import string
# qrcode依赖已移除
import asyncio
import os
import traceback
import urllib.parse
from io import BytesIO
from urllib.parse import urlparse, parse_qs, urlencode

# 提取视频ID的函数
async def extract_video_id_async(text):
    """从文本中提取B站视频ID（BV号或av号）"""
    if not text:
        return None
        
    # 匹配BV号或av号的正则表达式
    pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:bilibili\.com/video/|b23\.tv/|m\.bilibili\.com/video/)(BV[A-Za-z0-9]+|av\d+)|(?:^|\s)(BV[A-Za-z0-9]+|av\d+)(?:\s|$)', re.IGNORECASE)
    
    # 尝试直接匹配
    match = pattern.search(text)
    if match:
        # 返回第一个非None的组
        return next((g for g in match.groups() if g), None)
    
    # 如果是短链接，尝试解析
    if 'b23.tv' in text:
        try:
            short_url = re.search(r'https?://b23\.tv/\w+', text)
            if short_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(short_url.group(), allow_redirects=False) as resp:
                        if resp.status == 302:
                            location = resp.headers.get('Location')
                            if location:
                                match = pattern.search(location)
                                if match:
                                    return next((g for g in match.groups() if g), None)
        except Exception as e:
            print(f"解析短链接出错: {e}")
    
    return None

# WBI签名相关函数
def get_mixin_key(orig: str) -> str:
    """获取WBI签名的混合密钥"""
    return hashlib.md5(orig.encode()).hexdigest()

async def get_wbi_keys(cookies=None):
    """获取最新的WBI签名密钥"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com'
        }
        
        # 添加cookies
        if cookies:
            headers['Cookie'] = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.bilibili.com/x/web-interface/nav', headers=headers) as resp:
                res = await resp.json()
                if res['code'] != 0:
                    print(f"获取WBI密钥失败: {res['message']}")
                    return None, None
                    
                img_url = res['data']['wbi_img']['img_url']
                sub_url = res['data']['wbi_img']['sub_url']
                
                img_key = img_url.split('/')[-1].split('.')[0]
                sub_key = sub_url.split('/')[-1].split('.')[0]
                
                return img_key, sub_key
    except Exception as e:
        print(f"获取WBI密钥出错: {e}")
        return None, None

def encrypt_wbi(params: dict, img_key: str, sub_key: str) -> dict:
    """为请求参数进行WBI签名"""
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time
    
    # 按照key排序
    params = dict(sorted(params.items()))
    
    # 过滤一些key
    filtered_params = {
        k: params[k] for k in params
        if k not in ["sign", "wts"]
    }
    
    # 拼接参数
    query = urlencode(filtered_params)
    
    # 计算签名
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    
    # 添加签名
    params['sign'] = wbi_sign
    
    return params

# 扫码登录相关函数
async def generate_qrcode():
    """生成B站登录二维码 - 已禁用，不再支持二维码登录"""
    print("二维码登录功能已禁用")
    return None, None

async def check_qrcode_status(oauthKey):
    """检查二维码扫描状态 - 已禁用，不再支持二维码登录"""
    print("二维码登录功能已禁用")
    return {
        'status': 'error',
        'message': '二维码登录功能已禁用'
    }

async def login_with_qrcode():
    """完整的扫码登录流程 - 已禁用，不再支持二维码登录"""
    print("二维码登录功能已禁用")
    return None

# 提取视频ID
async def resolve_short_url(url):
    """解析B站短链接，获取真实URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, allow_redirects=False) as resp:
                if resp.status in [301, 302, 303, 307, 308]:
                    redirect_url = resp.headers.get('Location')
                    print(f"[短链接解析] {url} -> {redirect_url}")
                    return redirect_url
                else:
                    print(f"[短链接解析] 无重定向，返回原URL: {url}")
                    return url
    except Exception as e:
        print(f"[短链接解析] 解析短链接出错: {e}")
        return url

def extract_video_id_sync(url):
    """从B站URL中提取视频ID（同步版本，已废弃，请使用异步版本）"""
    if not url:
        return None
    
    try:
        # 清理URL，移除多余的引号和空格
        url = url.strip().strip('"\'')
        
        print(f"[提取视频ID] 警告：使用了同步版本的extract_video_id_sync，请改用异步版本")
        print(f"[提取视频ID] 原始URL: {url}")
        
        # 处理BV号 - 修正正则表达式以匹配完整BV号
        bv_match = re.search(r'[Bb][Vv]([0-9A-Za-z]+)', url)
        if bv_match:
            bvid = f"BV{bv_match.group(1)}"
            print(f"[提取视频ID] 提取到BV号: {bvid}")
            return bvid
        
        # 处理AV号
        av_match = re.search(r'[Aa][Vv](\d+)', url)
        if av_match:
            avid = f"av{av_match.group(1)}"
            print(f"[提取视频ID] 提取到AV号: {avid}")
            return avid
        
        # 处理URL参数中的bvid或aid
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            if 'bvid' in query_params:
                bvid = query_params['bvid'][0]
                print(f"[提取视频ID] 从URL参数提取到BV号: {bvid}")
                return bvid
            
            if 'aid' in query_params:
                avid = f"av{query_params['aid'][0]}"
                print(f"[提取视频ID] 从URL参数提取到AV号: {avid}")
                return avid
        except Exception as parse_error:
            print(f"[提取视频ID] 解析URL参数出错: {parse_error}")
        
        # 如果以上方法都失败，尝试从路径中提取
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')
            for part in path_parts:
                if part.startswith('BV') or part.startswith('bv'):
                    print(f"[提取视频ID] 从URL路径提取到BV号: {part}")
                    return part
                elif part.startswith('AV') or part.startswith('av'):
                    print(f"[提取视频ID] 从URL路径提取到AV号: {part}")
                    return part
        except Exception as path_error:
            print(f"[提取视频ID] 解析URL路径出错: {path_error}")
        
        print(f"[提取视频ID] 无法从URL提取视频ID: {url}")
        return None
    except Exception as e:
        print(f"[提取视频ID] 提取视频ID出错: {e}")
        print(f"[提取视频ID] 问题URL: {url}")
        print(f"[提取视频ID] 错误详情: {traceback.format_exc()}")
        return None

async def extract_video_id(url):
    """异步版本的视频ID提取，支持短链接解析"""
    if not url:
        return None
    
    try:
        # 清理URL，移除多余的引号和空格
        url = url.strip().strip('"\'')
        
        print(f"[提取视频ID] 原始URL: {url}")
        
        # 检查是否为B站短链接
        if 'b23.tv' in url or 'bili2233.cn' in url:
            print(f"[提取视频ID] 检测到短链接，开始解析...")
            resolved_url = await resolve_short_url(url)
            if resolved_url and resolved_url != url:
                print(f"[提取视频ID] 短链接解析成功: {resolved_url}")
                # 递归调用自身处理解析后的URL，但避免无限递归
                if 'b23.tv' not in resolved_url and 'bili2233.cn' not in resolved_url:
                    return await extract_video_id(resolved_url)
                else:
                    print(f"[提取视频ID] 警告: 解析后仍然是短链接，尝试直接提取")
            else:
                print(f"[提取视频ID] 短链接解析失败，尝试直接提取")
        
        # 尝试从URL中提取BV号或AV号
        # BV号格式: BV开头的10-12位字符
        bv_match = re.search(r'BV([a-zA-Z0-9]{10,12})', url)
        if bv_match:
            bvid = f"BV{bv_match.group(1)}"
            print(f"[提取视频ID] 成功提取BV号: {bvid}")
            return bvid
        
        # AV号格式: av+数字 或 AV+数字
        av_match = re.search(r'[aA][vV](\d+)', url)
        if av_match:
            aid = f"av{av_match.group(1)}"
            print(f"[提取视频ID] 成功提取AV号: {aid}")
            return aid
        
        # 尝试从URL参数中提取
        try:
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # 检查URL参数中是否有bvid或aid
            if 'bvid' in query_params:
                bvid = query_params['bvid'][0]
                print(f"[提取视频ID] 从URL参数提取BV号: {bvid}")
                return bvid
            elif 'aid' in query_params:
                aid = f"av{query_params['aid'][0]}"
                print(f"[提取视频ID] 从URL参数提取AV号: {aid}")
                return aid
        except Exception as e:
            print(f"[提取视频ID] 解析URL参数出错: {e}")
        
        # 尝试从路径中提取
        path_parts = parsed_url.path.split('/')
        for part in path_parts:
            if part.startswith('BV'):
                print(f"[提取视频ID] 从路径提取BV号: {part}")
                return part
            elif part.startswith('av'):
                print(f"[提取视频ID] 从路径提取AV号: {part}")
                return part
        
        print(f"[提取视频ID] 无法从URL提取视频ID: {url}")
        return None
    except Exception as e:
        print(f"[提取视频ID] 提取视频ID出错: {e}")
        print(f"[提取视频ID] 问题URL: {url}")
        print(f"[提取视频ID] 错误详情: {traceback.format_exc()}")
        return None

async def get_video_info(video_id, cookies=None):
    """获取B站视频信息"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com'
        }
        
        # 添加cookies
        if cookies:
            headers['Cookie'] = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        
        # 判断是BV号还是AV号
        if video_id.lower().startswith('av'):
            params = {'aid': video_id[2:]}
        else:  # BV号
            params = {'bvid': video_id}
        
        # 获取WBI签名
        img_key, sub_key = await get_wbi_keys(cookies)
        if img_key and sub_key:
            params = encrypt_wbi(params, img_key, sub_key)
            api_url = f"https://api.bilibili.com/x/web-interface/wbi/view?{urlencode(params)}"
        else:
            # 降级使用普通API
            api_url = f"https://api.bilibili.com/x/web-interface/view?{urlencode(params)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as resp:
                res = await resp.json()
                
                if res['code'] == 0:
                    return res['data']
                else:
                    print(f"API返回错误: {res['message']}")
                    return None
    except Exception as e:
        print(f"获取视频信息出错: {e}")
        return None

async def get_video_subtitle(video_id, cookies=None):
    """获取B站视频字幕"""
    try:
        # 如果传入的是URL而不是视频ID，先提取视频ID
        if video_id and ('http' in video_id or 'b23.tv' in video_id):
            print(f"[字幕] 检测到URL，尝试提取视频ID: {video_id}")
            extracted_id = await extract_video_id_async(video_id)
            if extracted_id:
                video_id = extracted_id
                print(f"[字幕] 成功从URL提取视频ID: {video_id}")
            else:
                print(f"[字幕] 无法从URL提取视频ID: {video_id}")
                return None
                
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com'
        }
        
        # 添加cookies
        if cookies:
            headers['Cookie'] = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        
        # 首先获取视频信息，找到cid
        print(f"[字幕] 开始获取视频信息: {video_id}")
        video_info = await get_video_info(video_id, cookies)
        if not video_info:
            print(f"[字幕] 获取视频信息失败，无法获取字幕: {video_id}")
            return None
        
        cid = video_info['cid']
        title = video_info.get('title', '未知标题')
        print(f"[字幕] 视频信息获取成功 - ID: {video_id}, CID: {cid}, 标题: {title}")
        
        # 获取字幕列表
        # 确保使用正确的视频ID格式
        if 'bvid' in video_info and video_info['bvid']:
            bvid = video_info['bvid']
            params = {
                'bvid': bvid,
                'cid': cid
            }
            print(f"[字幕] 使用BVID请求字幕: {bvid}")
            id_type = 'bvid'
            id_value = bvid
        else:
            # 确保aid是纯数字格式
            aid = str(video_info['aid']).replace('av', '')
            params = {
                'aid': aid,
                'cid': cid
            }
            print(f"[字幕] 使用AID请求字幕: {aid}")
            id_type = 'aid'
            id_value = aid
        
        # 获取WBI签名
        img_key, sub_key = await get_wbi_keys(cookies)
        if img_key and sub_key:
            params = encrypt_wbi(params, img_key, sub_key)
            subtitle_url = f"https://api.bilibili.com/x/player/wbi/v2?{urlencode(params)}"
            print(f"[字幕] 使用WBI签名请求字幕")
        else:
            # 降级使用普通API
            subtitle_url = f"https://api.bilibili.com/x/player/v2?{id_type}={id_value}&cid={cid}"
            print(f"[字幕] 降级使用普通API请求字幕")
        
        print(f"[字幕] 请求字幕列表URL: {subtitle_url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(subtitle_url, headers=headers) as resp:
                res = await resp.json()
                
                if res['code'] != 0:
                    print(f"[字幕] 获取字幕列表失败: {res.get('message', '未知错误')} (错误码: {res['code']})")
                    # 尝试使用另一种ID类型
                    if id_type == 'bvid' and 'aid' in video_info:
                        print(f"[字幕] 尝试使用AID重新请求字幕")
                        aid = str(video_info['aid']).replace('av', '')
                        retry_url = f"https://api.bilibili.com/x/player/v2?aid={aid}&cid={cid}"
                        async with session.get(retry_url, headers=headers) as retry_resp:
                            res = await retry_resp.json()
                    elif id_type == 'aid' and 'bvid' in video_info:
                        print(f"[字幕] 尝试使用BVID重新请求字幕")
                        retry_url = f"https://api.bilibili.com/x/player/v2?bvid={video_info['bvid']}&cid={cid}"
                        async with session.get(retry_url, headers=headers) as retry_resp:
                            res = await retry_resp.json()
                
                if res['code'] != 0 or 'subtitle' not in res['data']:
                    print(f"[字幕] 获取字幕列表失败: {res.get('message', '未知错误')}")
                    return None
                
                subtitle_list = res['data']['subtitle']['subtitles']
                print(f"[字幕] 找到字幕数量: {len(subtitle_list)}")
                
                if not subtitle_list:
                    print(f"[字幕] 视频 '{title}' 没有字幕")
                    return None
                
                # 获取字幕（优先选择官方字幕）
                # ai_status=0 表示官方字幕，ai_status=1 表示AI生成字幕
                official_subtitles = [s for s in subtitle_list if s.get('ai_status', 1) == 0]
                
                if official_subtitles:
                    subtitle_item = official_subtitles[0]
                    print(f"[字幕] 使用官方字幕: {subtitle_item.get('lan_doc', '未知语言')}")
                else:
                    # 如果没有官方字幕，使用AI生成字幕
                    subtitle_item = subtitle_list[0]
                    print(f"[字幕] 使用AI生成字幕 (可能不准确): {subtitle_item.get('lan_doc', '未知语言')}")
                
                # 打印字幕详细信息，便于调试
                print(f"[字幕] 字幕详情: {json.dumps(subtitle_item, ensure_ascii=False)}")
                
                subtitle_content_url = subtitle_item['subtitle_url']
                if not subtitle_content_url.startswith('http'):
                    subtitle_content_url = f"https:{subtitle_content_url}"
                
                print(f"[字幕] 字幕内容URL: {subtitle_content_url}")
                
                # 获取字幕内容
                try:
                    async with session.get(subtitle_content_url, headers=headers) as subtitle_resp:
                        if subtitle_resp.status != 200:
                            print(f"[字幕] 获取字幕内容失败: HTTP状态码 {subtitle_resp.status}")
                            return None
                        
                        subtitle_data = await subtitle_resp.json()
                        
                        # 提取纯文本
                        text_lines = []
                        for item in subtitle_data.get('body', []):
                            if 'content' in item:
                                text_lines.append(item['content'])
                        
                        if not text_lines:
                            print(f"[字幕] 字幕内容为空")
                            return None
                        
                        subtitle_text = '\n'.join(text_lines)
                        print(f"[字幕] 成功获取字幕，共{len(text_lines)}行")
                        print(f"[字幕] 字幕预览: {subtitle_text[:100]}...")
                        
                        # 验证字幕有效性
                        if len(text_lines) < 3:
                            print(f"[字幕] 警告: 字幕行数过少，可能不完整")
                        
                        return subtitle_text
                except Exception as e:
                    print(f"[字幕] 获取字幕内容出错: {e}")
                    print(f"[字幕] 错误详情: {traceback.format_exc()}")
                    return None
    
    except Exception as e:
        print(f"[字幕] 获取视频字幕出错: {e}")
        print(f"[字幕] 错误详情: {traceback.format_exc()}")
        return None

# 测试函数
async def test_api(video_url, use_login=False):
    """测试API功能"""
    video_id = await extract_video_id(video_url)
    if not video_id:
        return "无法提取视频ID"
    
    print(f"提取的视频ID: {video_id}")
    
    # 如果需要登录
    cookies = None
    if use_login:
        print("开始扫码登录流程...")
        cookies = await login_with_qrcode()
        if not cookies:
            print("登录失败，将使用未登录状态继续")
    
    # 获取视频信息
    video_info = await get_video_info(video_id, cookies)
    if not video_info:
        return "获取视频信息失败"
    
    print(f"视频标题: {video_info['title']}")
    print(f"UP主: {video_info['owner']['name']}")
    
    # 获取字幕
    subtitle = await get_video_subtitle(video_id, cookies)
    if subtitle:
        print(f"字幕长度: {len(subtitle)}")
        print(f"字幕预览: {subtitle[:100]}...")
    else:
        print("无法获取字幕或视频没有字幕")
    
    return "测试完成"

# 保存和加载cookies
def save_cookies(cookies, file_path="bilibili_cookies.json"):
    """保存cookies到文件"""
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(cookies, f)
        print(f"Cookies已保存到: {file_path}")
        return True
    except Exception as e:
        print(f"保存cookies出错: {e}")
        return False

def load_cookies(file_path="bilibili_cookies.json"):
    """从文件加载cookies"""
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        if not os.path.exists(file_path):
            print(f"Cookies文件不存在: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        print(f"Cookies已从{file_path}加载")
        return cookies
    except Exception as e:
        print(f"加载cookies出错: {e}")
        return None