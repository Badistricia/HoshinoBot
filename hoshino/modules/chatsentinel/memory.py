from collections import deque
import time

class MemoryStore:
    def __init__(self, maxlen=50):
        self.history = deque(maxlen=maxlen)

    def add(self, sender: str, content: str):
        self.history.append({
            "timestamp": time.time(),
            "sender": sender,
            "content": content
        })

    def get_full_context_str(self) -> str:
        lines = []
        for msg in self.history:
            # Format: UserA: Message content
            lines.append(f"{msg['sender']}: {msg['content']}")
        return "\n".join(lines)

    def get_recent_messages(self, count=5):
        return list(self.history)[-count:]
