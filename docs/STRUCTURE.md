## 项目目录结构说明

```text
ensp-ai-assistant/
├─ README.md                # 项目总览（中文）
├─ requirements.txt         # Python 依赖列表
├─ .env.example             # 环境变量示例（LLM API Key 等）
├─ .env                     # 本地环境变量（不应提交到版本库）
│
├─ config/                  # 配置与提示词
│  ├─ config.yaml           # 应用主配置（连接、LLM、数据库、拓扑）
│  └─ prompts/              # 大模型提示词模板
│     ├─ intent_parser.txt
│     ├─ command_gen.txt
│     └─ fault_diagnosis.txt
│
├─ src/                     # 核心源码
│  ├─ main.py               # Streamlit Web 应用入口
│  │
│  ├─ ai/                   # AI 能力层
│  │  ├─ llm_client.py      # LLM 调用封装（OpenAI / 本地）
│  │  ├─ intent_parser.py   # 自然语言 → 任务列表
│  │  ├─ command_gen.py     # 任务 → VRP 配置命令
│  │  └─ fault_diagnosis.py # 故障诊断与修复建议
│  │
│  ├─ connection/           # 设备连接与会话管理
│  │  ├─ device_manager.py  # 设备信息、Telnet 连接、命令执行
│  │  └─ session_pool.py    # 连接会话池（复用连接）
│  │
│  ├─ topology/             # 拓扑采集与构建
│  │  ├─ collector.py       # 并发采集拓扑相关命令输出
│  │  ├─ builder.py         # 基于采集数据构建 NetworkX 拓扑图
│  │  └─ visualizer.py      # 使用 matplotlib + Streamlit 可视化拓扑
│  │
│  ├─ executor/             # 配置执行与任务调度
│  │  ├─ config_executor.py # 按任务生成并下发配置命令
│  │  └─ task_scheduler.py  # 简单任务队列与后台执行（预留）
│  │
│  ├─ validator/            # 测试与验证
│  │  ├─ tester.py          # ping/traceroute/show 验证
│  │  └─ reporter.py        # 生成 JSON / 文本报告
│  │
│  └─ utils/                # 通用工具
│     ├─ db.py              # SQLite 数据库访问（设备/任务持久化）
│     ├─ logger.py          # 日志配置（stdout + data/app.log）
│     ├─ prompt_loader.py   # 提示词模板加载
│     └─ parsers.py         # TextFSM CLI 解析工具
│
├─ data/                    # 运行期数据（自动生成）
│  ├─ app.log               # 应用日志
│  ├─ topology.json         # 最近保存的拓扑结构
│  └─ session_logs/         # 设备会话日志（按设备 + 时间命名）
│
└─ docs/                    # 项目文档
   ├─ README.md             # 文档总览（可选）
   ├─ PRODUCT_OVERVIEW.md   # 产品说明索引（指向下列文档）
   ├─ INTRODUCTION.md       # 产品简介与场景
   ├─ FEATURES.md           # 核心特性列表
   ├─ ARCHITECTURE.md       # 高层架构与模块划分
   └─ USER_GUIDE.md         # 典型使用流程 / 用户指南
```

### 建议阅读顺序

1. `README.md`：快速了解项目和启动方式。  
2. `docs/INTRODUCTION.md`：理解产品定位和适用场景。  
3. `docs/FEATURES.md`：掌握完整功能清单。  
4. `docs/ARCHITECTURE.md`：了解整体架构与模块间关系。  
5. `docs/USER_GUIDE.md`：跟随步骤实际操作与体验产品。  

