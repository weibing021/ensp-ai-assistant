"""测试验证模块""" 
import re 
import logging 
from typing import List, Dict, Any 
from ..connection.device_manager import DeviceManager 

logger = logging.getLogger(__name__) 

class Tester: 
    """执行测试命令并验证结果""" 
    
    def __init__(self, device_manager: DeviceManager): 
        self.dm = device_manager 
        
    def ping(self, device: str, target_ip: str, count: int = 4) -> Dict[str, Any]: 
        """执行 ping 测试""" 
        command = f"ping -c {count} {target_ip}" 
        output = self.dm.execute_command(device, command) 
        if output is None: 
            return {"success": False, "error": "Command failed"} 
        
        # 解析 ping 结果（简化） 
        loss_match = re.search(r"(\d+)% packet loss", output) 
        loss = int(loss_match.group(1)) if loss_match else 100 
        success = loss < 100 
        return { 
            "success": success, 
            "packet_loss": loss, 
            "output": output 
        } 
    
    def traceroute(self, device: str, target_ip: str) -> Dict[str, Any]: 
        """执行 traceroute""" 
        command = f"tracert {target_ip}"  # 华为命令为 tracert 
        output = self.dm.execute_command(device, command) 
        return {"output": output} if output else {"error": "Command failed"} 
    
    def verify_config(self, device: str, show_command: str, expected: str = None) -> Dict[str, Any]: 
        """执行 show 命令并可选验证预期内容""" 
        output = self.dm.execute_command(device, show_command) 
        if output is None: 
            return {"success": False, "error": "Command failed"} 
        
        if expected: 
            success = expected in output 
            return {"success": success, "output": output} 
        else: 
            return {"output": output}
