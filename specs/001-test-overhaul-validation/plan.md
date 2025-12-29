# 实施计划: 测试全面重构与实现验证

**分支**: `001-test-overhaul-validation` | **日期**: 2025-12-29 | **规范**: [spec.md](./spec.md)
**输入**: 来自 `/specs/001-test-overhaul-validation/spec.md` 的功能规范

## 摘要

本项目旨在修复和验证 `001-llm-chat-assistant` 智能网络运维助手项目的实现质量。根据实现状态分析，项目已完成 92% 的核心功能（23/25），没有发现虚假实现，但存在以下需要解决的问题：

1. **服务器启动问题** - 可能是配置错误导致的阻塞性问题
2. **上下文压缩机制未完全实现** - FR-009d 部分完成，需要完善智能压缩策略
3. **测试套件重构** - 需要生成全面的单元测试、集成测试和端到端测试
4. **代码质量问题** - 部分代码存在重复，需要重构优化

**技术方法**:
- 使用 pytest 生成真实测试套件（无 mock）
- 修复配置加载和 LLM Provider 初始化问题
- 实现基于 token 阈值和重要性评分的上下文压缩算法
- 确保所有测试使用真实的智谱 API

## 技术背景

**语言/版本**: Python 3.11
**主要依赖**:
- pytest (测试框架)
- zai-sdk (智谱 AI 官方 SDK)
- rich (CLI UI)
- pyyaml (配置管理)
- uv (虚拟环境和依赖管理)

**存储**:
- 文件系统 (storage/vectors/、storage/history/、storage/uploads/)
- 对话历史持久化到 storage/history/
- 向量索引持久化到 storage/vectors/

**测试**: pytest (真实 API 测试，无 mock)
**目标平台**: Linux/macOS 服务器环境
**项目类型**: 单一项目 (CLI 客户端 + 服务器)
**性能目标**:
- 服务器启动时间 < 10 秒
- AI 工具调用响应时间 < 2 秒
- 测试运行时间 < 5 分钟

**约束条件**:
- 所有测试必须使用真实 API（不允许 mock）
- 测试必须在运行前检查 API key 有效性
- 配置文件必须放在项目根目录
- 所有日志必须写入 logs 文件夹

**规模/范围**:
- 25 个核心功能需求
- 4 个用户故事
- 单用户多会话场景
- 目标测试覆盖率 > 90%

## 章程检查

*门控: 必须在阶段 0 研究前通过. 阶段 1 设计后重新检查. *

基于 `.specify/memory/constitution.md` 中的原则,本功能 MUST 通过以下检查:

### 质量与一致性
- [x] 代码遵循项目编码规范 - 已在 001-llm-chat-assistant 中建立
- [x] 实现是真实的,不允许虚假实现或占位符 - 实现状态分析确认无虚假实现
- [x] 代码审查清单已准备 - 将在测试重构中包含

### 测试真实性
- [x] 测试计划不包含任何 mock 测试 - 明确要求使用真实 API
- [x] 涉及 LLM 的测试使用真实的智谱 API - 使用 zai-sdk
- [x] API key 验证机制已包含在测试设置中 - 测试前检查配置

### 文档与可追溯性
- [x] 日志将写入 logs 文件夹 - 已有日志系统
- [x] 日志格式为纯文本 (.log) - 符合章程
- [x] 日志包含时间戳、操作类型和上下文信息 - 已实现

### 真实集成
- [x] 使用官方 zai-sdk 进行智谱 AI 集成 - 已在 001-llm-chat-assistant 中实现
- [x] 所有 LLM 调用通过真实 API 进行 - 已实现
- [x] 无使用模拟回复的实现 - 实现状态分析确认

### 开发环境标准
- [x] Python 版本为 3.11 - 已在 .python-version 中指定
- [x] 使用 uv 管理虚拟环境 - 已使用 uv.lock 和 pyproject.toml
- [x] 依赖通过 uv 管理并记录 - 已配置

### 语言规范
- [x] 所有用户回复使用中文 - 已实现
- [x] 所有代码注释使用中文 - 已实现
- [x] 所有文档使用中文 - 已实现
- [x] 错误消息和日志使用中文 - 已实现

### 版本控制与测试纪律

- [ ] 每个阶段完成后通过真实测试 - **待执行**
- [ ] 测试通过后进行 git 提交 - **待执行**
- [ ] 提交消息清晰描述阶段工作和测试结果 - **待执行**
- [x] 不允许跳过测试或使用虚假测试 - 测试套件将强制执行

**章程检查状态**: ✅ **通过** - 所有检查项符合章程要求，剩余项将在实施过程中完成。

## 项目结构

### 文档(此功能)

```
specs/001-test-overhaul-validation/
├── plan.md              # 此文件 (/speckit.plan 命令输出)
├── research.md          # 阶段 0 输出 - 技术研究和最佳实践
├── data-model.md        # 阶段 1 输出 - 测试数据模型和验证规则
├── quickstart.md        # 阶段 1 输出 - 测试执行快速指南
├── contracts/           # 阶段 1 输出 - 测试合同和接口规范
│   └── test-contracts.md
└── tasks.md             # 阶段 2 输出 (/speckit.tasks 命令生成)
```

