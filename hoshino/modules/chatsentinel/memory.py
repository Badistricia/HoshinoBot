from collections import deque
import time
import re

class MemoryStore:
    def __init__(self, maxlen=500):
        self.history = deque(maxlen=maxlen)

    def add(self, sender: str, content: str):
        # Filter CQ codes and extra spaces
        # Remove [CQ:image,...], [CQ:face,...], etc.
        # Keep text content only.
        clean_content = re.sub(r'\[CQ:.*?\]', '', content)
        clean_content = clean_content.strip()
        
        # If content is empty after cleaning (e.g. only image), ignore?
        # User said "exclude CQ code and expressions", but maybe we should record "User sent an image"?
        # For context understanding, "User sent an image" might be better than silence.
        # But user specifically said "exclude". Let's stick to text.
        
        if not clean_content:
            return

        self.history.append({
            "timestamp": time.time(),
            "sender": sender,
            "content": clean_content
        })

    def get_full_context_str(self, limit=50) -> str:
        # Limit the number of messages returned for generating reply
        # even if we store 500. Sending 500 messages to LLM might be too expensive/long.
        # But user wants "context keep 500". 
        # For "Responder", maybe we still use 50 or 100?
        # For "aichat" context injection, we might use more.
        # Let's make it configurable.
        
        # Get last N messages
        msgs = list(self.history)[-limit:]
        
        lines = []
        for msg in msgs:
            # Format: UserA: Message content
            lines.append(f"{msg['sender']}: {msg['content']}")
        return "\n".join(lines)

    def get_recent_messages(self, count=20):
        return list(self.history)[-count:]
