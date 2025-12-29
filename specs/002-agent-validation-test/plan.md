# 实施计划: Agent功能全面验证测试

**分支**: `002-agent-validation-test` | **日期**: 2025-12-29 | **规范**: [spec.md](spec.md)
**输入**: 来自 `/specs/002-agent-validation-test/spec.md` 的功能规范

## 摘要

本功能旨在为后端已开发的Agent功能创建全面的验证测试框架。主要需求包括：使用真实智谱API（glm-4-flash模型）进行测试，生成详细的测试报告（包含输入、完整工具链调用、结果），并按照优先级逐步验证10个用户故事。技术方法将基于现有的pytest测试框架，扩展tests/integration/test_agent.py，创建新的tests/validation目录，实现结构化的测试报告生成器和用户确认驱动的测试执行流程。

## 技术背景

**语言/版本**: Python 3.11
**主要依赖**: pytest、asyncio、zai-sdk、pydantic
**存储**: 文件系统（测试报告存储到 specs/002-agent-validation-test/reports/）
**测试**: pytest (真实测试，无mock)
**目标平台**: Linux服务器（与现有Agent代码一致）
**项目类型**: 测试框架扩展（集成测试）
**性能目标**:
  - 工具调用响应时间（从用户输入到工具状态显示）< 2秒（90%的情况下）
  - 工具执行时间（单个工具运行）< 5秒（超时限制）
**约束条件**:
  - 必须使用真实的智谱API，不允许mock
  - 必须在测试前验证ZHIPU_API_KEY环境变量已配置
  - 每个测试完成后必须等待用户确认才能继续
  - 测试报告必须包含完整的工具链调用信息
**规模/范围**:
  - 10个测试用例（T001-T010）
  - 覆盖P1、P2、P3三个优先级
  - 验证3个核心工具（command_executor、sys_monitor、rag_search）
  - 验证Agent的ReAct循环、对话管理、错误处理、模型切换等功能

## 章程检查

*门控: 必须在阶段 0 研究前通过. 阶段 1 设计后重新检查. *

基于 `.specify/memory/constitution.md` 中的原则,本功能 MUST 通过以下检查:

### 质量与一致性
- [x] 代码遵循项目编码规范 - 将继承现有测试代码风格
- [x] 实现是真实的,不允许虚假实现或占位符 - 测试框架将使用真实Agent和真实API
- [x] 代码审查清单已准备 - 将在tasks.md中包含审查任务

### 测试真实性
- [x] 测试计划不包含任何 mock 测试 - 明确要求使用真实智谱API
- [x] 涉及 LLM 的测试使用真实的智谱 API - 使用zai-sdk和glm-4-flash
- [x] API key 验证机制已包含在测试设置中 - 将在测试初始化时验证ZHIPU_API_KEY

### 文档与可追溯性
- [x] 日志将写入 logs 文件夹 - 测试日志将写入logs/test_validation.log
- [x] 日志格式为纯文本 (.log) - 测试日志和报告都是纯文本/Markdown格式
- [x] 日志包含时间戳、操作类型和上下文信息 - 测试报告将包含详细的执行信息

### 真实集成
- [x] 使用官方 zai-sdk 进行智谱 AI 集成 - 复用现有src/llm/zhipu.py
- [x] 所有 LLM 调用通过真实 API 进行 - 测试将调用真实的智谱API
- [x] 无使用模拟回复的实现 - 测试框架将记录真实的API响应

### 开发环境标准
- [x] Python 版本为 3.11 - 与项目要求一致
- [x] 使用 uv 管理虚拟环境 - 与项目现有方式一致
- [x] 依赖通过 uv 管理并记录 - 无需新增依赖，复用现有pytest、zai-sdk

### 语言规范
- [x] 所有用户回复使用中文 - 测试报告和输出使用中文
- [x] 所有代码注释使用中文 - 代码注释使用中文
- [x] 所有文档使用中文 - 测试报告和文档使用中文
- [x] 错误消息和日志使用中文 - 测试框架输出的错误消息使用中文

### 版本控制与测试纪律

- [x] 每个阶段完成后通过真实测试 - 将使用真实API执行测试
- [x] 测试通过后进行 git 提交 - 每个测试阶段通过后提交
- [x] 提交消息清晰描述阶段工作和测试结果 - 提交消息包含测试通过状态
- [x] 不允许跳过测试或使用虚假测试 - 强制使用真实API和真实Agent

