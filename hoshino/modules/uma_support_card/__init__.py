from hoshino import Service

sv = Service('uma_support_card', help_='''
[uma事件 关键词] 模糊搜索赛马娘协助卡事件
'''.strip())

from . import uma_support_card 