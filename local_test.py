import sys
import asyncio
import logging
import os
from unittest.mock import MagicMock, AsyncMock
from types import ModuleType
import time
import json

# --- 1. Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TEST")

# --- 2. Mocking Dependencies ---

# Mock 'openai' before importing modules that use it
mock_openai = ModuleType("openai")
sys.modules["openai"] = mock_openai
mock_openai.AsyncOpenAI = MagicMock()
# Setup the client instance returned by AsyncOpenAI()
mock_openai_client = MagicMock()
mock_openai.AsyncOpenAI.return_value = mock_openai_client
# Setup chat.completions.create
async def mock_judge_create(**kwargs):
    # Simulate Judge response
    # Return a mock object with choices[0].message.content
    logger.info(f"⚖️ [Judge Mock] Received request with {len(kwargs.get('messages', []))} messages")
    return MagicMock(choices=[MagicMock(message=MagicMock(content="YES"))])

mock_openai_client.chat.completions.create = mock_judge_create

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
            if not hasattr(self, 'handlers'):
                self.handlers = []
            self.handlers.append(func)
            return func
        return decorator

    def on_fullmatch(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def scheduled_job(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

hoshino.Service = MockService
hoshino.priv = MagicMock()
hoshino.priv.check_priv.return_value = True
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
    def __init__(self):
        self.config = MagicMock()
        self.config.self_id = 123456

    async def send_group_msg(self, group_id, message):
        logger.info(f"🤖 [BOT SEND] Group {group_id}: {message}")
    
    async def send(self, ev, message):
        logger.info(f"🤖 [BOT REPLY] {message}")

    async def finish(self, ev, message):
        logger.info(f"🤖 [BOT FINISH] {message}")

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
# We need to mock 'generate_response' or similar if Responder uses it
# Wait, Responder in chatsentinel calls 'aichat_client.chat.completions.create' or similar?
# Let's check responder.py. 
# It likely imports client_manager from aichat.

mock_client_manager = MagicMock()
mock_aichat.client_manager = mock_client_manager
mock_aichat.config_manager = MagicMock()
mock_aichat.conversation_manager = MagicMock()

mock_responder_client = MagicMock()
mock_client_manager.get_client.return_value = mock_responder_client

async def mock_responder_create(**kwargs):
    messages = kwargs.get('messages', [])
    logger.info(f"🗣️ [Responder Mock] Generating reply for context length: {len(messages)}")
    return MagicMock(choices=[MagicMock(message=MagicMock(content="这是模拟的回复喵！(Responder Working)"))])

mock_responder_client.chat.completions.create = mock_responder_create

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
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Override config constants for faster testing
# config.BATCH_SIZE = 10
# config.BATCH_TIMEOUT = 99999.0

# --- 4. Interactive Test Loop ---
async def main():
    print("\n🚀 ChatSentinel Local Test Started!")
    print(f"🔧 Config: Batch Size={config.BATCH_SIZE}, Timeout={config.BATCH_TIMEOUT}s")
    print(f"🔧 Judge Model: {config.JUDGE_MODEL_NAME}")
    print("💡 Type a message and press Enter. Type 'exit' to quit.")

    bot = MockBot()
    group_id = 1001
    user_id = 101
    
    # Initialize instance
    inst = get_instance(group_id)
    inst.enabled = True # Force enable for testing

    print(f"✅ Instance for Group {group_id} initialized. Enabled: {inst.enabled}")

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

        # Manually trigger timeout check if needed (or just rely on batch size logic inside handle_msg)
        # handle_msg calls execute_logic if buffer full.
        # But for timeout, we normally rely on scheduler.
        # Here we can force check if buffer > 0
        if buffer_len > 0 and buffer_len < config.BATCH_SIZE:
             print("   [System] Waiting for more messages...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
