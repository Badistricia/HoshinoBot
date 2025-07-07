import requests
import json
import time

# HoshinoBot监听的地址和端口
HOSHINO_API_URL = "http://127.0.0.1:8080"

def send_group_message(message: str, group_id: int, user_id: int):
    """
    模拟发送一条群聊消息给HoshinoBot
    """
    event = {
        "post_type": "message",
        "message_type": "group",
        "time": int(time.time()),
        "self_id": 10000, # 机器人QQ号 (可随意)
        "sub_type": "normal",
        "user_id": user_id,
        "message_id": -12345, # 消息ID (可随意)
        "message": message,
        "raw_message": message,
        "font": 0,
        "sender": {
            "user_id": user_id,
            "nickname": f"测试用户{user_id}",
            "card": "本地测试",
            "role": "member",
        },
        "group_id": group_id,
    }

    try:
        response = requests.post(HOSHINO_API_URL, json=event, timeout=5)
        response.raise_for_status() # 如果请求失败 (非2xx状态码) 则抛出异常
        print(f"成功发送事件到 {HOSHINO_API_URL}")
        print(f"  - 群号: {group_id}")
        print(f"  - 用户: {user_id}")
        print(f"  - 消息: '{message}'")
        # HoshinoBot通常不返回内容，或返回空的204 No Content
        print(f"  - 响应状态码: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"发送事件失败: {e}")

if __name__ == "__main__":
    # --- 在这里修改你要测试的指令 ---
    
    # 示例1：在群987654321中，由用户12345678发送"日报"
    send_group_message(message="日报", group_id=987654321, user_id=12345678)

    print("-" * 20)

    # 示例2：在群111222333中，由用户87654321发送"昨日日报"
    send_group_message(message="昨日日报", group_id=111222333, user_id=87654321)