import sys
import asyncio
import logging
import os
from unittest.mock import MagicMock, AsyncMock
from types import ModuleType
import time

# --- 1. Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TEST")

# --- 2. Mocking Hoshino & Nonebot ---

# Create fake 'hoshino' package
hoshino = ModuleType("hoshino")
sys.modules["hoshino"] = hoshino

# Mock Service
class MockService:
    def __init__(self, name, **kwargs):
        self.name = name
        self.logger = logging.getLogger(name)
        logger.info(f"🔹 Service '{name}' initialized.")
    
    def on_message(self, *args, **kwargs):
        def decorator(func):
            # Register the handler manually so we can call it
            if not hasattr(self, 'handlers'):
                self.handlers = []
            self.handlers.append(func)
            return func
        return decorator

    def scheduled_job(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    # Add other methods if needed
    def on_prefix(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

hoshino.Service = MockService
hoshino.priv = MagicMock()
hoshino.logger = logger

# Create fake 'hoshino.typing'
hoshino_typing = ModuleType("hoshino.typing")
sys.modules["hoshino.typing"] = hoshino_typing
hoshino.typing = hoshino_typing

class MockCQEvent:
    def __init__(self, group_id, user_id, message, sender_info=None):
        self.group_id = group_id
        self.user_id = user_id
        self.self_id = 123456
        self.message = message
        self.sender = sender_info or {'nickname': f'User{user_id}'}

hoshino_typing.CQEvent = MockCQEvent

# Create fake 'nonebot'
nonebot = ModuleType("nonebot")
sys.modules["nonebot"] = nonebot

class MockBot:
    async def send_group_msg(self, group_id, message):
        logger.info(f"🤖 [BOT SEND] Group {group_id}: {message}")
    
    def __getattr__(self, name):
        return MagicMock()

nonebot.get_bot = MagicMock(return_value=MockBot())

# Create fake 'hoshino.modules' package
hoshino_modules = ModuleType("hoshino.modules")
sys.modules["hoshino.modules"] = hoshino_modules
hoshino.modules = hoshino_modules

# Create fake 'hoshino.modules.aichat'
mock_aichat = ModuleType("hoshino.modules.aichat")
sys.modules["hoshino.modules.aichat"] = mock_aichat
hoshino_modules.aichat = mock_aichat

# Mock aichat components
mock_config_manager = MagicMock()
mock_aichat.config_manager = mock_config_manager
mock_config_manager.get_config.return_value = {
    "model": "mock-gpt",
    "api_key": "mock-key",
    "base_url": "mock-url",
    "temperature": 0.7
}
mock_config_manager.apply_default_settings.return_value = {
    "model": "mock-gpt"
}

import json

# aichat.conversation_manager
mock_conversation_manager = MagicMock()
mock_aichat.conversation_manager = mock_conversation_manager

# Load real personas
personas_path = os.path.join(os.getcwd(), 'hoshino', 'modules', 'aichat', 'personas.json')
try:
    with open(personas_path, 'r', encoding='utf-8') as f:
        real_personas = json.load(f)
    logger.info(f"✅ Loaded {len(real_personas)} personas from {personas_path}")
except Exception as e:
    logger.warning(f"⚠️ Failed to load personas: {e}, using mock data.")
    real_personas = {
        "default": [{"role": "system", "content": "你是一个AI助手"}],
        "喵喵机": [{"role": "system", "content": "你是凯留，一只猫娘，说话句尾要带喵。"}]
    }

mock_conversation_manager.personas = real_personas

# Mock persona data for our test group
mock_conversation_manager.group_conversations = {
    "1001": {"persona": "喵喵机"} # Default to catgirl for testing
}

mock_client_manager = MagicMock()
mock_aichat.client_manager = mock_client_manager
mock_client = MagicMock()
mock_client_manager.get_client.return_value = mock_client

async def mock_create(**kwargs):
    # Simulate network delay
    await asyncio.sleep(0.5)
    messages = kwargs.get('messages', [])
    user_prompt = messages[-1]['content'] if messages else ""
    logger.info(f"🔮 [Responder Logic] Context sent to AI:\n{user_prompt[:100]}...")
    return MagicMock(choices=[MagicMock(message=MagicMock(content="这是模拟的回复喵！(Responder Working)"))])

mock_client.chat.completions.create = mock_create

# --- 3. Import Target Module ---
# Add hoshino/modules to path so we can import 'chatsentinel' directly
modules_path = os.path.join(os.getcwd(), 'hoshino', 'modules')
sys.path.append(modules_path)

# Import chatsentinel
try:
    import chatsentinel
    from chatsentinel import handle_msg, execute_logic, get_instance, config
except ImportError as e:
    logger.error(f"Import failed: {e}")
    # Print full traceback for easier debugging
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Override config constants for faster testing
config.BATCH_SIZE = 2
config.BATCH_TIMEOUT = 5.0

# --- 4. Interactive Test Loop ---
async def main():
    print("\n🚀 ChatSentinel Local Test Started!")
    print(f"🔧 Config: Batch Size={config.BATCH_SIZE}, Timeout={config.BATCH_TIMEOUT}s")
    print("💡 Type a message and press Enter. Type 'exit' to quit.")
    print("   (Messages are accumulated. Default batch trigger is 2 messages)")

    bot = MockBot()
    group_id = 1001
    user_id = 101

    # Ensure handler is registered
    # Our MockService registers handlers in self.handlers
    # But chatsentinel uses 'sv' instance. We need to find that instance.
    # It is created in chatsentinel/__init__.py: sv = Service(...)
    # Since we imported chatsentinel, we can access it.
    service_instance = chatsentinel.sv
    if hasattr(service_instance, 'handlers'):
        print(f"✅ Handler registered: {service_instance.handlers}")
    else:
        print("⚠️ No handlers registered on Service!")

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(None, input, "\nYou > ")
        except EOFError:
            break
            
        if user_input.lower() in ['exit', 'quit']:
            break
            
        if not user_input.strip():
            continue

        # Simulate Event
        ev = MockCQEvent(group_id, user_id, user_input)
        
        # Call Handler
        await handle_msg(bot, ev)
        
        # Check internal state
        inst = get_instance(group_id)
        buffer_len = len(inst.guard.pending_buffer)
        print(f"   [System] Buffer: {buffer_len}/{config.BATCH_SIZE}, Last Msg Time: {inst.guard.last_msg_time}")

        # Manually trigger timeout check if needed (or just rely on batch size)
        if inst.guard.should_trigger():
            print("   [System] Triggering Check (Timeout/Manual)...")
            await execute_logic(bot, group_id, inst)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
