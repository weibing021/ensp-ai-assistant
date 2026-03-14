"""配置命令生成器""" 
import json 
import logging 
from typing import List, Dict, Any 
from .llm_client import LLMClient 
from ..utils.prompt_loader import load_prompt 

logger = logging.getLogger(__name__) 

class CommandGenerator: 
    """根据结构化任务生成具体华为命令序列""" 
    
    def __init__(self, llm_client: LLMClient): 
        self.llm = llm_client 
        # 内置模板（简化版） 
        self.templates = { 
            "config_interface": self._gen_interface, 
            "config_ospf": self._gen_ospf, 
            "config_static_route": self._gen_static_route, 
        } 
    
    def generate(self, task: Dict[str, Any]) -> List[str]: 
        """为单个任务生成命令列表""" 
        action = task.get("action") 
        params = task.get("parameters", {}) 
        
        if action in self.templates: 
            return self.templates[action](params) 
        else: 
            # 未知操作，使用LLM生成 
            return self._generate_with_llm(task) 
    
    def _gen_interface(self, params: Dict) -> List[str]: 
        """生成接口配置命令""" 
        iface = params.get("interface") 
        ip = params.get("ip") 
        mask = params.get("mask") 
        # 掩码转换 
        if mask and str(mask).isdigit(): 
            mask = self._prefix_to_netmask(int(mask)) 
        
        commands = ["system-view", f"interface {iface}"] 
        if ip and mask: 
            commands.append(f"ip address {ip} {mask}") 
        commands.append("quit") 
        return commands 
    
    def _gen_ospf(self, params: Dict) -> List[str]: 
        """生成OSPF配置命令""" 
        process = params.get("process", 1) 
        area = params.get("area", 0) 
        network = params.get("network") 
        wildcard = params.get("wildcard", "0.0.0.255") 
        
        commands = ["system-view", f"ospf {process}"] 
        if network: 
            commands.append(f"area {area}") 
            commands.append(f"network {network} {wildcard}") 
        commands.append("quit") 
        return commands 
    
    def _gen_static_route(self, params: Dict) -> List[str]: 
        """生成静态路由命令""" 
        dest = params.get("destination") 
        mask = params.get("mask") 
        next_hop = params.get("next_hop") 
        if mask and str(mask).isdigit(): 
            mask = self._prefix_to_netmask(int(mask)) 
        commands = ["system-view", f"ip route-static {dest} {mask} {next_hop}"] 
        return commands 
    
    def _generate_with_llm(self, task: Dict) -> List[str]: 
        """调用LLM生成未知类型的命令""" 
        try:
            prompt_template = load_prompt("command_gen.txt") 
            # 兼容旧模板的变量名，或者直接传递整个 task
            prompt = prompt_template.format(
                intent=task.get("action"),
                target_devices=task.get("target_devices", []),
                parameters=task.get("parameters", {}),
                topology_context=task.get("context", "")
            ) 
            response = self.llm.invoke(prompt) 
            # 尝试解析返回的命令列表 
            return self._parse_command_list(response) 
        except Exception as e:
            logger.error(f"LLM command generation failed: {e}")
            return []
    
    def _prefix_to_netmask(self, prefix: int) -> str: 
        """将前缀长度转换为点分十进制掩码""" 
        mask = (0xffffffff << (32 - prefix)) & 0xffffffff 
        return f"{(mask >> 24) & 0xff}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}" 
    
    def _parse_command_list(self, text: str) -> List[str]: 
        """从LLM回复中提取命令列表""" 
        lines = text.strip().split('\n') 
        commands = [] 
        for line in lines: 
            line = line.strip() 
            # 过滤掉注释、Markdown 标记和空行
            if line and not line.startswith(('#', '//', '```', '!', '*')): 
                commands.append(line) 
        return commands
