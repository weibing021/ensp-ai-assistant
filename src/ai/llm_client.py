"""LLM客户端封装，支持 OpenAI / 兼容接口 和 本地模型""" 
import os 
from typing import Any, Dict 
from langchain_openai import ChatOpenAI 
from langchain_community.llms import Ollama 


class LLMClient: 
    """统一的LLM调用接口""" 
    
    def __init__(self, config: Dict[str, Any]): 
        self.config = config 
        provider = config.get('provider', 'openai') 
        model = config.get('model', 'gpt-3.5-turbo') 
        temperature = config.get('temperature', 0.2) 
        max_tokens = config.get('max_tokens', 1000) 
        base_url = config.get('base_url') or None
        api_key_env = config.get('api_key_env', 'OPENAI_API_KEY')
        api_key = os.getenv(api_key_env, "")
        
        if provider in ('openai', 'openai_compatible'): 
            # 对于 openai_compatible，通常需要配置自定义 base_url
            self.llm = ChatOpenAI( 
                model=model, 
                temperature=temperature, 
                max_tokens=max_tokens, 
                api_key=api_key,
                base_url=base_url,
            ) 
        elif provider == 'local': 
            # 本地大模型（例如 Ollama）
            self.llm = Ollama(model=model, temperature=temperature) 
        else: 
            raise ValueError(f"Unsupported LLM provider: {provider}") 
    
    def invoke(self, prompt: str, **kwargs) -> str: 
        """调用LLM并返回文本结果""" 
        response = self.llm.invoke(prompt, **kwargs) 
        
        if hasattr(response, 'content'):
            return str(response.content)
        return str(response)
