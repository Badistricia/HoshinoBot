from .client import GeminiClient
from . import config
import logging

logger = logging.getLogger("hoshino.chatsentinel.judge")

class TheJudge:
    def __init__(self):
        self.client = GeminiClient(config.JUDGE_API_KEY, config.JUDGE_MODEL_NAME)
        
    async def check(self, messages_str: str) -> bool:
        logger.info(f"Judging messages:\n{messages_str}")
        prompt = f"""
你是一个群聊话题筛选器。请阅读以下几条最新的群聊消息：
{messages_str}

判断依据：
1. 任何带有“bot”、“机器人”、“你”等指向性词语的，必须判定为 YES。
2. 任何疑问句，如果是向群友或机器人提问的，判定为 YES。
3. 任何有趣、吐槽、争议性话题，判定为 YES。
4. 只有纯粹的无意义刷屏、表情包、打卡才回复 NO。

如果值得机器人介入，请回复 "YES"；如果是无聊的闲聊，回复 "NO"。
只输出 YES 或 NO。
"""
        # Call API
        response = await self.client.generate(prompt)
        
        # Parse result
        clean_resp = response.strip().upper()
        logger.info(f"Judge Decision: {clean_resp}")
        
        return "YES" in clean_resp
