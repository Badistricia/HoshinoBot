import re
import json
import aiohttp
import time
import hashlib
import random
import string
import qrcode
import asyncio
import os
import traceback
from io import BytesIO
from urllib.parse import urlparse, parse_qs, urlencode

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
    """生成B站登录二维码"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        # 获取二维码内容
        async with aiohttp.ClientSession() as session:
            async with session.get('https://passport.bilibili.com/qrcode/getLoginUrl', headers=headers) as resp:
                res = await resp.json()
                if res['code'] != 0:
                    print(f"获取登录二维码失败: {res['message']}")
                    return None, None
                
                login_url = res['data']['url']
                oauthKey = res['data']['oauthKey']
                
                # 生成二维码
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(login_url)
                qr.make(fit=True)
                
                # 在控制台打印二维码
                try:
                    # 尝试使用终端打印二维码
                    from qrcode.main import QRCode
                    qr.print_ascii(invert=True)
                    print("\n请使用B站APP扫描上方二维码登录")
                except:
                    # 如果无法在终端打印，则保存为图片
                    img = qr.make_image(fill_color="black", back_color="white")
                    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_qrcode.png")
                    img.save(img_path)
                    print(f"登录二维码已生成，请扫描: {img_path}")
                
                # 同时提供链接
                print(f"\n或者直接打开此链接扫码: {login_url}")
                
                return oauthKey, login_url
    except Exception as e:
        print(f"生成登录二维码出错: {e}")
        return None, None

async def check_qrcode_status(oauthKey):
    """检查二维码扫描状态"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        data = {
            'oauthKey': oauthKey
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post('https://passport.bilibili.com/qrcode/getLoginInfo', headers=headers, data=data) as resp:
                res = await resp.json()
                
                # 扫码成功
                if res.get('status', False):
                    cookies = {}
                    for url in res.get('data', {}).get('url', '').split('&'):
                        if '=' in url:
                            key, value = url.split('=', 1)
                            cookies[key] = value
                    
                    return {
                        'status': 'success',
                        'cookies': cookies
                    }
                
                # 扫码失败或等待扫码
                else:
                    code = res.get('data', -1)
                    message = {
                        -1: "二维码尚未扫描",
                        -2: "二维码已过期",
                        -4: "二维码已扫描，等待确认",
                        -5: "二维码已扫描，等待确认"
                    }.get(code, f"未知状态: {code}")
                    
                    return {
                        'status': 'waiting',
                        'message': message,
                        'code': code
                    }
    except Exception as e:
        print(f"检查二维码状态出错: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

async def login_with_qrcode():
    """完整的扫码登录流程"""
    oauthKey, img_path = await generate_qrcode()
    if not oauthKey:
        return None
    
    print("请使用B站APP扫描二维码登录")
    
    # 循环检查扫码状态
    for i in range(120):  # 最多等待120秒
        status = await check_qrcode_status(oauthKey)
        
        if status['status'] == 'success':
            print("登录成功!")
            return status['cookies']
        
        elif status['status'] == 'waiting':
            if status['code'] == -4 or status['code'] == -5:
                print("二维码已扫描，等待确认...请在手机B站APP中点击确认按钮")
            else:
                print(f"等待扫码: {status['message']}")
        
        else:
            print(f"登录出错: {status.get('message', '未知错误')}")
            break
        
        # 根据状态调整检查频率
        if status['code'] == -4 or status['code'] == -5:
            # 已扫描等待确认时，更频繁地检查
            await asyncio.sleep(0.5)
        else:
            # 未扫描时，降低检查频率
            await asyncio.sleep(1)
    
    print("登录超时或失败")
    return None

# 提取视频ID
def extract_video_id(url):
    """从B站URL中提取视频ID"""
    if not url:
        return None
    
    try:
        # 清理URL，移除多余的引号和空格
        url = url.strip().strip('"\'')
        
        # 处理BV号
        bv_match = re.search(r'[Bb][Vv]([a-zA-Z0-9]+)', url)
        if bv_match:
            return f"BV{bv_match.group(1)}"
        
        # 处理AV号
        av_match = re.search(r'[Aa][Vv](\d+)', url)
        if av_match:
            return f"av{av_match.group(1)}"
        
        # 处理URL参数中的bvid或aid
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        if 'bvid' in query_params:
            return query_params['bvid'][0]
        
        if 'aid' in query_params:
            return f"av{query_params['aid'][0]}"
        
        return None
    except Exception as e:
        print(f"提取视频ID出错: {e}")
        print(f"问题URL: {url}")
        print(f"错误详情: {traceback.format_exc()}")
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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com'
        }
        
        # 添加cookies
        if cookies:
            headers['Cookie'] = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        
        # 首先获取视频信息，找到cid
        video_info = await get_video_info(video_id, cookies)
        if not video_info:
            print(f"获取视频信息失败，无法获取字幕: {video_id}")
            return None
        
        cid = video_info['cid']
        print(f"[字幕] 视频ID: {video_id}, CID: {cid}, 标题: {video_info['title']}")
        
        # 获取字幕列表
        # 确保aid是数字格式
        aid = str(video_info['aid']).replace('av', '')
        
        params = {
            'cid': cid,
            'aid': aid
        }
        
        # 获取WBI签名
        img_key, sub_key = await get_wbi_keys()
        if img_key and sub_key:
            params = encrypt_wbi(params, img_key, sub_key)
            subtitle_url = f"https://api.bilibili.com/x/player/wbi/v2?{urlencode(params)}"
        else:
            # 降级使用普通API
            subtitle_url = f"https://api.bilibili.com/x/player/v2?cid={cid}&aid={aid}"
        
        print(f"[字幕] 请求字幕列表URL: {subtitle_url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(subtitle_url, headers=headers) as resp:
                res = await resp.json()
                
                if res['code'] != 0 or 'subtitle' not in res['data']:
                    print(f"[字幕] 获取字幕列表失败: {res.get('message', '未知错误')}")
                    return None
                
                subtitle_list = res['data']['subtitle']['subtitles']
                print(f"[字幕] 找到字幕数量: {len(subtitle_list)}")
                
                if not subtitle_list:
                    print("[字幕] 视频没有字幕")
                    return None
                
                # 获取第一个字幕（通常是中文）
                subtitle_item = subtitle_list[0]
                subtitle_content_url = subtitle_item['subtitle_url']
                if not subtitle_content_url.startswith('http'):
                    subtitle_content_url = f"https:{subtitle_content_url}"
                
                print(f"[字幕] 字幕内容URL: {subtitle_content_url}")
                print(f"[字幕] 字幕语言: {subtitle_item.get('lan_doc', '未知')}")
                
                # 获取字幕内容
                async with session.get(subtitle_content_url, headers=headers) as subtitle_resp:
                    subtitle_data = await subtitle_resp.json()
                    
                    # 提取纯文本
                    text_lines = []
                    for item in subtitle_data.get('body', []):
                        if 'content' in item:
                            text_lines.append(item['content'])
                    
                    subtitle_text = '\n'.join(text_lines)
                    print(f"[字幕] 成功获取字幕，共{len(text_lines)}行，预览: {subtitle_text[:100]}...")
                    return subtitle_text
    
    except Exception as e:
        print(f"[字幕] 获取视频字幕出错: {e}")
        print(f"[字幕] 错误详情: {traceback.format_exc()}")
        return None

# 测试函数
async def test_api(video_url, use_login=False):
    """测试API功能"""
    video_id = extract_video_id(video_url)
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