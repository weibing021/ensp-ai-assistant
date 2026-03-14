"""Streamlit主应用入口""" 
import streamlit as st 
import yaml 
import os 
import sys
from dotenv import load_dotenv 

# 解决 ModuleNotFoundError: No module named 'src'
# 将项目根目录添加到 sys.path 中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.connection.device_manager import DeviceManager 
from src.topology.collector import InfoCollector 
from src.topology.builder import TopologyBuilder 
from src.topology.visualizer import visualize_topology 
from src.ai.llm_client import LLMClient 
from src.ai.intent_parser import IntentParser 
from src.ai.command_gen import CommandGenerator 
from src.ai.fault_diagnosis import FaultDiagnosis 
from src.executor.config_executor import ConfigExecutor 
from src.validator.tester import Tester 
from src.utils.logger import setup_logger 
from src.utils.db import DatabaseManager

# 加载环境变量 
load_dotenv() 

# 加载配置 
config_path = './config/config.yaml'
if not os.path.exists(config_path):
    st.error(f"未找到配置文件: {config_path}")
    st.stop()

with open(config_path, 'r', encoding='utf-8') as f: 
    config = yaml.safe_load(f) 

# 初始化日志 
setup_logger() 

# 初始化会话状态
if 'task_history' not in st.session_state:
    st.session_state['task_history'] = []
if 'last_parsed_tasks' not in st.session_state:
    st.session_state['last_parsed_tasks'] = None

# AI & 搜索相关会话配置
default_llm_cfg = config.get('llm', {})
llm_presets = config.get('llm_presets', [])
if 'llm_provider' not in st.session_state:
    st.session_state['llm_provider'] = default_llm_cfg.get('provider', 'openai')
if 'llm_model' not in st.session_state:
    st.session_state['llm_model'] = default_llm_cfg.get('model', 'gpt-3.5-turbo')
if 'llm_base_url' not in st.session_state:
    st.session_state['llm_base_url'] = default_llm_cfg.get('base_url', '')
if 'llm_api_key_env' not in st.session_state:
    st.session_state['llm_api_key_env'] = default_llm_cfg.get('api_key_env', 'OPENAI_API_KEY')
if 'llm_preset_name' not in st.session_state:
    st.session_state['llm_preset_name'] = "自定义（使用 config.yaml 配置）"
if 'use_web_search' not in st.session_state:
    # 预留开关：是否启用互联网聚合搜索增强
    st.session_state['use_web_search'] = False

# 侧边栏：AI & 搜索配置（放在设备管理前）
with st.sidebar:
    st.subheader("🤖 AI & 搜索配置")
    provider_labels = {
        "openai": "在线 OpenAI / 兼容接口",
        "openai_compatible": "OpenAI 兼容 API（国内/第三方）",
        "local": "本地大模型 (Ollama)",
    }
    inverse_provider_labels = {v: k for k, v in provider_labels.items()}
    # 预置模型选项（包含一个“自定义”占位）
    preset_names = ["自定义"] + [p.get("name", f"预设 {i+1}") for i, p in enumerate(llm_presets)]
    current_preset = st.session_state.get('llm_preset_name', "自定义")
    try:
        preset_index = preset_names.index(current_preset)
    except ValueError:
        preset_index = 0
    selected_preset = st.selectbox(
        "预设模型（可选）",
        options=preset_names,
        index=preset_index,
        help="选择一个预配置的免费/本地/兼容模型，或选择“自定义”手动填写。",
    )
    st.session_state['llm_preset_name'] = selected_preset

    # 如果选中了具体预设，则用预设覆盖当前会话配置
    if selected_preset != "自定义":
        for p in llm_presets:
            if p.get("name") == selected_preset:
                st.session_state['llm_provider'] = p.get('provider', st.session_state['llm_provider'])
                st.session_state['llm_model'] = p.get('model', st.session_state['llm_model'])
                if 'base_url' in p:
                    st.session_state['llm_base_url'] = p.get('base_url', st.session_state['llm_base_url'])
                if 'api_key_env' in p:
                    st.session_state['llm_api_key_env'] = p.get('api_key_env', st.session_state['llm_api_key_env'])
                break

    current_provider = st.session_state['llm_provider']
    current_label = provider_labels.get(current_provider, provider_labels['openai'])
    selected_label = st.selectbox(
        "LLM 提供方",
        options=list(provider_labels.values()),
        index=list(provider_labels.values()).index(current_label),
        key="llm_provider_label",
    )
    st.session_state['llm_provider'] = inverse_provider_labels[selected_label]

    st.session_state['llm_model'] = st.text_input(
        "模型名称",
        value=st.session_state['llm_model'],
        help="例如 gpt-3.5-turbo、gpt-4o、qwen-max、glm-4 等",
    )

    if st.session_state['llm_provider'] in ('openai', 'openai_compatible'):
        st.session_state['llm_base_url'] = st.text_input(
            "OpenAI 兼容 Base URL（可选）",
            value=st.session_state['llm_base_url'],
            help="例如 https://api.openai.com/v1 或 第三方兼容接口地址；留空使用默认。",
        )

    st.session_state['use_web_search'] = st.checkbox(
        "启用互联网聚合搜索增强（预留）",
        value=st.session_state['use_web_search'],
        help="开启后，解析/诊断逻辑可按需接入在线搜索能力（当前为预留开关）。",
    )

