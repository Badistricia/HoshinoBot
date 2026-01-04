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

请根据你的人设（Persona），对最新话题进行点评或吐槽。
要求：
1. 必须完全符合你的人设语气。
2. 简短（50字以内）、自然。
3. 如果话题无聊，可以用你的人设风格表示不感兴趣。
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
