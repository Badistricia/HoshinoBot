"""
Gemini API客户端
用于生成带完整HTML样式的日报/周报
"""
import httpx
import asyncio
import re
from .logger_helper import log_info, log_debug, log_warning, log_error_msg

class GeminiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        self.headers = {
            "Content-Type": "application/json"
        }
        log_info(f"GeminiClient 初始化完成，API Key: {'已设置' if api_key else '未设置'}")
    
    async def generate_html(self, prompt, max_retries=3, timeout=120.0):
        """
        生成完整的HTML内容
        :param prompt: 提示词
        :param max_retries: 最大重试次数
        :param timeout: 超时时间
        :return: HTML内容字符串
        """
        log_info(f"开始调用Gemini生成HTML报告")
        log_debug(f"提示词: {prompt[:200]}...")
        
        # 记录请求数据大小
        request_size = len(prompt.encode('utf-8'))
        log_info(f"请求数据大小: {request_size / 1024:.2f} KB")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                log_debug(f"尝试API请求 (尝试 {retry_count + 1}/{max_retries})...")
                
                # Gemini API使用URL参数传递API Key
                url = f"{self.base_url}?key={self.api_key}"
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers=self.headers,
                        json={
                            "contents": [{
                                "parts": [{
                                    "text": prompt
                                }]
                            }],
                            "generationConfig": {
                                "temperature": 1.0,
                                "topK": 40,
                                "topP": 0.95,
                                "maxOutputTokens": 8192,
                            }
                        },
                        timeout=timeout
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Gemini返回格式: candidates[0].content.parts[0].text
                    if "candidates" in result and len(result["candidates"]) > 0:
                        candidate = result["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            content = candidate["content"]["parts"][0]["text"]
                            
                            # 提取HTML内容（可能包含在markdown代码块中）
                            html_content = self._extract_html(content)
                            
                            if html_content:
                                log_info(f"Gemini生成成功，HTML长度: {len(html_content)}")
                                log_debug(f"HTML前200字符: {html_content[:200]}...")
                                return html_content
                            else:
                                log_warning("未能从返回内容中提取有效HTML")
                                return None
                    else:
                        log_error_msg(f"Gemini API返回格式异常: {result}")
                        return None
                
                elif response.status_code == 429:
                    # 速率限制，等待更长时间后重试
                    wait_time = min(5 * (retry_count + 1), 30)  # 最多等待30秒
                    log_warning(f"Gemini API速率限制，等待{wait_time}秒后重试")
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                
                elif response.status_code == 400:
                    # 请求参数错误
                    error_data = response.json()
                    log_error_msg(f"Gemini API请求参数错误: {error_data}")
                    
                    # 如果是内容过长，尝试减少
                    if "INVALID_ARGUMENT" in str(error_data):
                        log_warning("请求内容可能过长，尝试减少输入大小")
                        prompt_parts = prompt.split("聊天记录：\n")
                        if len(prompt_parts) == 2:
                            instruction, chat_log = prompt_parts
                            # 保留前70%的聊天记录
                            reduced_chat_log = chat_log[:int(len(chat_log) * 0.7)]
                            prompt = f"{instruction}聊天记录：\n{reduced_chat_log}\n\n[注: 由于长度限制，仅显示部分聊天记录]"
                            log_info(f"提示词已减少到原来的70%，新大小: {len(prompt.encode('utf-8')) / 1024:.2f} KB")
                            retry_count += 1
                        else:
                            log_error_msg("无法裁剪提示词，格式不符合预期")
                            return None
                    else:
                        return None
                
                else:
                    log_error_msg(f"Gemini API调用失败: {response.status_code} {response.text}")
                    retry_count += 1
                    await asyncio.sleep(2)
            
            except httpx.TimeoutException:
                log_warning(f"Gemini API请求超时，尝试重试 ({retry_count + 1}/{max_retries})")
                retry_count += 1
                await asyncio.sleep(2)
            
            except Exception as e:
                log_error_msg(f"Gemini API调用出错: {str(e)}")
                import traceback
                log_error_msg(traceback.format_exc())
                retry_count += 1
                await asyncio.sleep(2)
        
        log_error_msg(f"达到最大重试次数 ({max_retries})，Gemini生成失败")
        return None
    
    def _extract_html(self, content):
        """
        从返回内容中提取HTML代码
        处理可能的markdown代码块包裹
        """
        # 尝试提取markdown代码块中的HTML
        html_pattern = r'```html\s*(.*?)\s*```'
        match = re.search(html_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            log_info("从markdown代码块中提取HTML")
            return match.group(1).strip()
        
        # 尝试提取普通代码块
        code_pattern = r'```\s*(.*?)\s*```'
        match = re.search(code_pattern, content, re.DOTALL)
        if match:
            potential_html = match.group(1).strip()
            # 检查是否是HTML（包含DOCTYPE或html标签）
            if '<!DOCTYPE' in potential_html or '<html' in potential_html.lower():
                log_info("从普通代码块中提取HTML")
                return potential_html
        
        # 如果内容本身就是HTML（包含DOCTYPE或html标签）
        if '<!DOCTYPE' in content or '<html' in content.lower():
            log_info("内容本身就是HTML")
            return content.strip()
        
        # 都不是，返回None
        log_warning("未能识别出有效的HTML内容")
        return None
