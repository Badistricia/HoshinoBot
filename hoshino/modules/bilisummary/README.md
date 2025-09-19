# B站视频解析和总结模块

这是一个适用于HoshinoBot的B站视频解析和总结模块，可以自动识别群聊中的B站视频链接，发送小程序卡片，并支持AI总结功能。

## 功能特点

- 🔗 **自动链接解析**：自动识别群聊中的B站视频链接，发送小程序卡片
- 📝 **AI智能总结**：回复"总结"或"摘要"可获取视频的AI总结
- 🎯 **多种触发方式**：支持命令式和引用式两种总结方式
- 📊 **丰富信息展示**：显示视频标题、UP主、时长、播放量等详细信息
- 🤖 **AI接口集成**：支持DeepSeek等多种AI服务

## 安装方法

1. 将整个`bilisummary`文件夹放入HoshinoBot的`hoshino/modules/`目录下
2. 安装依赖：`pip install -r requirements.txt`
3. 重启HoshinoBot

## 使用方法

### 1. 自动链接解析
当群友发送B站视频链接时，机器人会自动发送小程序卡片：

支持的链接格式：
- 标准链接：`https://www.bilibili.com/video/BV1GJ411x7h7`
- 短链接：`https://b23.tv/BV1GJ411x7h7`
- 移动端链接：`https://m.bilibili.com/video/BV1GJ411x7h7`
- AV号链接：`https://www.bilibili.com/video/av170001`
- 纯BV号：`BV1GJ411x7h7`

### 2. AI总结功能

#### 方式一：引用消息总结
1. 群友发送B站视频链接
2. 回复该消息并发送"总结"或"摘要"
3. 机器人会生成该视频的AI总结

#### 方式二：命令式总结
发送以下命令之一，后跟视频链接或BV号：
- `b站摘要 [链接/BV号]`
- `B站摘要 [链接/BV号]`
- `哔哩哔哩摘要 [链接/BV号]`
- `bili摘要 [链接/BV号]`

### 使用示例

```
# 自动解析（群友发送）
https://www.bilibili.com/video/BV1GJ411x7h7
→ 机器人自动发送小程序卡片

# 引用总结
群友：https://www.bilibili.com/video/BV1GJ411x7h7
你：[回复上述消息] 总结
→ 机器人生成AI总结

# 命令总结
b站摘要 BV1GJ411x7h7
→ 机器人生成AI总结
```

## 配置说明

### AI配置
在`ai_summary.py`中的`config.json`文件中配置AI服务：

```json
{
    "api_key": "your-api-key",
    "base_url": "https://api.deepseek.com/v1",
    "proxy": null,
    "model": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 1000
}
```

### B站登录（可选）
如需获取更多视频信息，可以配置B站登录：

1. 运行 `python manual_login.py` 进行二维码登录
2. 登录成功后会自动保存cookies到 `bilibili_cookies.json`

## 文件结构

```
bilisummary/
├── __init__.py          # 主模块文件
├── bilibili_api.py      # B站API接口
├── ai_summary.py        # AI总结功能
├── ai_client.py         # AI客户端
├── manual_login.py      # B站登录工具
├── test_summary.py      # 测试脚本
├── requirements.txt     # 依赖列表
└── README.md           # 说明文档
```

## 本地测试

可以使用测试脚本进行功能测试：

```bash
cd hoshino/modules/bilisummary
python test_summary.py
```

## 注意事项

- 🔐 **登录状态**：未登录状态下可能无法获取某些视频信息
- 📺 **字幕获取**：部分视频可能没有字幕，会影响总结质量
- ⚡ **响应速度**：AI总结需要一定时间，请耐心等待
- 🔑 **API密钥**：请确保AI服务的API密钥有效且有足够额度
- 🚫 **私有视频**：无法解析需要登录或付费的视频

## 依赖项

- `aiohttp`：异步HTTP请求
- `qrcode`：二维码生成（登录功能）
- `Pillow`：图像处理（二维码显示）

## 更新日志

- **v2.0**：新增自动链接解析和小程序发送功能
- **v2.0**：新增引用消息总结功能
- **v2.0**：优化消息格式和用户体验
- **v1.0**：基础AI总结功能