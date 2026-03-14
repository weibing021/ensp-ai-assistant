"""配置执行器""" 
import logging 
from typing import List, Dict, Any 
from ..connection.device_manager import DeviceManager 
from ..ai.command_gen import CommandGenerator 

logger = logging.getLogger(__name__) 

class ConfigExecutor: 
    """执行配置任务""" 
    
    def __init__(self, device_manager: DeviceManager, command_gen: CommandGenerator): 
        self.dm = device_manager 
        self.cmd_gen = command_gen 
        
    def execute_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]: 
        """执行任务列表，返回每个设备的结果""" 
        results = {} 
        # 按设备分组任务 
        device_tasks = {} 
        for task in tasks: 
            # 兼容字段名 device 或 target_device
            device = task.get("device") or task.get("target_device")
            if not device:
                logger.warning(f"Task skipped: No target device specified in {task}")
                continue
            if device not in device_tasks: 
                device_tasks[device] = [] 
            device_tasks[device].append(task) 
        
        # 为每个设备生成并执行命令 
        for device, task_list in device_tasks.items(): 
            device_results = [] 
            all_success = True 
            
            for task in task_list: 
                commands = self.cmd_gen.generate(task) 
                if commands: 
                    logger.info(f"Executing on {device}: {commands}") 
                    ok = self.dm.execute_config_commands(device, commands) 
                    device_results.append({ 
                        "task": task, 
                        "commands": commands, 
                        "success": ok 
                    }) 
                    if not ok: 
                        all_success = False 
                        logger.error(f"Execution failed on {device} for task: {task}")
                        break  # 失败后停止该设备后续配置
                else: 
                    device_results.append({ 
                        "task": task, 
                        "commands": [], 
                        "success": False, 
                        "error": "No commands generated" 
                    }) 
                    all_success = False 
                    logger.error(f"Command generation failed for task on {device}: {task}")
            
            results[device] = { 
                "success": all_success, 
                "tasks": device_results 
            } 
        
        return results

    def execute_raw_commands(self, device: str, commands: List[str]) -> bool:
        """直接下发原始命令列表"""
        return self.dm.execute_config_commands(device, commands)
