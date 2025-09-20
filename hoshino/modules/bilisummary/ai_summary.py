import os
import json
import sys

# 添加当前目录到sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_client import ai_client

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-94a61ab92c414de58af7e7cbf9d73cd7"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# 配置文件路径
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件出错: {e}")
    
    # 默认配置
    default_config = {
        "api_key": DEEPSEEK_API_KEY,
        "base_url": DEEPSEEK_BASE_URL,
        "proxy": None,
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    # 保存默认配置
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存默认配置出错: {e}")
    
    return default_config

async def generate_summary(video_info, subtitle=None, max_length=1000):
    """生成视频摘要"""
    config = load_config()
    client = ai_client.get_client(config)
    
    # 准备提示词
    title = video_info.get('title', '未知标题')
    author = video_info.get('owner', {}).get('name', '未知作者')
    desc = video_info.get('desc', '无描述')
    
    # 构建系统提示词
    system_prompt = "你是一个专业的视频内容总结助手，请根据提供的视频信息生成一个简洁、全面的视频摘要。"
    
    # 构建用户提示词
    user_prompt = f"请为以下B站视频生成一个摘要：\n\n标题：{title}\n作者：{author}\n描述：{desc}\n"
    
    # 如果有字幕，添加字幕内容
    if subtitle and subtitle.strip():
        # 如果字幕太长，截取前中后三部分
        if len(subtitle) > 3000:
            first_part = subtitle[:1000]
            middle_part = subtitle[len(subtitle)//2-500:len(subtitle)//2+500]
            last_part = subtitle[-1000:]
            subtitle_text = f"{first_part}\n...(中间内容省略)...\n{middle_part}\n...(中间内容省略)...\n{last_part}"
        else:
            subtitle_text = subtitle
        
        user_prompt += f"\n字幕内容：\n{subtitle_text}"
        user_prompt += "\n\n请根据视频标题、描述和字幕内容，生成一个全面、客观的视频内容摘要，包括主要观点、关键信息和结论。摘要应该简洁明了，不超过500字。"
    else:
        user_prompt += "\n\n【注意：该视频没有字幕】\n请仅根据视频标题和描述，尝试推测视频可能的内容，并生成一个简短的摘要。请在摘要开头明确说明'由于视频没有字幕，此摘要仅基于标题和描述推测'。摘要不超过300字。"
    
    try:
        # 调用DeepSeek API
        response = await client.chat.completions.create(
            model=config.get('model', 'deepseek-chat'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 1000)
        )
        
        # 提取生成的摘要
        summary = response.choices[0].message.content
        return summary
    
    except Exception as e:
        print(f"生成摘要出错: {e}")
        # 生成简单摘要作为备选
        return generate_simple_summary(video_info, subtitle)

def generate_simple_summary(video_info, subtitle=None):
    """生成简单摘要（当API调用失败时使用）"""
    title = video_info.get('title', '未知标题')
    author = video_info.get('owner', {}).get('name', '未知作者')
    desc = video_info.get('desc', '无描述')
    
    summary = f"视频《{title}》由UP主 {author} 创作。\n\n"
    summary += f"视频描述：{desc}\n\n"
    
    if subtitle:
        # 提取字幕的前100字符、中间100字符和最后100字符
        if len(subtitle) > 300:
            first_part = subtitle[:100].replace("\n", " ")
            middle_part = subtitle[len(subtitle)//2-50:len(subtitle)//2+50].replace("\n", " ")
            last_part = subtitle[-100:].replace("\n", " ")
            summary += f"字幕摘录：\n开头：{first_part}...\n中间：{middle_part}...\n结尾：{last_part}"
        else:
            subtitle_content = subtitle[:300].replace("\n", " ")
            summary += f"字幕内容：{subtitle_content}..."
    else:
        summary += "（该视频没有字幕）"
    
    return summary