# 📊 Gemini周报功能使用说明

## 🎯 功能特点

使用Gemini Flash直接生成完整HTML的周报，避免模板解析的各种问题：

✅ **灵活性高** - AI自由设计布局，不受模板限制  
✅ **样式丰富** - 自动生成精美的深色主题 Bento Grid 布局  
✅ **减少错误** - 不需要复杂的内容解析逻辑  
✅ **更有创意** - AI可以根据内容特点调整设计  

## 🔧 配置步骤

### 1. 获取Gemini API Key

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 登录Google账号
3. 点击"Create API Key"创建API密钥
4. 复制生成的API Key

### 2. 配置API Key

编辑 `config.py` 文件：

```python
# Gemini配置（用于周报等需要直接生成HTML的场景）
GEMINI_API_KEY = "你的Gemini API Key"  # 粘贴你的API Key
USE_GEMINI_FOR_WEEKLY = True  # 启用Gemini周报
```

### 3. 安装依赖

确保已安装必要的依赖：

```bash
pip install httpx playwright
# 初始化playwright浏览器
playwright install chromium
```

## 📝 使用方法

### 命令格式

```
周报              # 生成本群的周报
周报 群号         # 生成指定群的周报（需要管理员权限）
```

别名命令：`zhoubao`、`zb`

### 使用示例

```
# 生成本群周报
周报

# 生成指定群的周报
周报 123456789
```

## 🎨 周报内容

周报自动包含以下内容：

1. **周报标题和日期范围** - 显示统计的时间段
2. **本周数据概览** - 总消息数、活跃人数、最活跃时段等
3. **热门话题TOP5** - 本周最热门的讨论话题
4. **本周热词云** - 高频关键词列表
5. **精彩瞬间** - 摘录有趣或有价值的对话
6. **群星榜单** - 话痨王、话题之星、金句之王等
7. **本周总结** - AI生成的周报总结

## 🔍 工作原理

```
1. 收集过去7天的聊天记录
2. 优化并压缩聊天记录格式
3. 调用Gemini API生成完整HTML
4. 使用Playwright将HTML转换为图片
5. 发送图片到群聊
```

## 🌟 优势对比

### 传统模板方式

```
❌ 需要复杂的内容解析逻辑
❌ 模板固定，灵活性差
❌ 容易出现格式解析错误
❌ 维护成本高
```

### Gemini直接生成HTML

```
✅ AI直接生成完整HTML，无需解析
✅ 布局灵活，可以根据内容调整
✅ 减少代码复杂度和bug
✅ 样式更现代、更美观
```

## ⚙️ 高级配置

### 自定义提示词

在 `config.py` 中修改 `GEMINI_WEEKLY_PROMPT` 可以自定义周报内容和样式：

```python
GEMINI_WEEKLY_PROMPT = """
你的自定义提示词...
"""
```

### 调整聊天记录长度

在 `weekly_report.py` 中修改 `MAX_LENGTH` 参数：

```python
MAX_LENGTH = 80000  # 最大字符数，根据需要调整
```

## 🐛 故障排除

### 问题1：提示"Gemini API未配置"

**解决方案**：检查 `config.py` 中的 `GEMINI_API_KEY` 是否正确设置

### 问题2：图片生成失败

**解决方案**：
1. 确保已安装playwright: `pip install playwright`
2. 初始化浏览器: `playwright install chromium`
3. 检查日志文件查看详细错误信息

### 问题3：API调用失败

**解决方案**：
1. 检查API Key是否有效
2. 确认网络连接正常
3. 查看日志中的具体错误信息

### 问题4：聊天记录过长

**解决方案**：系统会自动截断过长的记录，在提示词中会注明"部分记录被省略"

## 📦 文件结构

```
dailySum/
├── gemini_client.py       # Gemini API客户端
├── weekly_report.py       # 周报生成逻辑
├── config.py              # 配置文件（添加GEMINI_API_KEY）
└── __init__.py            # 命令处理（添加周报命令）
```

## 💡 提示

1. 周报生成需要过去7天的聊天记录，确保日报功能正常运行
2. 首次使用建议先测试本群周报，确认功能正常
3. 生成周报可能需要30-60秒，请耐心等待
4. 如果群消息量特别大，可能需要更长时间

## 🎉 示例效果

周报将以精美的图片形式展示：
- 深色主题，类似苹果官网风格
- Bento Grid卡片式布局
- 优雅的渐变色和圆角设计
- 清晰的数据可视化
- emoji图标点缀

---

**注意**：Gemini API可能有调用频率限制，请合理使用～
