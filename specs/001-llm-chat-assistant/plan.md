# 实施计划: 智能网络运维助手

**分支**: `001-llm-chat-assistant` | **日期**: 2025-12-29 | **规范**: [spec.md](./spec.md)
**输入**: 来自 `/specs/001-llm-chat-assistant/` 的设计文档

## 摘要

实现一个智能网络运维助手系统，包含 TCP 长连接通信（NPLT 协议）、UDP 可靠文件传输（RDT 协议）和基于智谱 AI 的 Agent 工具调用功能。系统采用异步 Python 架构，使用 Rich 库实现类 IDE 的 CLI 终端界面，支持多会话管理、文件上传与 RAG 检索、模型动态切换等高级功能。

## 技术背景

**语言/版本**: Python 3.11
**主要依赖**: zai-sdk（智谱 AI 官方 SDK）、asyncio（异步编程）、Rich（CLI UI 库）、FAISS（向量存储）、PyYAML（配置管理）

**存储**:

- 文件系统（storage/vectors/、storage/history/、storage/uploads/）
- JSON 格式持久化
- FAISS 向量索引

**测试**: pytest（真实测试，无 mock）

**目标平台**: Linux 服务器（命令行环境）

**项目类型**: 单一项目（客户端-服务器架构）

**性能目标**:

- AI 工具调用响应时间 < 2s（SC-002）
- 流式文本响应延迟 < 1s（SC-003）
- UDP 文件传输吞吐量 > 1MB/s（0% 丢包，SC-004）
- UDP 文件传输成功率 100%（10% 丢包，SC-005）

**约束条件**:

- 文件上传限制 10MB
- 最大会话历史支持（通过压缩机制）
- 心跳超时 90 秒
- 工具执行超时 5 秒

**规模/范围**:

- 单用户场景（未来扩展支持 10 并发客户端）
- 支持多会话管理
- 3 个核心用户故事（对话、RAG、文件传输）
- 99 个基础任务 + 7 个模型切换任务 + 20 个多会话管理任务

## 章程检查

*门控: 必须在阶段 0 研究前通过。阶段 1 设计后重新检查。*

基于 `.specify/memory/constitution.md` 中的原则，本功能 MUST 通过以下检查：

### 质量与一致性
- [x] 代码遵循项目编码规范（Python 3.11，PEP 8）
- [x] 实现是真实的，不允许虚假实现或占位符（已验证所有代码，无 pass 占位符）
- [x] 代码审查清单已准备

### 测试真实性
- [x] 测试计划不包含任何 mock 测试
- [x] 涉及 LLM 的测试使用真实的智谱 API
- [x] API key 验证机制已包含在测试设置中（环境变量 ZHIPU_API_KEY）

### 文档与可追溯性
- [x] 日志将写入 logs 文件夹
- [x] 日志格式为纯文本 (.log)
- [x] 日志包含时间戳、操作类型和上下文信息

### 真实集成
- [x] 使用官方 zai-sdk 进行智谱 AI 集成
- [x] 所有 LLM 调用通过真实 API 进行
- [x] 无使用模拟回复的实现

### 开发环境标准
- [x] Python 版本为 3.11
- [x] 使用 uv 管理虚拟环境
- [x] 依赖通过 uv 管理并记录

### 语言规范
- [x] 所有用户回复使用中文
- [x] 所有代码注释使用中文
- [x] 所有文档使用中文
- [x] 错误消息和日志使用中文

### 版本控制与测试纪律

- [x] 每个阶段完成后通过真实测试
- [x] 测试通过后进行 git 提交
- [x] 提交消息清晰描述阶段工作和测试结果
- [x] 不允许跳过测试或使用虚假测试

**章程合规状态**: ✅ 全部通过（所有 107 个基础任务已完成，7 个模型切换任务和 20 个多会话管理任务已完成，209 个测试全部通过，2 个跳过）

## 项目结构

### 文档(此功能)

```
specs/001-llm-chat-assistant/
├── plan.md              # 此文件 (/speckit.plan 命令输出)
├── research.md          # 阶段 0 输出 - 技术决策记录
├── data-model.md        # 阶段 1 输出 - 数据模型定义
├── quickstart.md        # 阶段 1 输出 - 快速开始指南
├── contracts/           # 阶段 1 输出 - API 协议规范
│   ├── nplt-protocol.md # NPLT 协议规范
│   └── rdt-protocol.md  # RDT 协议规范
└── tasks.md             # 阶段 2 输出 - 任务分解列表
```

