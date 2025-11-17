# B站视频总结功能配置

# 是否启用B站链接自动总结功能
ENABLE_AUTO_SUMMARY = True

# 是否启用B站小程序自动总结功能
ENABLE_MINIAPP_SUMMARY = True

# 总结长度设置
SUMMARY_MAX_LENGTH = 300  # 总结最大长度（字符数）
SUMMARY_SEGMENTS = 3  # 从字幕中提取的片段数量

# 字幕处理设置
USE_SUBTITLE = True  # 是否使用字幕
SUBTITLE_FALLBACK = True  # 当无法获取字幕时，是否使用视频简介作为替代

# 请求超时设置（秒）
REQUEST_TIMEOUT = 10

# 调试模式
DEBUG = False

# DeepSeek API 设置
USE_AI_SUMMARY = True  # 是否使用 AI 进行总结
AI_CONFIG = {
    'api_key': '',  # 需要在实际使用时填写
    'base_url': 'https://api.deepseek.com/v1',
    'model': 'deepseek-chat',  # 默认模型
    'max_tokens': 1000,  # 生成的最大 token 数
    'temperature': 0.7,  # 生成的随机性
    'timeout': 30,  # API 请求超时时间（秒）
    'proxy': None,  # 代理设置，如 'http://127.0.0.1:7890'
}

# AI 总结提示词
SUMMARY_PROMPT = """你是一个专业的视频内容总结助手。请根据以下B站视频信息和字幕内容，生成一个简洁、全面的视频内容总结。
总结应该包括视频的主要内容、关键点和结论。

视频信息:
标题: {title}
UP主: {uploader}
简介: {desc}

视频字幕内容:
{subtitle}

请生成一个不超过300字的总结，格式如下:
【视频总结】
{summary}

注意：总结应该客观、准确，不要添加个人评价。"""