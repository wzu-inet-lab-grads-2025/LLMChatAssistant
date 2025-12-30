# 实施计划: 文件操作工具集成到 Agent

**分支**: `003-file-tools-integration` | **日期**: 2025-12-30 | **规范**: [spec.md](spec.md)
**输入**: 来自 `/specs/003-file-tools-integration/spec.md` 的功能规范

## 摘要

本功能旨在为 ReAct Agent 添加三个新的文件操作工具（文件上传、文件下载、文件语义检索），并实现工具串行调用能力。主要需求包括：用户可以上传文件到服务器并自动建立索引、Agent 可以将服务器文件发送给用户、支持自然语言语义检索文件、以及多步骤操作的串行工具调用（如先搜索再下载）。技术方法将基于现有的 ReAct Agent 框架，创建三个新的工具类（FileUploadTool、FileDownloadTool、FileSemanticSearchTool），集成到现有的工具注册表，并更新 Agent 提示词以支持文件操作场景。

## 技术背景

**语言/版本**: Python 3.11
**主要依赖**: pytest、asyncio、zai-sdk、pydantic
**存储**: 文件系统（storage/uploads/ 用于文件存储，storage/vectors/ 用于向量索引）
**测试**: pytest (真实测试，无mock)
**目标平台**: Linux服务器（与现有Agent代码一致）
**项目类型**: 单一项目（后端功能扩展）
**性能目标**:
  - 文件上传（含索引）：5MB文件在 30秒内完成
  - 文件下载：5MB文件在 20秒内完成
  - 语义检索：90%的请求在 3秒内返回结果
  - 串行工具调用：检索+下载在 10秒内完成
**约束条件**:
  - 必须使用真实的智谱API，不允许mock
  - 文件大小限制 10MB
  - 仅支持文本文件类型
  - ReAct循环限制最多5轮工具调用
  - 必须使用现有的PathValidator进行路径验证
  - 必须复用现有的NPLT协议进行文件传输
**规模/范围**:
  - 3个新工具（FileUploadTool、FileDownloadTool、FileSemanticSearchTool）
  - 1个Agent提示词更新
  - 5个用户故事（P1: 3个，P2: 1个，P3: 1个）
  - 复用现有：VectorStore、IndexManager、PathValidator、NPLT协议

## 章程检查

*门控: 必须在阶段 0 研究前通过. 阶段 1 设计后重新检查. *

基于 `.specify/memory/constitution.md` 中的原则,本功能 MUST 通过以下检查:

### 质量与一致性
- [x] 代码遵循项目编码规范 - 将继承现有工具代码风格（src/tools/）
- [x] 实现是真实的,不允许虚假实现或占位符 - 将实现真实的文件操作和真实API调用
- [x] 代码审查清单已准备 - 将在tasks.md中包含审查任务

### 测试真实性
- [x] 测试计划不包含任何 mock 测试 - 明确要求使用真实文件和真实智谱API
- [x] 涉及 LLM 的测试使用真实的智谱 API - 使用zai-sdk和glm-4-flash
- [x] API key 验证机制已包含在测试设置中 - 将在测试初始化时验证ZHIPU_API_KEY

### 文档与可追溯性
- [x] 日志将写入 logs 文件夹 - 文件操作日志将写入logs/file_operations.log
- [x] 日志格式为纯文本 (.log) - 所有日志都是纯文本格式
- [x] 日志包含时间戳、操作类型和上下文信息 - 日志将记录文件路径、操作类型、执行结果

### 真实集成
- [x] 使用官方 zai-sdk 进行智谱 AI 集成 - 复用现有src/llm/zhipu.py
- [x] 所有 LLM 调用通过真实 API 进行 - 将调用真实的智谱API进行Embedding
- [x] 无使用模拟回复的实现 - 所有文件检索将使用真实的向量索引

### 开发环境标准
- [x] Python 版本为 3.11 - 与项目要求一致
- [x] 使用 uv 管理虚拟环境 - 与项目现有方式一致
- [x] 依赖通过 uv 管理并记录 - 无需新增依赖，复用现有pytest、zai-sdk

### 语言规范
- [x] 所有用户回复使用中文 - 文件操作错误消息和提示使用中文
- [x] 所有代码注释使用中文 - 代码注释使用中文
- [x] 所有文档使用中文 - 测试报告和文档使用中文
- [x] 错误消息和日志使用中文 - 文件操作错误消息使用中文

### 版本控制与测试纪律

- [x] 每个阶段完成后通过真实测试 - 将使用真实文件和真实API执行测试
- [x] 测试通过后进行 git 提交 - 每个工具实现完成后提交
- [x] 提交消息清晰描述阶段工作和测试结果 - 提交消息包含测试通过状态
- [x] 不允许跳过测试或使用虚假测试 - 强制使用真实文件和真实API