# 初始化核心组件（使用 st.cache_resource 确保在 Streamlit 重新运行时不会重复创建连接池等）
@st.cache_resource
def init_components(llm_overrides: dict):
    dm = DeviceManager(config['connection']) 
    # 合并配置：以 UI 选择为主
    merged_llm_cfg = config['llm'].copy()
    merged_llm_cfg.update(llm_overrides or {})
    llm = LLMClient(merged_llm_cfg) 
    ip = IntentParser(llm) 
    cg = CommandGenerator(llm) 
    exe = ConfigExecutor(dm, cg) 
    t = Tester(dm) 
    diag = FaultDiagnosis(llm) 
    db = DatabaseManager()
    topo_collector = InfoCollector(dm, config.get('topology', {}))
    topo_builder = TopologyBuilder()
    # 尝试加载已有拓扑（如果存在）
    topo_builder.load_topology()
    
    # 从数据库加载历史设备
    saved_devices = db.get_devices()
    for name, ip_addr, port, dev_type in saved_devices:
        dm.add_device(name, ip_addr, port)
        
    return dm, llm, ip, cg, exe, t, diag, db, topo_collector, topo_builder

llm_overrides = {
    "provider": st.session_state['llm_provider'],
    "model": st.session_state['llm_model'],
    "base_url": st.session_state['llm_base_url'],
    "api_key_env": st.session_state['llm_api_key_env'],
}
device_manager, llm_client, intent_parser, command_gen, executor, tester, diagnosis, db_manager, topo_collector, topo_builder = init_components(llm_overrides)

# Streamlit 界面布局
st.set_page_config(page_title="eNSP AI Assistant", layout="wide", page_icon="🧠") 
st.title("� eNSP AI 配置助手") 

# 侧边栏：设备管理 
with st.sidebar: 
    st.header("🏢 设备管理") 
    with st.form("add_device"): 
        name = st.text_input("设备名", placeholder="例如: R1") 
        ip_addr = st.text_input("IP地址", value="127.0.0.1") 
        port = st.number_input("Telnet端口", value=2000, step=1) 
        submitted = st.form_submit_button("➕ 添加设备") 
        if submitted and name and ip_addr: 
            # 保存到内存
            device_manager.add_device(name, ip_addr, port) 
            # 保存到数据库
            device_info = device_manager.devices[name]
            db_manager.add_device(name, ip_addr, port, device_info['device_type'])
            st.success(f"设备 {name} 已添加到列表") 
            st.rerun()
    
    st.divider()
    st.subheader("📋 已添加设备") 
    devices_list = device_manager.devices.keys()
    if not devices_list:
        st.info("暂无设备，请先添加")
    else:
        connected_devices = device_manager.get_all_connected()
        for dev_name in list(devices_list): 
            status_label = "🟢 已连接" if dev_name in connected_devices else "🔴 未连接"
            with st.expander(f"{status_label} | 🖥️ {dev_name}"):
                info = device_manager.devices[dev_name]
                st.caption(f"类型: {info['device_type']} | 地址: {info['ip']}:{info['port']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔗 连接", key=f"conn_{dev_name}"): 
                        with st.spinner(f"正在连接 {dev_name}..."):
                            conn = device_manager.connect(dev_name) 
                            if conn: 
                                st.success(f"连接成功") 
                                st.rerun()
                            else: 
                                # 在 UI 中展示具体的失败原因
                                st.error(f"连接失败")
                                st.info("💡 请检查 eNSP 设备是否已启动，以及 Serial Port 端口号是否正确。")
                with col2:
                    if st.button("🗑️ 移除", key=f"del_{dev_name}"):
                        device_manager.remove_device(dev_name)
                        db_manager.delete_device(dev_name)
                        st.rerun()

