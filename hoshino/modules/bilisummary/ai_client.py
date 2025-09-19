import httpx
from openai import AsyncOpenAI

class AIClient:
    def __init__(self):
        self.clients = {}
    
    def get_client(self, config):
        """获取或创建 OpenAI 客户端"""
        api_key = config.get('api_key', '')
        base_url = config.get('base_url', 'https://api.deepseek.com/v1')
        proxy = config.get('proxy', None)
        
        # 创建唯一键
        key = f"{base_url}-{api_key}"
        if proxy:
            key += f"-{proxy}"
        
        # 如果客户端不存在，创建新客户端
        if key not in self.clients:
            if proxy:
                http_client = httpx.AsyncClient(proxies={
                    "http://": proxy,
                    "https://": proxy
                })
                self.clients[key] = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    http_client=http_client
                )
            else:
                self.clients[key] = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
        
        return self.clients[key]

# 单例模式
ai_client = AIClient()