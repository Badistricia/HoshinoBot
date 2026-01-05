import os

# API Configuration
# Use DeepSeek API Key
JUDGE_API_KEY = "sk-94a61ab92c414de58af7e7cbf9d73cd7"
JUDGE_BASE_URL = "https://api.deepseek.com"

# Responder 现在委托给 aichat 模块，所以这里的 RESPONDER_API_KEY 不再使用
RESPONDER_API_KEY = JUDGE_API_KEY

# Models
# Judge Model (判官): 用于低成本快速判断
JUDGE_MODEL_NAME = "deepseek-chat"


# System Constants
BATCH_SIZE = 10
BATCH_TIMEOUT = 999999 # Disabled effectively, or unused
DAILY_LIMIT = 1450
HISTORY_LEN = 500

# Proxy Configuration (Optional)
# Example: "http://127.0.0.1:7890"
PROXY_URL = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