# 主标签页 
tab1, tab2, tab3, tab4 = st.tabs(["💬 指令解析与执行", "🗺️ 拓扑自动发现", "⚙️ 手动配置下发", "🔍 故障分析排错"]) 

with tab1: 
    st.header("💬 自然语言指令解析") 
    st.info("输入您的配置需求，AI 将生成任务清单。解析后的任务可保存至历史记录以便后续执行。")
    user_input = st.text_area("配置需求 (例如: '在 R1 和 R2 之间配置 OSPF')", height=100) 
    
    col1, col2 = st.columns([1, 5])
    with col1:
        parse_btn = st.button("🚀 开始解析", use_container_width=True)
    
    if parse_btn: 
        if user_input: 
            with st.spinner("AI 正在解析意图..."): 
                tasks = intent_parser.parse(user_input) 
                st.session_state['last_parsed_tasks'] = tasks 
        else:
            st.warning("请输入指令内容")
    
    if st.session_state['last_parsed_tasks']: 
        st.subheader("🤖 当前解析结果") 
        st.json(st.session_state['last_parsed_tasks']) 
        
        if st.button("💾 保存至待执行清单", type="primary"):
            from datetime import datetime
            task_entry = {
                "id": len(st.session_state['task_history']) + 1,
                "time": datetime.now().strftime("%H:%M:%S"),
                "input": user_input[:50] + "..." if len(user_input) > 50 else user_input,
                "tasks": st.session_state['last_parsed_tasks']
            }
            st.session_state['task_history'].append(task_entry)
            st.session_state['last_parsed_tasks'] = None
            st.success("任务已保存到 '配置执行' 标签页中")
            st.rerun()

with tab2:
    st.header("🗺️ 拓扑自动发现")
    all_devs = list(device_manager.devices.keys())
    if not all_devs:
        st.info("暂无设备，请先在侧边栏添加并连接设备")
    else:
        target_devs = st.multiselect("选择参与拓扑发现的设备", options=all_devs, default=all_devs, key="topo_devices")
        if st.button("🚀 开始拓扑发现", type="primary"):
            if not target_devs:
                st.warning("请至少选择一个设备")
            else:
                # 步骤1：确保参与拓扑发现的设备已启用 LLDP
                with st.spinner("正在检查并启用设备 LLDP 功能..."):
                    for dev in target_devs:
                        ok = device_manager.ensure_lldp_enabled(dev)
                        if not ok:
                            st.warning(f"设备 {dev} 的 LLDP 启用可能失败，请稍后在 CLI 中手动确认。")

                # 步骤2：采集信息并构建拓扑
                with st.spinner("正在采集设备信息并构建拓扑..."):
                    collected = topo_collector.collect_all(target_devs)
                    graph = topo_builder.build(collected)
                    topo_builder.save_topology()
                st.success("拓扑发现完成")

        # 如果已有拓扑数据，进行可视化展示
        if topo_builder.graph and topo_builder.graph.number_of_nodes() > 0:
            st.subheader("📍 当前拓扑视图")
            fig = visualize_topology(topo_builder.graph)
            if fig:
                st.pyplot(fig)

