from hoshino.modules.aichat import config_manager, client_manager, conversation_manager
from hoshino import logger

class Responder:
    def __init__(self):
        pass

    async def generate(self, group_id: str, full_history: str) -> str:
        # 1. Get Group Config
        group_id = str(group_id)
        config = config_manager.get_config(group_id)
        if not config:
            # Use default if not configured (defaulting to deepseek as per aichat logic)
            config = config_manager.apply_default_settings({}, 'deepseek')
            config['model'] = 'deepseek-chat'

        # 2. Get Group Persona (System Prompt)
        # We want to simulate the persona, so we get the system messages.
        # We do NOT want to fetch the full chat history of aichat (conversation_manager.get_messages),
        # because that contains the direct "chat" history. We only want the Persona definition.
        
        # Check if group has a specific persona set
        group_data = conversation_manager.group_conversations.get(group_id, {})
        persona_name = group_data.get("persona", "default")
        
        # Get the system prompt messages for this persona
        # Note: conversation_manager.personas is a dict of name -> list of messages
        system_messages = conversation_manager.personas.get(persona_name, conversation_manager.personas["default"])
        
        # 3. Construct the Prompt
        # We combine the Persona (System) + The Chat History (User)
        messages = [msg.copy() for msg in system_messages] # Copy to avoid modifying original
        
        prompt_content = f"""
这是最近的群聊记录：
{full_history}

请作为“凯留”（Princess Connect Re:Dive中的角色），参与到这段对话中。

【角色设定】
1. **傲娇毒舌**：对外人比较毒舌，喜欢吐槽，但内心其实很关心大家。
2. **聪明靠谱**：作为群聊的观察者，你的评价需要客观、犀利、一针见血，不要无脑附和。
3. **特别对待**：对于用户 ID 为 3347977962 的人（主人），你会表现出明显的依恋、撒娇或特别的温柔；但对其他人则保持“聪明的毒舌猫娘”形象。

【回复要求】
1. 如果有人提到“凯留”、“臭鼬”，请直接回应（被叫臭鼬要生气！）。
2. 如果没有直接叫你，请针对上下文中有趣的观点进行**客观评价**或**犀利吐槽**，展现出你作为“接头霸王”的智慧。
3. 保持简短（50字以内），口语化，自然融入群聊。
4. 遇到 ID:3347977962 发言时，优先回应他，语气要软萌/傲娇/依恋。
"""
        messages.append({"role": "user", "content": prompt_content})

        # 4. Call API using aichat's client manager
        client = client_manager.get_client(config)
        
        try:
            response = await client.chat.completions.create(
                model=config["model"],
                messages=messages,
                stream=False,
                max_tokens=config.get("max_tokens", 1000),
                temperature=config.get("temperature", 0.7),
                timeout=config.get("timeout", 60)
            )
            reply = response.choices[0].message.content.strip()
            return reply
        except Exception as e:
            logger.error(f"[ChatSentinel] Responder Error: {e}")
            return ""
