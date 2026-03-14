## 高层架构说明

### 模块划分

- **UI 层（Streamlit）**  
  - `main.py`：提供 Web 界面与交互逻辑。  
  - 负责调用下层服务：意图解析、命令生成、执行、诊断、拓扑等。

- **连接与会话层**  
  - `DeviceManager`：管理设备信息、Telnet 连接、命令执行。  
  - `SessionPool`：缓存和复用会话，提升多设备场景的执行效率。

- **AI 能力层**  
  - `LLMClient`：封装 OpenAI / 本地模型调用。  
  - `IntentParser`：自然语言 → 任务列表（JSON）。  
  - `CommandGenerator`：任务 → VRP 命令序列。  
  - `FaultDiagnosis`：设备状态 + 故障描述 → 诊断报告与修复建议。

- **拓扑层**  
  - `InfoCollector`：并发采集拓扑相关命令输出。  
  - `TopologyBuilder`：根据采集结果构建 NetworkX 拓扑图。  
  - `visualizer`：将拓扑图渲染为可视化图像在 Web 中展示。

- **执行与验证层**  
  - `ConfigExecutor`：根据任务列表调用命令生成器与设备管理器进行自动下发。  
  - `TaskScheduler`：简单任务队列与后台执行框架（预留）。  
  - `Tester`：连通性测试与配置验证。  
  - `Reporter`：以 JSON 或文本形式生成任务执行报告。

- **基础设施层**  
  - `DatabaseManager`：SQLite 持久化设备与任务。  
  - `logger`：统一日志配置。  
  - `prompt_loader`：加载和管理模型提示词模板。  
  - `CLIParser`：基于 TextFSM 的 CLI 输出解析工具。

### 架构示意图（Mermaid）

```mermaid
flowchart LR
    User[用户浏览器\nStreamlit 页面] --> UI[UI 层\n(main.py Tabs)]
    
    UI --> IP[IntentParser\n自然语言解析]
    UI --> CG[CommandGenerator\n命令生成]
    UI --> EXE[ConfigExecutor\n配置执行]
    UI --> DIAG[FaultDiagnosis\n故障诊断]
    UI --> TOPO_UI[拓扑可视化\nTopologyVisualizer]
    UI --> TEST[Tester\n连通性/验证]
    
    IP --> LLM[LLMClient]
    CG --> LLM
    DIAG --> LLM
    
    EXE --> DM[DeviceManager\n连接 & 会话池]
    TEST --> DM
    TOPO_COLLECT[InfoCollector\n并发采集] --> DM
    DIAG --> DM
    
    DM --> ENSP[eNSP 虚拟设备\n(VRP)]
    
    TOPO_COLLECT --> TOPO_BUILD[TopologyBuilder\n拓扑构建]
    TOPO_BUILD --> TOPO_UI
    
    UI --> DB[DatabaseManager\n设备/任务持久化]
    UI --> LOG[Logger\n日志输出]
```