### 安全第一原则
- [x] 文件访问使用统一的路径白名单控制 - FileDownloadTool将使用PathValidator
- [x] 白名单配置存储在 config.yaml 的 file_access.allowed_paths - 复用现有配置
- [x] 路径验证器防止路径遍历攻击（../ 规范化） - 使用现有PathValidator
- [x] 黑名单模式保护敏感文件（.env、.ssh/*、/etc/passwd 等） - PathValidator已包含黑名单
- [x] 任何工具不绕过白名单访问文件系统 - 所有文件操作必须通过PathValidator

### 自动化与按需索引
- [x] RAG 工具支持按需索引（execute_async 方法） - FileSemanticSearchTool将复用RAGTool
- [x] 索引管理器使用懒加载策略，避免重复索引 - 使用现有IndexManager
- [x] 索引持久化存储到 storage/vectors/ 目录 - 使用现有VectorStore
- [x] 索引创建验证文件类型（仅文本文件）和大小（最大 10MB） - 复用现有验证逻辑
- [x] 系统重启后自动加载已持久化的索引 - VectorStore已支持持久化

### 多层防御策略
- [x] 文件访问依次通过白名单、黑名单、大小限制、内容类型验证 - FileUploadTool和FileDownloadTool将实现
- [x] 命令执行限制输出大小（默认最大 100KB） - 不涉及命令执行，但文件传输限制大小
- [x] 命令参数验证黑名单字符（;, &, |, >, <, `, $, (, ), \n, \r） - 文件路径验证使用PathValidator
- [x] 正则表达式搜索验证复杂度，防止 ReDoS 攻击 - 不涉及正则搜索
- [x] Glob 模式匹配限制最大文件数（默认 100 个） - 使用现有Glob限制

### 可审计性与透明性
- [x] 所有文件访问操作记录日志 - 文件操作将记录到logs/file_operations.log
- [x] 所有索引创建记录详细信息（文件路径、分块数量、创建时间） - 使用现有IndexManager日志
- [x] 所有工具调用记录执行状态、持续时间 - 工具执行结果包含duration和status
- [x] 文件访问被拒绝时返回明确的拒绝理由 - PathValidator返回明确的拒绝消息
- [x] 提供索引状态查询接口 - FileSemanticSearchTool提供索引状态查询

**章程检查状态**: ✅ 全部通过

## 项目结构

### 文档(此功能)

```
specs/003-file-tools-integration/
├── plan.md              # 此文件 (/speckit.plan 命令输出)
├── research.md          # 阶段 0 输出 (/speckit.plan 命令)
├── data-model.md        # 阶段 1 输出 (/speckit.plan 命令)
├── quickstart.md        # 阶段 1 输出 (/speckit.plan 命令)
├── contracts/           # 阶段 1 输出 (/speckit.plan 命令)
│   └── file-tools-interface.md  # 文件工具接口定义
└── tasks.md             # 阶段 2 输出 (/speckit.tasks 命令 - 非 /speckit.plan 创建)
```

### 源代码(仓库根目录)

```
src/
├── tools/               # 现有：工具实现
│   ├── base.py          # 工具基类（Tool、ToolExecutionResult）
│   ├── command.py       # 现有：命令执行工具
│   ├── monitor.py       # 现有：系统监控工具
│   ├── rag.py           # 现有：RAG检索工具
│   ├── file_upload.py   # 新增：文件上传工具
│   ├── file_download.py # 新增：文件下载工具
│   └── file_search.py   # 新增：文件语义检索工具
├── server/
│   └── agent.py         # 现有：ReActAgent实现（需要更新工具注册和提示词）
├── protocols/
│   └── nplt.py          # 现有：NPLT协议（已支持文件传输消息类型）
├── storage/
│   ├── files.py         # 现有：UploadedFile数据类
│   ├── vector_store.py  # 现有：向量存储
│   └── index_manager.py # 现有：索引管理器
└── utils/
    └── path_validator.py # 现有：路径验证器

tests/
├── integration/         # 现有：集成测试
│   └── test_agent.py    # 现有Agent测试
├── validation/          # 现有：功能验证测试
│   └── test_agent_validation.py
├── unit/
│   └── tools/           # 新增：文件工具单元测试
│       ├── test_file_upload.py
│       ├── test_file_download.py
│       └── test_file_search.py
└── integration/         # 新增：文件工具集成测试
    └── test_file_tools_integration.py

logs/
└── file_operations.log  # 新增：文件操作日志

storage/
└── uploads/             # 现有：上传文件存储目录
    └── {file_id}/
        ├── {filename}
        └── metadata.json
```

**结构决策**: 选择单一项目结构，因为这是后端功能的扩展，不需要新的前端或服务。文件工具将作为新的模块添加到 `src/tools/` 目录，复用现有的工具基类和基础设施（PathValidator、VectorStore、IndexManager）。测试将添加到现有的测试结构中，包括单元测试和集成测试。

## 复杂度跟踪

*无章程违规，此部分为空*