### 安全第一原则
- [x] 文件访问使用统一的路径白名单控制 - 测试将验证Agent的PathValidator
- [x] 白名单配置存储在 config.yaml 的 file_access.allowed_paths - 测试将使用现有配置
- [x] 路径验证器防止路径遍历攻击（../ 规范化） - 测试将包含路径遍历攻击场景
- [x] 黑名单模式保护敏感文件（.env、.ssh/*、/etc/passwd 等） - 测试将验证黑名单功能
- [x] 任何工具不绕过白名单访问文件系统 - 测试将验证CommandTool的安全机制

### 自动化与按需索引
- [x] RAG 工具支持按需索引（execute_async 方法） - 测试将验证RAGTool的自动索引
- [x] 索引管理器使用懒加载策略，避免重复索引 - 测试将验证索引不会重复创建
- [x] 索引持久化存储到 storage/vectors/ 目录 - 测试将验证索引持久化
- [x] 索引创建验证文件类型（仅文本文件）和大小（最大 10MB） - 测试将包含文件类型和大小验证
- [x] 系统重启后自动加载已持久化的索引 - 测试将验证IndexManager的加载机制

### 多层防御策略
- [x] 文件访问依次通过白名单、黑名单、大小限制、内容类型验证 - 测试将验证多层防御
- [x] 命令执行限制输出大小（默认最大 100KB） - 测试将验证CommandTool的输出限制
- [x] 命令参数验证黑名单字符（;, &, |, >, <, `, $, (, ), \n, \r） - 测试将验证命令黑名单
- [x] 正则表达式搜索验证复杂度，防止 ReDoS 攻击 - 测试将包含正则复杂度场景（如果适用）
- [x] Glob 模式匹配限制最大文件数（默认 100 个） - 测试将验证glob限制

### 可审计性与透明性
- [x] 所有文件访问操作记录日志 - 测试报告将记录工具调用的详细信息
- [x] 所有索引创建记录详细信息（文件路径、分块数量、创建时间） - 测试将验证索引创建日志
- [x] 所有工具调用记录执行状态、持续时间 - 测试报告将包含每个工具调用的状态和时间
- [x] 文件访问被拒绝时返回明确的拒绝理由 - 测试将验证错误消息的明确性
- [x] 提供索引状态查询接口 - 测试将验证RAGTool的状态查询功能

**章程检查状态**: ✅ 全部通过

## 项目结构

### 文档(此功能)

```
specs/002-agent-validation-test/
├── plan.md              # 此文件 (/speckit.plan 命令输出)
├── research.md          # 阶段 0 输出 (/speckit.plan 命令)
├── data-model.md        # 阶段 1 输出 (/speckit.plan 命令)
├── quickstart.md        # 阶段 1 输出 (/speckit.plan 命令)
├── contracts/           # 阶段 1 输出 (/speckit.plan 命令)
│   └── test-report-schema.md  # 测试报告格式契约
├── reports/             # 测试报告输出目录
│   ├── T001-基础对话.md
│   ├── T002-系统监控.md
│   └── ...
└── tasks.md             # 阶段 2 输出 (/speckit.tasks 命令)
```

### 源代码(仓库根目录)

```
tests/
├── validation/          # 新增：Agent功能验证测试
│   ├── __init__.py
│   ├── conftest.py      # pytest配置和fixtures
│   ├── test_agent_validation.py  # 主测试文件
│   ├── test_framework.py  # 测试框架基础类
│   └── test_reporter.py    # 测试报告生成器
├── integration/         # 现有：集成测试
│   └── test_agent.py    # 现有Agent测试（将被复用）
├── unit/                # 现有：单元测试
├── contract/            # 现有：契约测试
└── performance/         # 现有：性能测试

src/
├── server/
│   └── agent.py         # 现有：ReActAgent实现（被测试对象）
├── llm/
│   └── zhipu.py         # 现有：ZhipuProvider（被测试对象）
├── tools/               # 现有：工具实现（被测试对象）
│   ├── command.py
│   ├── monitor.py
│   └── rag.py
└── storage/             # 现有：存储模块（被测试对象）

logs/
└── test_validation.log  # 测试日志文件
```

**结构决策**: 选择单一项目结构，因为这是一个测试功能扩展，不需要新的前端或后端服务。测试框架将作为tests/validation目录添加到现有的测试结构中，复用现有的pytest配置和测试工具。测试报告将输出到specs/002-agent-validation-test/reports/目录，作为功能验证文档的一部分。

## 阶段 0: 研究与决策

### 研究任务清单

由于本功能是测试验证，技术栈已经明确（Python 3.11, pytest, zai-sdk），无需重大技术决策。但需要研究以下方面：

1. **pytest异步测试最佳实践** - 如何组织异步测试（asyncio）、如何使用fixtures
2. **测试报告格式** - Markdown报告的最佳结构、如何嵌入代码片段和表格
3. **用户确认流程** - 如何在测试过程中实现"用户确认"机制（可能需要交互式输入）
4. **性能指标收集** - 如何准确测量工具调用响应时间、工具执行时间
5. **测试数据隔离** - 如何确保测试之间的独立性和数据隔离

### 研究方法

- 查阅现有tests/integration/test_agent.py的测试模式
- 参考pytest官方文档关于异步测试和fixtures的最佳实践
- 分析现有Agent代码中的ToolCall数据结构，确保测试报告能准确捕获所有信息

## 阶段 1: 设计

### 数据模型

将在 data-model.md 中定义以下实体：

1. **TestCase（测试用例）** - 测试的基本单位
2. **TestReport（测试报告）** - 汇总测试结果
3. **ToolCallRecord（工具调用记录）** - 从ToolCall转换的记录结构
4. **PerformanceMetrics（性能指标）** - 响应时间、执行时间等
5. **ValidationResult（验证结果）** - 验收场景的通过/失败状态

### API合约

将在 contracts/ 中定义：

1. **test-report-schema.md** - 测试报告的Markdown格式规范
2. **test-framework-interface.md** - 测试框架的接口定义（如TestRunner、TestReporter类）

### 快速开始指南

将在 quickstart.md 中提供：

1. 环境准备（设置ZHIPU_API_KEY）
2. 运行单个测试
3. 运行所有测试
4. 查看测试报告
5. 调试测试失败

## 阶段 2: 任务分解（未完成）

阶段2将在 `/speckit.tasks` 命令中完成，将生成详细的tasks.md文件，包含：

- 基础设施任务（设置测试框架、报告生成器）
- P1测试实现任务（T001-T004）
- P2测试实现任务（T005-T009）
- P3测试实现任务（T010）
- 文档和验收任务

## 复杂度跟踪

*无章程违规，此部分为空*

## 下一步行动

1. ✅ 完成计划模板填充
2. ⏳ 执行阶段0：生成research.md
3. ⏳ 执行阶段1：生成data-model.md、contracts/、quickstart.md
4. ⏳ 更新代理上下文（运行update-agent-context.sh）
5. ⏳ 重新评估章程检查
6. ⏳ 报告完成情况并等待用户确认进入阶段2（/speckit.tasks）