with tab3: 
    st.header("⚙️ 任务执行与手动配置") 
    
    # 历史任务引用部分
    st.subheader("� 待执行任务清单")
    if not st.session_state['task_history']:
        st.info("暂无已解析的任务，请先在 '指令解析' 标签页中进行解析并保存。")
    else:
        # 选择要执行的历史任务
        task_options = {f"[{t['time']}] {t['input']}": t for t in st.session_state['task_history']}
        selected_task_key = st.selectbox("🎯 选择待执行任务", options=list(task_options.keys()))
        
        if selected_task_key:
            selected_task_data = task_options[selected_task_key]
            st.json(selected_task_data['tasks'])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 立即执行该任务", type="primary", use_container_width=True):
                    with st.spinner("正在下发配置..."):
                        results = executor.execute_tasks(selected_task_data['tasks'])
                        st.session_state['last_exec_results'] = results
                        st.success("执行完成")
            with col2:
                if st.button("🗑️ 移除此任务", use_container_width=True):
                    st.session_state['task_history'] = [t for t in st.session_state['task_history'] if t['id'] != selected_task_data['id']]
                    st.rerun()

    if 'last_exec_results' in st.session_state:
        st.divider()
        st.subheader("📊 执行结果反馈")
        st.json(st.session_state['last_exec_results'])
        if st.button("🧹 清除执行记录"):
            del st.session_state['last_exec_results']
            st.rerun()

    st.divider()
    st.subheader("📝 手动 CLI 命令下发")
    all_devs = list(device_manager.devices.keys())
    if not all_devs:
        st.warning("请先在侧边栏添加设备")
    else:
        selected_dev = st.selectbox("🎯 选择目标设备", options=all_devs, key="manual_dev") 
        commands_text = st.text_area("📝 输入 VRP 命令（每行一条）", height=150, key="manual_cmd") 
        if st.button("📤 发送配置", use_container_width=True): 
            if commands_text: 
                cmd_list = [c.strip() for c in commands_text.split('\n') if c.strip()] 
                with st.spinner(f"正在向 {selected_dev} 发送命令..."):
                    success = device_manager.execute_config_commands(selected_dev, cmd_list) 
                    if success: 
                        st.success(f"配置已成功应用于 {selected_dev}") 
                    else: 
                        st.error("配置发送失败")

    st.divider()
    st.subheader("📡 多设备远程命令执行")
    connected_devs = device_manager.get_all_connected()
    if not connected_devs:
        st.info("当前暂无已连接设备，请先在侧边栏连接设备后再执行远程命令。")
    else:
        multi_devs = st.multiselect(
            "选择要执行命令的设备（仅显示已连接设备）",
            options=connected_devs,
            default=connected_devs,
            key="multi_exec_devs"
        )
        multi_cmds_text = st.text_area("🧾 输入操作/查询命令（每行一条）", height=120, key="multi_exec_cmds")
        if st.button("▶️ 执行远程命令", use_container_width=True):
            if not multi_devs:
                st.warning("请至少选择一个设备")
            elif not multi_cmds_text:
                st.warning("请输入至少一条命令")
            else:
                cmd_list = [c.strip() for c in multi_cmds_text.split('\n') if c.strip()]
                with st.spinner("正在多设备并发执行命令..."):
                    batch_out = device_manager.execute_batch(
                        device_names=multi_devs,
                        commands=cmd_list,
                        is_config=False,
                    )
                    st.session_state["last_multi_exec"] = {"devices": multi_devs, "commands": cmd_list, "results": batch_out}

    if "last_multi_exec" in st.session_state:
        st.subheader("📃 多设备命令执行结果")
        last = st.session_state["last_multi_exec"]
        for dev in last["devices"]:
            dev_res = last["results"].get(dev, {})
            with st.expander(f"🖥️ {dev}", expanded=False):
                if not dev_res:
                    st.info("未获取到任何输出（可能连接失败或命令执行异常）。")
                else:
                    for cmd in last["commands"]:
                        output = dev_res.get(cmd)
                        st.markdown(f"**$ {cmd}**")
                        if output is None:
                            st.text("执行失败或无输出")
                        else:
                            st.code(output)

    st.divider()
    st.subheader("📥 设备配置读取与备份")
    if not all_devs:
        st.info("请先在侧边栏添加设备")
    else:
        cfg_dev = st.selectbox("选择要读取配置的设备", options=all_devs, key="cfg_dev")
        col_cfg1, col_cfg2 = st.columns(2)
        with col_cfg1:
            if st.button("📑 读取当前配置", use_container_width=True):
                with st.spinner(f"正在从 {cfg_dev} 读取当前配置..."):
                    cfg_output = device_manager.execute_command(cfg_dev, "display current-configuration")
                    if cfg_output is None:
                        st.error("读取配置失败，请检查连接状态。")
                    else:
                        st.session_state["last_config_dump"] = {"device": cfg_dev, "content": cfg_output}
        with col_cfg2:
            if st.button("💾 保存配置到服务器", use_container_width=True):
                cfg_info = st.session_state.get("last_config_dump")
                if not cfg_info or cfg_info.get("device") != cfg_dev:
                    st.warning("请先读取该设备的当前配置。")
                else:
                    import datetime
                    import os as _os
                    backup_dir = "./data/config_backups"
                    _os.makedirs(backup_dir, exist_ok=True)
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{cfg_dev}_config_{ts}.cfg"
                    path = _os.path.join(backup_dir, filename)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(cfg_info["content"])
                    st.success(f"配置已保存到 {path}")

        if "last_config_dump" in st.session_state and st.session_state["last_config_dump"].get("device") == cfg_dev:
            st.subheader("📄 最近读取的设备配置")
            st.code(st.session_state["last_config_dump"]["content"])

