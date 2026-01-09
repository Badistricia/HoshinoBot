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

请判断当前的话题进展是否值得机器人（你，角色为“凯留”）介入。
判断依据：
1. 【高优先级】如果最近的消息中明确出现了“凯留”、“臭鼬”、“佩可”、“可可萝”等与你角色相关的关键词，或者有人在叫你，必须判定为 YES。
2. 【中优先级】如果当前群聊话题很有趣、值得吐槽、或者有争议性（例如讨论游戏、动画、生活琐事），且适合你以“凯留”的身份发表评论（吐槽或附和），判定为 YES。
3. 【低优先级】如果是无意义的刷屏、复读、打卡、单纯的表情包斗图，或者话题已经结束，请判定为 NO。

你的目标是让“凯留”自然地参与到群聊中，既能回应呼唤，也能在大家聊得开心时插嘴吐槽。

如果值得介入，请回复 "YES"；否则回复 "NO"。
只输出 YES 或 NO。
"""
        # Call API
        response = await self.client.generate(prompt)
        
        # Parse result
        clean_resp = response.strip().upper()
        logger.info(f"Judge Decision: {clean_resp}")
        
        return "YES" in clean_resp
