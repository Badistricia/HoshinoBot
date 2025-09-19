import json
import os
import sys
import asyncio

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from bilibili_api import save_cookies

def parse_cookies_string(cookies_str):
    """解析从浏览器复制的cookies字符串"""
    cookies = {}
    try:
        # 尝试解析为JSON格式
        try:
            cookies = json.loads(cookies_str)
            return cookies
        except json.JSONDecodeError:
            pass
        
        # 尝试解析为cookie字符串格式
        for item in cookies_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
        
        # 如果是单个值，可能是SESSDATA，尝试直接使用
        if not cookies and cookies_str.strip():
            cookies["SESSDATA"] = cookies_str.strip()
            print("已识别为SESSDATA值")
        
        return cookies
    except Exception as e:
        print(f"解析cookies失败: {e}")
        return None

async def manual_login():
    """手动输入cookies登录"""
    print("\n===== B站手动登录 =====")
    print("请按照以下步骤操作:")
    print("1. 使用浏览器访问 https://www.bilibili.com/ 并登录")
    print("2. 登录成功后，按F12打开开发者工具")
    print("3. 切换到'应用'或'Application'标签")
    print("4. 在左侧找到'Cookies' -> 'https://www.bilibili.com'")
    print("5. 找到并复制SESSDATA和bili_jct的值")
    print("6. 在下方分别输入\n")
    
    # 分步骤输入各个cookie值
    cookies = {}
    
    # 输入SESSDATA
    sessdata = input("请输入SESSDATA值: ")
    if sessdata.strip():
        cookies['SESSDATA'] = sessdata.strip()
        print("已保存SESSDATA")
    else:
        print("未输入SESSDATA，取消登录")
        return None
    
    # 输入bili_jct
    bili_jct = input("请输入bili_jct值: ")
    if bili_jct.strip():
        cookies['bili_jct'] = bili_jct.strip()
        print("已保存bili_jct")
    else:
        print("未输入bili_jct，但将继续使用SESSDATA尝试登录")
    
    # 可选输入其他cookie
    print("\n如果有其他cookie需要输入，请按以下格式输入: key=value")
    print("输入空行结束输入")
    
    while True:
        other_cookie = input("其他cookie (留空结束): ")
        if not other_cookie:
            break
            
        if '=' in other_cookie:
            key, value = other_cookie.strip().split('=', 1)
            cookies[key] = value
            print(f"已添加 {key}")
        else:
            print("格式错误，请使用 key=value 格式")
    
    # 检查必要的cookie是否存在
    if 'SESSDATA' not in cookies:
        print("缺少必要的cookie: SESSDATA")
        return None
    
    print("\n登录信息汇总:")
    for key, value in cookies.items():
        masked_value = value[:5] + "..." + value[-5:] if len(value) > 15 else value
        print(f"{key}: {masked_value}")
    
    # 保存cookies
    save_cookies(cookies)
    print("登录成功并保存cookies")
    
    return cookies

if __name__ == "__main__":
    asyncio.run(manual_login())