with tab4: 
    st.header("🔍 网络故障分析排错") 
    st.info("AI 专家将协助您分析连通性问题并给出修复建议。")
    fault_desc = st.text_area("⚠️ 故障现象描述 (例如: 'R1 无法 ping 通 R2，但是 R1 接口状态是 UP')", height=100) 
    
    if st.button("🩺 开始 AI 诊断", type="primary"): 
        if fault_desc: 
            all_devs = list(device_manager.devices.keys())
            if not all_devs:
                st.warning("请先添加设备以供 AI 采集诊断数据")
            else:
                with st.spinner("正在采集诊断上下文信息 (路由表/接口状态)..."): 
                    # 并发采集所有设备的关键诊断信息
                    collect_cmds = [
                        "display ip routing-table",
                        "display ip interface brief",
                    ]
                    batch_results = device_manager.execute_batch(
                        device_names=all_devs,
                        commands=collect_cmds,
                        is_config=False,
                    )
                    device_outputs = {}
                    for dev, cmd_res in batch_results.items():
                        device_outputs[dev] = {
                            "routing": cmd_res.get("display ip routing-table"),
                            "interfaces": cmd_res.get("display ip interface brief"),
                        }
                    
                    with st.spinner("AI 专家正在分析根因并生成修复方案..."): 
                        diag_result = diagnosis.diagnose(fault_desc, device_outputs) 
                        st.session_state['diag_result'] = diag_result 
        else:
            st.warning("请先描述故障现象")

    if 'diag_result' in st.session_state:
        res = st.session_state['diag_result']
        st.subheader("🔬 诊断分析报告")
        st.write(f"**分析详情**: {res.get('analysis', '无数据')}")
        st.write(f"**风险等级**: `{res.get('risk_level', 'Unknown')}`")
        
        st.subheader("🛠️ 修复建议命令")
        if res.get('suggestions'):
            st.code("\n".join(res['suggestions']))
            if st.button("🚀 自动应用修复配置"):
                # 这里可以根据建议自动执行，为了安全暂时仅展示
                st.info("自动应用功能待进一步确认安全策略后开启")
        else:
            st.info("AI 未能生成具体的修复命令，请手动核查")

# 底部页脚
st.markdown("---") 
st.caption("eNSP AI Assistant v0.1.0 | Powered by Gemini & LangChain | © 2026")
