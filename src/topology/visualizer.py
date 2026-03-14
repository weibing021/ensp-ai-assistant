import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt

def visualize_topology(graph: nx.Graph):
    """可视化网络拓扑图"""
    if not graph or graph.number_of_nodes() == 0:
        st.warning("暂无拓扑数据可供展示")
        return None

    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 获取节点标签（优先使用 hostname）
    labels = {node: data.get('hostname', node) for node, data in graph.nodes(data=True)}
    
    # 布局算法
    pos = nx.spring_layout(graph, seed=42)
    
    # 绘制节点
    nx.draw_networkx_nodes(graph, pos, node_size=2000, node_color='skyblue', ax=ax)
    
    # 绘制边
    nx.draw_networkx_edges(graph, pos, width=2, edge_color='gray', ax=ax)
    
    # 绘制标签
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=12, font_family='sans-serif', ax=ax)
    
    # 绘制边标签（端口信息）
    edge_labels = {}
    for u, v, data in graph.edges(data=True):
        local_port = data.get('local_port', '')
        remote_port = data.get('remote_port', '')
        if local_port or remote_port:
            edge_labels[(u, v)] = f"{local_port} <-> {remote_port}"
    
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_size=8, ax=ax)
    
    ax.set_title("Network Topology Map")
    ax.axis('off')
    
    return fig

class TopologyVisualizer:
    def __init__(self, topology_builder):
        self.topology_builder = topology_builder

    def render(self):
        fig = visualize_topology(self.topology_builder.graph)
        if fig:
            st.pyplot(fig)
