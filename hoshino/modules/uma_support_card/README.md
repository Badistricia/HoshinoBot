# 赛马娘协助卡查询插件

一个简单的赛马娘协助卡事件查询插件，用于在HoshinoBot中使用。

## 功能

- 模糊搜索赛马娘协助卡事件
- 显示事件的详细信息和选项效果
- 数据实时更新

## 使用方法

### 查询协助卡事件

使用以下命令进行查询：

```
uma事件 事件关键词
```

例如：
- `uma事件 云霄飞车`
- `uma事件 蹄铁`
- `马娘事件 这也烦恼`
- `赛马娘事件 胜利舞台`

### 更新数据

管理员可以使用以下命令手动更新数据：

```
更新uma数据
```

或

```
更新赛马娘数据
```

首次使用时，插件会自动初始化和下载所需数据。

## 数据来源

数据来源于Bilibili赛马娘工具站：
- 协助卡列表: https://api.game.bilibili.com/game/player/tools/uma/support_cards
- 协助卡详情: https://api.game.bilibili.com/game/player/tools/uma/support_card_detail

## 注意事项

- 首次使用时需要从API获取数据，可能需要一些时间
- 查询使用模糊匹配，返回最相关的前3个结果 