# Smart TodoList for Nonebot2

基于 Nonebot2 的智能待办清单插件，支持中文自然语言时间解析与仿便利贴风格图片生成。

## 功能特点

- **轻量化**: 使用 JSON 本地存储，按群/用户隔离数据。
- **智能化**: 集成 `jionlp`，支持 "明天下午三点提醒我" 等自然语言解析。
- **美观化**: 使用 HTML/CSS 渲染生成仿便利贴风格的图片列表。
- **持久化**: 自动管理定时任务，Bot 重启后任务不丢失。

## 依赖插件

请确保安装以下依赖：

```bash
pip install nonebot2 nonebot-adapter-onebot nonebot-plugin-apscheduler nonebot-plugin-htmlrender jionlp
```

注意: `jionlp` 首次运行会自动下载模型，请保持网络畅通。

## 指令列表

- **添加待办**: `记 [内容]` / `todo add [内容]` / `+ [内容]`
  - 示例: `记 明天上午10点去开会`
  - 机器人会自动识别时间并设置提醒。
- **查看列表**: `代办` / `todo list` / `dd`
  - 生成便利贴图片发送。
- **完成待办**: `完成 [ID]` / `ok [ID]`
  - 标记完成并取消提醒。
- **删除待办**: `删除 [ID]` / `del [ID]`
  - 物理删除数据。
- **清空待办**: `清空代办`
  - 清空当前用户在当前群的所有数据（需二次确认）。

## 目录结构

```
todo_list/
├── __init__.py           # 插件入口
├── data_manager.py       # 数据管理
├── scheduler_manager.py  # 定时任务管理
├── render_utils.py       # 图片渲染工具
└── templates/
    └── todo_list.html    # HTML 模板
```
