# 实施计划: 智能网络运维助手

**分支**: `001-llm-chat-assistant` | **日期**: 2025-12-29 | **规范**: [spec.md](spec.md)
**输入**: 来自 `/specs/001-llm-chat-assistant/spec.md` 的功能规范

## 摘要

本功能实现一个智能网络运维助手系统，包含以下核心能力：

1. **CLI客户端基础对话** - 通过TCP长连接(NPLT协议)与AI助手进行实时对话
2. **文件上传与RAG检索** - 上传文本文件，基于向量检索进行语义搜索
3. **RDT可靠文件传输** - 通过UDP协议实现滑动窗口机制的可靠文件传输

系统采用客户端-服务器架构，使用ReAct Agent模式集成智谱AI，提供系统监控、命令执行和文档检索等运维功能。

## 技术背景

**语言/版本**: Python 3.11
**主要依赖**:
- zai-sdk (智谱AI官方SDK)
- rich (CLI UI库)
- numpy (向量计算)
- pyyaml (配置管理)
- python-dotenv (环境变量管理)

**存储**:
- 文件系统 (storage/vectors/ - 向量索引, storage/history/ - 对话历史, storage/uploads/ - 上传文件)
- 纯文本日志 (logs/)

**测试**: pytest (真实测试，无mock)
**目标平台**: Linux服务器/macOS/Windows
**项目类型**: 单一项目 (客户端+服务器同仓库)
**性能目标**:
- AI工具调用响应时间 < 2秒 (SC-002)
- 流式文本首字延迟 < 1秒 (SC-003)
- UDP传输吞吐量 > 1MB/s (0%丢包) (SC-004)

**约束条件**:
- 工具执行超时: 5秒
- 文件上传限制: 10MB
- 最大工具调用轮数: 5轮
- 心跳间隔: 90秒

**规模/范围**:
- 单用户场景 (可扩展至10并发客户端)
- 3个核心工具 (command_executor, sys_monitor, rag_search)
- 支持2个聊天模型 (glm-4-flash, glm-4.5-flash)

## 章程检查

*门控: 必须在阶段 0 研究前通过. 阶段 1 设计后重新检查. *

基于 `.specify/memory/constitution.md` 中的原则,本功能 MUST 通过以下检查:

### 质量与一致性
- [x] 代码遵循项目编码规范 (中文注释、PEP 8)
- [x] 实现是真实的,不允许虚假实现或占位符
- [x] 代码审查清单已准备 (参见checklists/)

### 测试真实性
- [x] 测试计划不包含任何 mock 测试
- [x] 涉及 LLM 的测试使用真实的智谱 API
- [x] API key 验证机制已包含在测试设置中 (tests/conftest.py)

### 文档与可追溯性
- [x] 日志将写入 logs 文件夹
- [x] 日志格式为纯文本 (.log)
- [x] 日志包含时间戳、操作类型和上下文信息 (src/utils/logger.py)

### 真实集成
- [x] 使用官方 zai-sdk 进行智谱 AI 集成
- [x] 所有 LLM 调用通过真实 API 进行 (src/llm/zhipu.py)
- [x] 无使用模拟回复的实现

### 开发环境标准
- [x] Python 版本为 3.11
- [x] 使用 uv 管理虚拟环境
- [x] 依赖通过 uv 管理并记录 (pyproject.toml)

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

## 项目结构

### 文档(此功能)

```
specs/001-llm-chat-assistant/
├── plan.md              # 此文件
├── research.md          # 技术研究文档
├── data-model.md        # 数据模型定义
├── quickstart.md        # 快速开始指南
├── contracts/           # 协议规范
│   ├── nplt.md         # NPLT协议规范
│   └── rdt.md          # RDT协议规范
├── tasks.md             # 实施任务列表
└── checklists/          # 质量检查清单
    ├── requirements.md  # 规范质量检查
    ├── ux.md           # 用户体验检查
    └── security.md     # 安全性检查
```

### 源代码(仓库根目录)

```
src/
├── client/              # 客户端模块
│   ├── main.py         # 客户端主入口
│   ├── nplt_client.py  # NPLT协议客户端
│   ├── rdt_client.py   # RDT协议客户端
│   └── ui.py           # Rich UI组件
├── server/              # 服务器模块
│   ├── main.py         # 服务器主入口
│   ├── nplt_server.py  # NPLT协议服务器
│   ├── rdt_server.py   # RDT协议服务器
│   └── agent.py        # ReAct Agent实现
├── llm/                 # LLM Provider模块
│   ├── base.py         # 抽象接口
│   └── zhipu.py        # 智谱AI实现
├── tools/               # 工具模块
│   ├── base.py         # 工具基类
│   ├── command.py      # 命令执行工具
│   ├── monitor.py      # 系统监控工具
│   └── rag.py          # RAG检索工具
├── storage/             # 存储模块
│   ├── history.py      # 对话历史
│   └── vector_store.py # 向量存储
├── protocols/           # 协议模块
│   └── nplt.py         # NPLT协议定义
└── utils/               # 工具模块
    ├── config.py       # 配置管理
    └── logger.py       # 日志工具

tests/
├── unit/                # 单元测试
├── integration/         # 集成测试
├── contract/            # 协议测试
└── performance/         # 性能测试

storage/                 # 运行时数据
├── vectors/            # 向量索引
├── history/            # 对话历史
└── uploads/            # 上传文件

logs/                    # 日志文件
```

**结构决策**: 单一项目结构，客户端和服务器共享协议和工具模块。这种结构便于代码复用和维护，符合小到中型项目的最佳实践。

## 复杂度跟踪

| 违规 | 为什么需要 | 拒绝更简单替代方案的原因 |
|-----------|------------|-------------------------------------|
| 自定义协议 (NPLT + RDT) | 需要特定的应用层消息传递和可靠的UDP文件传输 | 标准协议 (HTTP/WebSocket) 无法满足UDP文件传输的教学目标和特定的流式控制需求 |
| ReAct Agent 多轮工具调用 | 需要AI动态决定工具使用和推理链 | 单轮工具调用无法实现复杂的推理和任务分解能力 |
| 向量存储 + RAG | 需要对上传文件进行语义检索 | 关键词搜索无法提供语义理解和相关性排序 |

## 已知问题与修复

### 模型切换功能缺陷 (已发现，待修复)

**问题**: 服务器端的 `model_switch_callback` 未设置，导致模型切换请求发送后，LLM Provider 实际上不会切换模型。

**影响**: 用户执行 `/model glm-4.5-flash` 后，客户端状态更新但服务器仍使用原模型。

**修复方案**:
在 [src/server/main.py](src/server/main.py:122) 中添加：
```python
# 注册模型切换回调
self.nplt_server.model_switch_callback = self.llm_provider.set_model
```

**验证**: 需要添加测试用例验证模型切换确实生效 (参见FR-020)

## 下一步

### 阶段 0: 研究与技术选型

已完成的决策 (在 research.md 中记录):
- ✅ Python 3.11 + uv
- ✅ zai-sdk (智谱AI官方SDK)
- ✅ rich (CLI UI)
- ✅ 自定义NPLT协议 (TCP应用层)
- ✅ 自定义RDT协议 (UDP可靠传输)
- ✅ ReAct Agent模式

### 阶段 1: 设计与契约

待生成文档:
1. data-model.md - 实体和关系
2. contracts/nplt.md - NPLT协议规范
3. contracts/rdt.md - RDT协议规范
4. quickstart.md - 快速开始指南 (已生成)

### 阶段 2: 任务分解

运行 `/speckit.tasks` 生成详细的实施任务列表。
