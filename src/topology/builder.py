"""拓扑构建器""" 
import networkx as nx 
import re 
import json
import logging
import os
from typing import Dict, Any, List, Tuple 

logger = logging.getLogger(__name__)

class TopologyBuilder: 
    """根据采集的信息构建网络拓扑图""" 
    
    def __init__(self, data_dir="./data"): 
        self.data_dir = data_dir
        self.graph = nx.Graph()  # 节点可以是设备或子网 
        self.devices = {}  # name -> device info 
        self.nodes = {}    # 兼容旧版本 JSON 序列化
        self.edges = []    # 兼容旧版本 JSON 序列化
        
    def build(self, collected_data: Dict[str, Dict[str, str]]) -> nx.Graph: 
        """从采集数据构建拓扑""" 
        self._parse_devices(collected_data) 
        self._infer_links(collected_data)
        # 更新 nodes 和 edges 列表用于持久化
        self._update_serialization_data()
        return self.graph 
    
    def _parse_devices(self, data: Dict[str, Dict[str, str]]): 
        """解析设备基本信息和接口""" 
        for dev_name, cmd_outputs in data.items(): 
            # 提取主机名（从 display current-configuration 中解析 sysname） 
            sysname_output = cmd_outputs.get("display current-configuration | include sysname", "") 
            match = re.search(r"sysname\s+(\S+)", sysname_output) 
            hostname = match.group(1) if match else dev_name 
            
            self.devices[dev_name] = { 
                "hostname": hostname, 
                "interfaces": []  # 稍后填充 
            } 
            # 添加设备节点 
            self.graph.add_node(dev_name, type="device", hostname=hostname) 
            
            # 解析接口信息（需调用parsers模块） 
            # TODO: 接入 CLIParser 并解析 display ip interface brief
     
    def _infer_links(self, data: Dict[str, Dict[str, str]]): 
        """推断设备间链路""" 
        # 方法1: 通过LLDP邻居 (display lldp neighbor brief)
        # 方法2: 通过ARP表匹配同一子网 (display arp)
        # 方法3: 通过路由表直连网段 (display ip routing-table)
        # TODO: 实现具体的链路推断算法 
        for dev_name, cmd_outputs in data.items():
            lldp_output = cmd_outputs.get("display lldp neighbor brief", "")
            if lldp_output:
                # 简单解析示例（实际应使用 TextFSM）
                lines = lldp_output.splitlines()
                for line in lines:
                    # 匹配典型的 LLDP 简表输出行
                    # LocalIntf  NeighborDev  NeighborIntf
                    # GE0/0/1    SW2          GE0/0/1
                    match = re.search(r"(\S+)\s+(\S+)\s+(\S+)", line)
                    if match and "Neighbor" not in line and "Local" not in line:
                        local_int, neighbor_dev, neighbor_int = match.groups()
                        self.graph.add_edge(dev_name, neighbor_dev, 
                                            local_port=local_int, 
                                            remote_port=neighbor_int)

    def _update_serialization_data(self):
        """将 Graph 转换为 nodes/edges 列表以便保存"""
        self.nodes = {node: data for node, data in self.graph.nodes(data=True)}
        self.edges = []
        for u, v, data in self.graph.edges(data=True):
            edge = {"source": u, "target": v}
            edge.update(data)
            self.edges.append(edge)

    def save_topology(self, filename="topology.json"):
        """保存拓扑到文件"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        path = os.path.join(self.data_dir, filename)
        with open(path, "w") as f:
            json.dump({"nodes": self.nodes, "edges": self.edges}, f, indent=2)
        logger.info(f"Topology saved to {path}")

    def load_topology(self, filename="topology.json"):
        """从文件加载拓扑"""
        path = os.path.join(self.data_dir, filename)
        try:
            with open(path, "r") as f:
                data = json.load(f)
                self.nodes = data["nodes"]
                self.edges = data["edges"]
                # 重新构建 graph
                self.graph = nx.Graph()
                for node_id, node_data in self.nodes.items():
                    self.graph.add_node(node_id, **node_data)
                for edge in self.edges:
                    u = edge.pop("source")
                    v = edge.pop("target")
                    self.graph.add_edge(u, v, **edge)
            logger.info(f"Topology loaded from {path}")
        except FileNotFoundError:
            logger.error(f"Topology file {path} not found")
        except Exception as e:
            logger.error(f"Error loading topology: {e}")
