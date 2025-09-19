# B站视频总结模块

这是一个适用于HoshinoBot的B站视频总结模块，可以自动识别群聊中的B站视频链接和小程序分享，并生成视频内容的摘要总结。

## 功能特点

- 自动识别B站视频链接和小程序分享
- 提取视频标题、UP主、简介等基本信息
- 获取视频字幕并生成内容摘要
- 支持本地测试功能

## 安装方法

1. 将整个`bilisummary`文件夹放入HoshinoBot的`hoshino/modules/`目录下
2. 重启HoshinoBot

## 使用方法

模块会自动监听群聊消息，当检测到B站视频链接或小程序分享时，会自动获取视频信息并生成总结。

支持的链接格式：
- 标准链接：`https://www.bilibili.com/video/BV1GJ411x7h7`
- 短链接：`https://b23.tv/BV1GJ411x7h7`
- AV号链接：`https://www.bilibili.com/video/av170001`
- B站小程序分享

## 配置说明

在`config.py`中可以修改以下配置：

```python
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
```

## 本地测试

可以使用`test.py`进行本地测试：

```bash
cd hoshino/modules/bilisummary
python test.py
```

测试脚本会提供几个预设的B站视频链接供测试，也可以输入自定义链接进行测试。

## 注意事项

- 由于B站API限制，部分视频可能无法获取字幕
- 总结功能基于字幕内容，如果视频没有字幕，将只显示基本信息
- 服务器性能较差时，可能会导致响应较慢

## 依赖项

本模块依赖于HoshinoBot的`aiorequests`模块，无需额外安装依赖。