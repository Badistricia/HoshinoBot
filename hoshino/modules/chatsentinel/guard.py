import time
from typing import List
from . import config

class TrafficGuard:
    def __init__(self):
        self.pending_buffer: List[str] = []
        self.last_msg_time = time.time()
        self.daily_usage = 0
        self.last_reset_day = time.localtime().tm_yday
        self.cooldown_until = 0

    def _check_reset_daily(self):
        current_day = time.localtime().tm_yday
        if current_day != self.last_reset_day:
            self.daily_usage = 0
            self.last_reset_day = current_day

    def add_to_buffer(self, msg: str) -> bool:
        """
        Returns True if added, False if filtered.
        """
        # Update time even if filtered? No, usually update time on valid activity.
        # But for timeout, we want to know when the last message was received.
        self.last_msg_time = time.time()

        # Filter rules
        if len(msg) < 2:
            return False
        if msg.startswith(('/', '#', '!', '！')): # Common command prefixes
            return False
        # Simple deduplication (check last in buffer)
        if self.pending_buffer and self.pending_buffer[-1] == msg:
            return False
        
        self.pending_buffer.append(msg)
        return True

    def should_trigger(self) -> bool:
        self._check_reset_daily()
        
        if self.daily_usage >= config.DAILY_LIMIT:
            return False
            
        if time.time() < self.cooldown_until:
            return False

        if not self.pending_buffer:
            return False

        # Condition 1: Buffer full
        if len(self.pending_buffer) >= config.BATCH_SIZE:
            return True
            
        # Condition 2: Timeout (Processing cold starts)
        # Note: This logic works if called periodically or on new message
        if len(self.pending_buffer) > 0 and (time.time() - self.last_msg_time > config.BATCH_TIMEOUT):
            return True
            
        return False

    def pop_buffer(self) -> str:
        content = "\n".join(self.pending_buffer)
        self.pending_buffer.clear()
        self.increment_usage()
        return content
        
    def increment_usage(self):
        self.daily_usage += 1

    def set_cooldown(self, seconds):
        self.cooldown_until = time.time() + seconds
