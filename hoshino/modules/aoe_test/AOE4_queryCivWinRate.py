import json

import requests
from logging import getLogger
import matplotlib.pyplot as plt
from PIL import Image

from matplotlib.offsetbox import OffsetImage, AnnotationBbox


proxies = {"http": "", "https": ""}
logger = getLogger(__name__)
session = requests.session()

request_header = {'User-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36'}


# 一个方法 获取民族整体胜率 参数是param，默认是当前赛季最新赛季
async def queryCivWinRate(text: str) -> str:
    """ Tries to find a player based on a text containing either name, steam_id or profile_id
    Returns the player name and rank if found, otherwise returns None"""


    try:

        url = f"https://aoe4world.com/api/v0/stats/rm_solo/civilizations?patch=10257&rating{text}"
        logger.info(url)
        resp = json.loads(session.get(url).text)
        if(resp.get("error")):
            return resp.get("error")

        logger.info(f"resp: {resp}")

        civDataList:list = resp.get("data")

        civDataList.sort(key=lambda x: x['win_rate'], reverse=False)

        # 创建一个新的图形
        fig, ax = plt.subplots()
        fig.set_size_inches(14, 9)

        bar_width = 0.5  # 柱状宽度

        # 设置Y轴标签和头像
        for i, data in enumerate(civDataList):
            img = Image.open('hoshino/modules/aoe_test/resource/' + data['civilization'] + '.png')
            imagebox = OffsetImage(img, zoom=0.2)
            ab = AnnotationBbox(imagebox, (60, i), frameon=False)
            ax.add_artist(ab)

        ax.set_yticks(range(len(civDataList)))
        ax.set_yticklabels([data['civilization'] for data in civDataList])

        # 绘制胜率柱
        for i, data in enumerate(civDataList):
            win_rate = data['win_rate']
            ax.barh(i + bar_width / 2, win_rate, color='green', height=bar_width)
            ax.text(win_rate / 2, i + bar_width / 2, f'{win_rate:.2f}%', va='center',ha='center')

        # 绘制挑选率柱
        for i, data in enumerate(civDataList):
            pick_rate = data['pick_rate']
            ax.barh(i - bar_width / 2, pick_rate, color='blue', height=bar_width)
            ax.text(pick_rate + 5, i - bar_width / 2, f'{pick_rate:.2f}%', va='center',ha='center')

        # 设置X轴范围和标签
        ax.set_xlim(0, 65)
        ax.set_xlabel('Rate')

        # 设置标题
        ax.set_title('Top 10 Civilizations Win Rate and Pick Rate Comparison')

        width = 0.35  # the width of the bars
        plt.plot(2, 3, label='Win Rate: Green\nPick Rate: Blue', color='black')
        # ax.bar_label(rects, padding=3)
        fig.suptitle(f"ELO{text}", fontsize=20)

        plt.legend(loc='best')  # 图列位置，可选best，center等


        logger.info("保存图片")
        plt.savefig('top_10_civ_win_rate.png')
        return fig
    except Exception:
        logger.exception("请求数据的时候发生错误: %s", Exception)