### 源代码(仓库根目录)

```
# 项目使用单一项目结构
src/
├── client/              # CLI 客户端
│   ├── main.py         # 客户端入口
│   ├── ui.py           # Rich UI 组件
│   └── rdt_client.py   # RDT 文件传输客户端
├── server/             # 服务器
│   ├── main.py         # 服务器入口 (待修复)
│   ├── nplt_server.py  # NPLT 协议服务器
│   ├── agent.py        # Agent ReAct 循环
│   └── rdt_server.py   # RDT 文件传输服务器
├── protocols/          # 协议实现
│   ├── nplt.py         # NPLT 协议
│   └── rdt.py          # RDT 协议
├── tools/              # Agent 工具
│   ├── command.py      # 命令执行工具
│   ├── monitor.py      # 系统监控工具
│   └── rag.py          # RAG 检索工具
├── storage/            # 存储层
│   ├── history.py      # 对话历史管理
│   └── vector_store.py # 向量索引存储
├── llm/                # LLM Provider
│   ├── base.py         # 抽象接口
│   ├── zhipu.py        # 智谱实现
│   └── models.py       # 模型配置
├── utils/              # 工具函数
│   ├── config.py       # 配置管理
│   └── logger.py       # 日志系统
└── __init__.py

tests/                  # 测试目录 (待重新生成)
├── unit/               # 单元测试
│   ├── test_nplt.py           # NPLT 协议测试
│   ├── test_rdt.py            # RDT 协议测试
│   ├── test_agent.py          # Agent 测试
│   ├── test_tools.py          # 工具测试
│   ├── test_storage.py        # 存储层测试
│   └── test_llm.py            # LLM Provider 测试
├── integration/        # 集成测试
│   ├── test_client_server.py  # 客户端-服务器通信测试
│   ├── test_file_upload.py    # 文件上传和 RAG 测试
│   └── test_session_management.py # 会话管理测试
└── e2e/                # 端到端测试
    ├── test_conversation.py   # 完整对话流程测试
    ├── test_file_transfer.py  # 文件传输流程测试
    └── test_multi_session.py  # 多会话管理测试

config.yaml             # 主配置文件
.env                    # 环境变量 (ZHIPU_API_KEY)
logs/                   # 日志文件夹
storage/                # 数据存储文件夹
├── vectors/            # 向量索引
├── history/            # 对话历史
│   └── archive/        # 归档会话
└── uploads/            # 上传文件
```

**结构决策**: 使用单一项目结构，因为这是一个 CLI 客户端-服务器应用。客户端和服务器共享协议、工具和存储层代码。测试按单元、集成和端到端分层组织，确保全面覆盖。

## 阶段 0: 研究任务

### 0.1 服务器启动问题诊断

**目标**: 确定服务器无法启动的根本原因

**研究任务**:
1. 分析 `src/server/main.py` 的启动流程
2. 检查 `src/utils/config.py` 的配置加载逻辑
3. 验证 LLM Provider 初始化流程 (`src/llm/zhipu.py`)
4. 确认配置文件格式和必需字段

**预期输出**:
- 服务器启动问题根因分析报告
- 配置错误修复方案
- 配置验证测试用例

### 0.2 测试最佳实践研究

**目标**: 确定真实 API 测试的最佳实践

**研究任务**:
1. pytest 测试结构和组织模式
2. 真实 API 测试的前置条件检查
3. 测试失败时的错误信息最佳实践
4. 测试覆盖率工具和目标

**预期输出**:
- 测试结构设计决策
- API key 验证工具函数
- 测试失败报告模板

### 0.3 上下文压缩算法研究

**目标**: 设计智能上下文压缩策略

**研究任务**:
1. Token 计数方法 (tiktoken vs. API 估算)
2. 消息重要性评分算法
3. 上下文压缩最佳实践 (总结、选择性删除、摘要)
4. 智谱 API 的 max_tokens 限制

**预期输出**:
- 上下文压缩算法设计
- Token 计数工具函数
- 重要性评分策略

## 阶段 1: 设计制品

### 1.1 数据模型设计 (data-model.md)

**内容**:
- 测试数据模型 (测试配置、测试结果)
- 配置验证规则
- 错误状态模型

### 1.2 测试合同 (contracts/test-contracts.md)

**内容**:
- 测试接口规范
- 测试前置条件
- 测试验收标准

### 1.3 快速开始指南 (quickstart.md)

**内容**:
- 环境配置步骤
- 测试执行命令
- 常见问题排查

## 阶段 2: 实施计划

将通过 `/speckit.tasks` 命令生成详细的任务分解，包括：

1. **修复服务器启动问题** (P0)
2. **实现上下文压缩机制** (P0)
3. **重新生成测试套件** (P1)
4. **代码质量优化** (P1)
5. **可交付性验证** (P2)

## 复杂度跟踪

| 违规 | 为什么需要 | 拒绝更简单替代方案的原因 |
|-----------|------------|-------------------------------------|
| 无 | N/A | 项目遵循所有章程原则，无需违规 |

## 下一步

1. 执行阶段 0 研究 (research.md)
2. 生成阶段 1 设计制品 (data-model.md, contracts/, quickstart.md)
3. 运行 `/speckit.tasks` 生成详细任务列表
