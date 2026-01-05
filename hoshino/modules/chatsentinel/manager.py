from .memory import MemoryStore
from .guard import TrafficGuard
from . import config

class GroupInstance:
    def __init__(self):
        self.memory = MemoryStore(maxlen=config.HISTORY_LEN)
        self.guard = TrafficGuard()
        self.enabled = False 

# Shared components
# We keep instances here so it can be imported by other modules
instances = {}

def get_instance(group_id) -> GroupInstance:
    if group_id not in instances:
        instances[group_id] = GroupInstance()
    return instances[group_id]
