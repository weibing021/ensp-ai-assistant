"""自然语言意图解析模块""" 
import json 
import logging 
from typing import List, Dict, Any 
from .llm_client import LLMClient 
from ..utils.prompt_loader import load_prompt 

logger = logging.getLogger(__name__) 

class IntentParser: 
    """将用户自然语言指令解析为结构化任务列表""" 
    
    def __init__(self, llm_client: LLMClient, topology_context: str = ""): 
        self.llm = llm_client 
        self.topology_context = topology_context 
        
    def parse(self, user_input: str) -> List[Dict[str, Any]]: 
        """解析指令，返回任务列表""" 
        try:
            prompt_template = load_prompt("intent_parser.txt") 
            prompt = prompt_template.format( 
                topology_context=self.topology_context, 
                user_input=user_input 
            ) 
            
            response = self.llm.invoke(prompt) 
            # 提取 JSON 
            tasks = self._extract_json(response) 
            logger.info(f"Parsed tasks: {tasks}") 
            return tasks 
        except Exception as e: 
            logger.error(f"Intent parsing failed: {e}") 
            return [] 
    
    def _extract_json(self, text: str) -> List[Dict]: 
        """从 LLM 回复中提取 JSON 数组""" 
        # 尝试找到第一个 [ 和最后一个 ] 之间的内容 
        start = text.find('[') 
        end = text.rfind(']') + 1 
        if start != -1 and end > start: 
            json_str = text[start:end] 
            try: 
                return json.loads(json_str) 
            except json.JSONDecodeError: 
                logger.warning(f"Invalid JSON: {json_str}") 
        return []
