"""这是一份实例配置文件

将其修改为你需要的配置，并将文件夹config_example重命名为config
"""

# hoshino监听的端口与ip
PORT = 8081
HOST = '127.0.0.1'          # 本地部署使用此条配置（QQ客户端和bot端运行在同一台计算机）
# HOST = '0.0.0.0'          # 开放公网访问使用此条配置（不安全）

DEBUG = True               # 调试模式

BLACK_LIST = [1974906693]   # 黑名单，权限为 BLACK = -999
WHITE_LIST = []             # 白名单，权限为 WHITE = 51
SUPERUSERS = [3347977962]        # 填写超级用户的QQ号，可填多个用半角逗号","隔开，权限为 SUPERUSER = 999

PYS = {3347977962,1459758033}

NICKNAME = r'凯留|凯露|at,qq=1784559591'          # 机器人的昵称。呼叫昵称等同于@bot，可用元组配置多个昵称

# IP = '106.52.140.45'                                      #修改为你的服务器ip,推荐修改
# public_address = '106.52.140.45:8080'                     #修改为你的服务器ip+端口,推荐修改
# PassWord = '12345678'


COMMAND_START = {''}        # 命令前缀（空字符串匹配任何消息）
COMMAND_SEP = set()         # 命令分隔符（hoshino不需要该特性，保持为set()即可）

# 发送图片的协议
# 可选 http, file, base64
# 当QQ客户端与bot端不在同一台计算机时，可用http协议
RES_PROTOCOL = 'file'
# 资源库文件夹，需可读可写，windows下注意反斜杠转义
RES_DIR = r'./res/'
# 使用http协议时需填写，原则上该url应指向RES_DIR目录
RES_URL = 'http://127.0.0.1:5000/static/'

'''
启用的模块
初次尝试部署时请先保持默认
如欲启用新模块，请认真阅读部署说明，逐个启用逐个配置
切忌一次性开启多个
'''


MODULES_ON = {
    # 'botmanage',
    # 'dice',
    # 'groupmaster', #群聊基础功能
    # 'hourcall', #报时功能
    # 'kancolle', #舰娘的远征
    # 'mikan', #蜜柑订阅番剧
    # 'pcrclanbattle',
    # 'priconne',
    # 'picfinder',
    # 'setu',
    # 'translate',
    # 'twitter-v2',
    # 'test',    #测试下看看




    # 'reload',#重启
    # 'hiumsentences',#网抑云语录
    # 'generator',#营销文生成等五个小功能
    # 'eqa',#问答功能2
    # 'fake_news',
    # 'russian',#俄罗斯轮盘赌
    # 'picapi',#自定义拉取图片
    #'bilisearchspider',#b站订阅,
    # 'image_generate',#取代原image
    # 'memberguess',#猜群友头像
    # 'portune',#运势插件
    # 'pcr_calendar',#全服务器通用日历表，关键词为日历
    # 'xcw',#数个插件的混合，需要xcw资源包配合链接：https://pan.baidu.com/s/1tb0skZTs8NSHYZ-Tm3Cs0w 提取码：2333
    # 'revgif',#GIF图倒放

    # 'whattoeat',
    # 'fucking_crazy_thursday',

    # 'daxuexi_HoshinoBot',
    # 'travelpolicy_HoshinoBot', #出行政策
    # 'pcr_calculator_plus',
    # 'dailynews',
    # 'yaowoyizhi',
    # 'dailywife',
    # 'custom',
    # 'pokemon_whois',
    # 'aoe4_watcher_bot',
    # 'aoe_test',
    'dailySum'


}
# version = 'hoshino_xcw_0.9'