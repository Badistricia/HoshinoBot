import os

# API Configuration
# 用户指定的 Key
JUDGE_API_KEY = "AIzaSyCVSAMizJh6qwtLU_x68JW7PXO8il2cDJ8"

# Responder 现在委托给 aichat 模块，所以这里的 RESPONDER_API_KEY 不再使用
# 但为了兼容性保留定义，或者用于备用
RESPONDER_API_KEY = JUDGE_API_KEY

# Models
# Judge Model (判官): 用于低成本快速判断
JUDGE_MODEL_NAME = "gemini-2.5-flash"


# System Constants
BATCH_SIZE = 4
BATCH_TIMEOUT = 15.0 # Seconds
DAILY_LIMIT = 1450
HISTORY_LEN = 50

# Proxy Configuration (Optional)
# Example: "http://127.0.0.1:7890"
PROXY_URL = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
