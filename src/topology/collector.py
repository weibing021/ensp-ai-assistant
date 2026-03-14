"""设备信息采集器""" 
import logging 
from typing import List, Dict, Any, Optional 
from ..connection.device_manager import DeviceManager 

logger = logging.getLogger(__name__) 

class InfoCollector: 
    """从设备采集原始信息""" 
    
    def __init__(self, device_manager: DeviceManager, topology_config: Optional[Dict[str, Any]] = None): 
        self.dm = device_manager 
        self.topology_config = topology_config or {}
        
    def collect_all(self, device_names: List[str]) -> Dict[str, Dict[str, str]]: 
        """采集所有指定设备的信息""" 
        commands = self._get_collection_commands()
        # 如果 DeviceManager 支持批量接口，优先使用并发采集
        if hasattr(self.dm, "execute_batch"):
            batch_results = self.dm.execute_batch(
                device_names=device_names,
                commands=commands,
                is_config=False,
            )
            return batch_results

        # 回退到逐设备串行采集
        results: Dict[str, Dict[str, str]] = {} 
        for name in device_names: 
            device_data: Dict[str, str] = {} 
            for cmd in commands: 
                output = self.dm.execute_command(name, cmd) 
                if output is not None: 
                    device_data[cmd] = output 
                else: 
                    logger.warning(f"Failed to execute {cmd} on {name}") 
            results[name] = device_data 
        return results 
    
    def _get_collection_commands(self) -> List[str]: 
        """获取要采集的命令列表（可从配置文件读取）""" 
        # 优先从拓扑配置中读取拓扑发现命令
        commands = self.topology_config.get('commands')
        if commands:
            return commands
        
        # 默认命令列表
        return [ 
            "display interface brief", 
            "display ip interface brief", 
            "display arp", 
            "display mac-address", 
            "display lldp neighbor brief", 
            "display current-configuration | include sysname" 
        ]
