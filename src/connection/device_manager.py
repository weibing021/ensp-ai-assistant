"""设备连接管理模块""" 
import logging 
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any 
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler 
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException 
from .session_pool import SessionPool 

logger = logging.getLogger(__name__) 

class DeviceManager: 
    """管理所有网络设备的连接""" 
    
    def __init__(self, config: dict): 
        self.config = config 
        self.devices: Dict[str, dict] = {}  # name -> device info 
        self.sessions: Dict[str, Any] = {} 
        self.pool = SessionPool(max_size=config.get('pool_size', 10)) 
        
    def add_device(self, name: str, ip: str, port: int = 2000) -> bool: 
        """添加设备信息（eNSP 专用：默认免密 Telnet）""" 
        # eNSP 强制使用 generic_telnet 以跳过所有自动化登录探测
        device_type = 'generic_telnet'

        self.devices[name] = { 
            'name': name, 
            'ip': ip, 
            'port': port, 
            'device_type': device_type
        } 
        return True 
    
    def remove_device(self, name: str) -> bool: 
        """移除设备并断开连接""" 
        if name in self.sessions: 
            self.disconnect(name) 
        return self.devices.pop(name, None) is not None 
    
    def connect(self, name: str) -> Optional[Any]: 
        """建立设备连接""" 
        if name in self.sessions: 
            return self.sessions[name] 
        
        device_info = self.devices.get(name) 
        if not device_info: 
            logger.error(f"Device {name} not found") 
            return None 
        
        # 尝试从池中获取或新建连接 
        session = self.pool.get(name) 
        if session: 
            self.sessions[name] = session 
            return session 
        
        try: 
            # 处理会话日志路径
            session_log = self.config.get('session_log')
            if session_log:
                # 规范化路径并转为绝对路径
                session_log = os.path.abspath(os.path.normpath(session_log))
                # 如果是目录，则生成文件名
                if session_log.endswith('/') or session_log.endswith('\\') or os.path.isdir(session_log) or not os.path.splitext(session_log)[1]:
                    if not os.path.exists(session_log):
                        os.makedirs(session_log)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    session_log = os.path.join(session_log, f"{name}_{timestamp}.log")

            # 构建连接参数
            # eNSP 专用：使用 generic_telnet 彻底跳过认证
            conn_params = {
                'device_type': device_info['device_type'], 
                'ip': device_info['ip'], 
                'port': device_info['port'], 
                'timeout': self.config.get('timeout', 10), # 缩短超时，快速反馈
                'session_log': session_log,
            }
            
            logger.info(f"Attempting RAW Telnet connection to {device_info['ip']}:{device_info['port']}")
            
            connection = ConnectHandler(**conn_params) 
            
            # 关键：发送回车以唤醒 eNSP 终端提示符
            # 使用 write_channel 绕过 send_command 的提示符等待逻辑
            logger.info("Sending initial newline to wake up device...")
            connection.write_channel("\n")
            import time
            time.sleep(1) # 等待设备响应
            
            # 获取当前提示符
            prompt = connection.find_prompt()
            logger.info(f"Device woke up. Current prompt: {prompt}")
            
            self.sessions[name] = connection 
            self.pool.add(name, connection) 
            logger.info(f"Successfully connected to {name}") 
            return connection 
        except Exception as e: 
            error_msg = f"Failed to connect to {name}: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            # 记录更详细的排查建议
            if "TCP connection to device failed" in str(e):
                logger.error(f"Troubleshooting: Please check if eNSP device {name} is started and Serial Port {device_info['port']} is correct.")
            elif "Authentication failed" in str(e) or "Authentication Failed" in str(e):
                logger.error(f"Troubleshooting: Password/Username incorrect for {name}.")
            return None 
    
    def disconnect(self, name: str) -> bool: 
        """断开设备连接""" 
        if name in self.sessions: 
            try: 
                self.sessions[name].disconnect() 
            except Exception as e: 
                logger.warning(f"Error disconnecting {name}: {e}") 
            finally: 
                del self.sessions[name] 
                self.pool.remove(name) 
            return True 
        return False 
    
    def execute_command(self, name: str, command: str) -> Optional[str]: 
        """在设备上执行命令""" 
        conn = self.connect(name) 
        if not conn: 
            return None 
        try: 
            output = conn.send_command(command) 
            return output 
        except Exception as e: 
            logger.error(f"Command '{command}' on {name} failed: {e}") 
            return None 
    
    def execute_config_commands(self, name: str, commands: List[str]) -> bool: 
        """在设备上执行配置命令列表""" 
        conn = self.connect(name) 
        if not conn: 
            return False 
        try: 
            output = conn.send_config_set(commands) 
            logger.debug(f"Config result on {name}: {output}") 
            return True 
        except Exception as e: 
            logger.error(f"Config on {name} failed: {e}") 
            return False 
    
    def get_all_connected(self) -> List[str]: 
        """返回当前已连接的设备列表""" 
        return list(self.sessions.keys())

    def execute_commands(
        self,
        name: str,
        commands: List[str],
        is_config: bool = False
    ) -> Dict[str, Optional[str]]:
        """
        在单个设备上执行多条命令。
        is_config=True 时按配置命令处理（send_config_set），否则 send_command。
        返回 {command: output or None}
        """
        results: Dict[str, Optional[str]] = {}
        conn = self.connect(name)
        if not conn:
            return {cmd: None for cmd in commands}

        for cmd in commands:
            try:
                if is_config:
                    output = conn.send_config_set([cmd])
                else:
                    output = conn.send_command(cmd)
                results[cmd] = output
            except Exception as e:
                logger.error(f"Command '{cmd}' on {name} failed: {e}")
                results[cmd] = None

        return results

    def execute_batch(
        self,
        device_names: List[str],
        commands: List[str],
        is_config: bool = False,
        max_workers: int = 5,
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        在多台设备上并发执行多条命令。
        返回结构:
        {
            "R1": {"display ip interface brief": "...", ...},
            "R2": {...},
        }
        任一条失败则对应 value 为 None。
        """
        results: Dict[str, Dict[str, Optional[str]]] = {}

        def worker(dev_name: str) -> Dict[str, Optional[str]]:
            conn = self.connect(dev_name)
            if not conn:
                return {cmd: None for cmd in commands}

            dev_res: Dict[str, Optional[str]] = {}
            for cmd in commands:
                try:
                    if is_config:
                        output = conn.send_config_set([cmd])
                    else:
                        output = conn.send_command(cmd)
                    dev_res[cmd] = output
                except Exception as e:
                    logger.error(f"Command '{cmd}' on {dev_name} failed: {e}")
                    dev_res[cmd] = None
            return dev_res

        # 限制最大并发，避免对 eNSP/本机造成过大压力
        worker_count = min(max_workers, len(device_names)) or 1
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_dev = {
                executor.submit(worker, dev): dev
                for dev in device_names
            }
            for future in as_completed(future_to_dev):
                dev_name = future_to_dev[future]
                try:
                    dev_res = future.result()
                except Exception as e:
                    logger.error(f"Batch execution error on {dev_name}: {e}")
                    dev_res = {cmd: None for cmd in commands}
                results[dev_name] = dev_res

        return results

    def ensure_lldp_enabled(self, name: str) -> bool:
        """
        确保指定设备已启用 LLDP。
        如果检测到未启用或无法确认状态，则尝试下发全局 lldp enable。
        返回 True 表示最终认为已启用（或命令下发成功），False 表示失败。
        """
        # 尝试通过查询命令判断 LLDP 是否可用
        check_cmd = "display lldp local"
        output = self.execute_command(name, check_cmd)
        if output:
            text = output.lower()
            # 粗略判断：存在关键字段且没有明显错误提示，则认为已启用
            if ("lldp" in text and "enable" in text) and not any(
                kw in text for kw in ["unrecognized command", "error", "not enabled"]
            ):
                logger.info(f"LLDP already enabled on {name}")
                return True

        # 未能确定或明确未启用，尝试通过配置命令启用 LLDP（全局）
        logger.info(f"Enabling LLDP globally on {name} ...")
        ok = self.execute_config_commands(
            name,
            [
                "system-view",
                "lldp enable",
                "quit",
            ],
        )
        if not ok:
            logger.error(f"Failed to enable LLDP on {name}")
            return False

        # 再次做一次轻量校验（不强依赖结果）
        verify_output = self.execute_command(name, check_cmd)
        if verify_output:
            logger.info(f"LLDP enable verification output on {name}: {verify_output[:200]}...")
        return True