### 源代码(仓库根目录)

```
src/
├── client/              # 客户端模块
│   ├── main.py          # 客户端主程序
│   ├── nplt_client.py   # NPLT 协议客户端
│   ├── rdt_client.py    # RDT 文件传输客户端
│   └── ui.py            # Rich UI 组件
├── server/              # 服务器模块
│   ├── main.py          # 服务器主程序
│   ├── nplt_server.py   # NPLT 协议服务器
│   ├── rdt_server.py    # RDT 文件传输服务器
│   └── agent.py         # ReAct Agent 实现
├── protocols/           # 协议定义
│   ├── nplt.py          # NPLT 消息协议
│   └── rdt.py           # RDT 传输协议
├── llm/                 # LLM 抽象层
│   ├── base.py          # LLM Provider 抽象接口
│   └── zhipu.py         # 智谱 AI 实现
├── storage/             # 存储层
│   ├── vector_store.py  # 向量存储（FAISS）
│   └── history.py       # 对话历史管理
├── tools/               # Agent 工具
│   ├── base.py          # 工具基类
│   ├── command.py       # 命令执行工具
│   ├── monitor.py       # 系统监控工具
│   └── rag.py           # RAG 检索工具
└── utils/               # 工具模块
    ├── config.py        # 配置管理
    └── logger.py        # 日志管理

tests/
├── integration/         # 集成测试
│   ├── test_agent.py    # Agent 测试
│   ├── test_client.py   # 客户端测试
│   └── test_server.py   # 服务器测试
└── unit/                # 单元测试

storage/                 # 数据存储目录
├── vectors/             # 向量索引
├── history/             # 对话历史
├── uploads/             # 上传文件
└── archive/             # 归档会话（多会话管理）

logs/                    # 日志文件

config.yaml              # 主配置文件
.env                     # 环境变量（ZHIPU_API_KEY）
```

**结构决策**: 选择单一项目结构，因为这是一个客户端-服务器架构的系统，客户端和服务器共享协议定义、LLM 抽象层和存储组件。将所有代码放在单一仓库中便于维护和版本控制。

## 已知问题与实现说明

### 上下文管理实现状态

**规范期望**（spec.md:36-38）：
- 对话上下文窗口大小策略：基于 token 阈值的智能压缩机制
- 上下文压缩策略：智能评分（根据消息重要性评分压缩）
- 对话历史窗口管理机制：双层管理机制（本地保存完整历史，传递给大模型的上下文使用压缩+滑动窗口模式）

**当前实现**（spec.md:42）：
- ✅ 本地保存完整对话历史（用于 `/history` 命令）
- ✅ 传递给 LLM 使用固定轮数策略（`get_context(max_turns=3)`）
- ⚠️ Token 阈值压缩和重要性评分机制标记为"未来增强功能"
- ⚠️ 双层管理机制部分实现（本地保存完整历史，但传递给 LLM 的上下文未启用压缩）

**实现代码**：
- [src/storage/history.py:111-121](../src/storage/history.py#L111-L121) - `get_context()` 使用简单的 FIFO 截断
- [src/server/agent.py](../src/server/agent.py) - Agent 调用 `get_context(max_turns=3)` 获取最近 3 轮对话

**说明**：当前实现采用固定轮数策略，能够在大多数场景下提供良好的上下文连续性，并控制 token 消耗。完整的智能压缩+窗口模式（包含 token 计算、重要性评分算法）被明确标记为未来增强功能，不在当前 MVP 范围内。

### 多会话管理功能

**状态**: ✅ 已完成（阶段 6，T080-T097）

已实现完整的单用户多会话管理功能：
- ✅ 会话创建、查看、切换、删除
- ✅ AI 自动命名（第 3 轮对话后触发）
- ✅ 会话自动归档（30 天未访问）
- ✅ 客户端命令（`/sessions`、`/switch`、`/new`、`/delete`）
- ✅ 服务器端会话管理器集成

## 复杂度跟踪

*仅在章程检查有必须证明的违规时填写*

**状态**: ✅ 本项目严格遵循所有章程原则，无违规需要记录，无需复杂度证明。

## 架构决策记录（研究阶段）

决策记录详见 [research.md](./research.md)

## 数据模型

数据模型定义详见 [data-model.md](./data-model.md)

## API 合同

协议规范详见 [contracts/](./contracts/) 目录

## 快速开始

快速开始指南详见 [quickstart.md](./quickstart.md)
