from .client import APIClient
from . import config
import logging

logger = logging.getLogger("hoshino.chatsentinel.judge")

class TheJudge:
    def __init__(self):
        self.client = APIClient(
            api_key=config.JUDGE_API_KEY, 
            model_name=config.JUDGE_MODEL_NAME,
            base_url=config.JUDGE_BASE_URL
        )
        
    async def check(self, messages_str: str) -> bool:
        logger.info(f"Judging messages (Context + New):\n{messages_str}")
        prompt = f"""
你是一个群聊话题筛选器。以下是最近的群聊记录（包含上下文）：
{messages_str}

请判断当前的话题进展是否值得机器人（你）介入。
判断依据：
1. 最近的消息中如果有“bot”、“机器人”、“你”等指向性词语，必须判定为 YES。
2. 最近的消息中如果有向群友或机器人提问的疑问句，判定为 YES。
3. 当前正在进行有趣、吐槽、争议性话题，且适合插嘴，判定为 YES。
4. 只有纯粹的无意义刷屏、表情包、打卡，或者话题已经结束，才回复 NO。

如果值得机器人介入，请回复 "YES"；否则回复 "NO"。
只输出 YES 或 NO。
"""
        # Call API
        response = await self.client.generate(prompt)
        
        # Parse result
        clean_resp = response.strip().upper()
        logger.info(f"Judge Decision: {clean_resp}")
        
        return "YES" in clean_resp
