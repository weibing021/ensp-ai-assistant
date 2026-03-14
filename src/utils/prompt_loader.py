"""加载提示词模板文件""" 
import os 

PROMPT_DIR = os.path.join(os.path.dirname(__file__), '../../config/prompts') 

def load_prompt(name: str) -> str: 
    """从文件加载提示词模板""" 
    file_path = os.path.join(PROMPT_DIR, name) 
    try: 
        with open(file_path, 'r', encoding='utf-8') as f: 
            return f.read() 
    except FileNotFoundError: 
        # 返回默认提示词 
        return _default_prompt(name) 

def _default_prompt(name: str) -> str: 
    """默认提示词（用于测试）""" 
    prompts = { 
        "intent_parser.txt": """你是一个网络配置助手。请将用户指令解析为JSON任务列表。 
拓扑上下文：{topology_context} 
用户指令：{user_input} 
输出JSON：""", 
        "command_gen.txt": """你是一个华为设备配置专家。根据任务生成配置命令。 
任务：{task} 
输出命令列表，每行一条：""", 
        "fault_diagnosis.txt": """你是一个网络故障专家。分析以下故障并提供建议。 
故障描述：{fault_description} 
设备输出：{device_outputs} 
输出JSON格式分析结果。""" 
    } 
    return prompts.get(name, "")
