# 实施计划: CLI客户端重构与验证

**分支**: `001-cli-client-refactor` | **日期**: 2026-01-01 | **规范**: [spec.md](./spec.md)
**输入**: 来自 `/specs/001-cli-client-refactor/spec.md` 的功能规范

## 摘要

本功能旨在重构CLI客户端代码，从 `src/client/` 移至独立的顶层 `clients/cli/` 目录，建立支持多客户端（CLI、Desktop、Web）的架构。实施过程分为三个主要阶段：

1. **验证与修复阶段**：使用真实后端API和智谱AI真实接口全面验证现有12项CLI功能，识别并修复所有问题
2. **重构阶段**：执行目录结构重构，实现客户端独立部署能力
3. **回归测试阶段**：验证重构后功能完整性，确保无回归

**核心原则**：所有测试必须使用真实后端功能和真实大模型接口，禁止任何形式的mock测试或虚假实现。

## 技术背景

**语言/版本**: Python 3.11 (通过 uv 管理)
**主要依赖**:
- asyncio: 异步编程框架
- rich: CLI终端UI库
- zai-sdk: 智谱AI官方SDK (使用真实API)
- pytest: 测试框架 (禁止使用mock)
- pyyaml: 配置文件解析

**通信协议**:
- NPLT (Network Protocol for LLM Transport): 基于TCP的自定义二进制协议，用于聊天和控制
- RDT (Reliable Data Transfer): 基于UDP的可靠数据传输协议，用于文件传输

**存储**:
- 文件系统: logs/ (日志)、storage/ (数据)、storage/vectors/ (向量索引)
- 配置: config.yaml (YAML格式)

**测试**:
- pytest: 单元测试和集成测试框架
- 真实测试要求: 禁止使用mock，所有LLM调用必须使用智谱API (glm-4-flash或glm-4.5-flash)
- API key验证: 测试前必须验证ZHIPU_API_KEY已配置

**目标平台**:
- CLI客户端: Linux/macOS/Windows (Python直接运行)
- 服务器: Linux服务器 (Docker容器可选)
- 未来Desktop客户端: Windows (PyInstaller打包为.exe)

**项目类型**: 单仓库多包 (monorepo) - 客户端和服务器在同一仓库，但独立部署

**性能目标**:
- 连接建立: <2秒
- 聊天响应首字: <500ms (流式输出)
- 文件传输速度: >10MB/s (本地网络，RDT协议)
- UI渲染: 60fps (Rich终端UI)
- 重构后性能: 与重构前差异<10%

**约束条件**:
- 测试真实性: 100%真实测试，零mock
- 章程合规: 必须符合项目章程v1.6.0的所有原则
- 客户端独立: 客户端代码不依赖src/目录中的服务器代码
- 协议同步: 客户端和服务器协议定义保持同步
- 独立部署: 客户端可独立打包和分发

**规模/范围**:
- 现有代码: 约3000行Python代码 (客户端)
- 重构文件: 5个主要模块 + 测试文件
- 测试场景: 12项核心功能 × 多种边界情况
- 文档更新: README、架构文档、API文档

## 章程检查

*门控: 必须在阶段 0 研究前通过. 阶段 1 设计后重新检查. *

基于 `.specify/memory/constitution.md` 中的原则,本功能 MUST 通过以下检查:

### 质量与一致性
- [x] 代码遵循项目编码规范 (Python PEP 8 + 中文注释)
- [x] 实现是真实的,不允许虚假实现或占位符
- [x] 代码审查清单已准备 (包含重构审查项)

### 测试真实性
- [x] **测试计划不包含任何 mock 测试** (核心要求)
- [x] **涉及 LLM 的测试使用真实的智谱 API** (使用 glm-4-flash)
- [x] API key 验证机制已包含在测试设置中 (启动前验证ZHIPU_API_KEY)

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

### 安全第一原则
- [x] 文件访问使用统一的路径白名单控制
- [x] 白名单配置存储在 config.yaml 的 file_access.allowed_paths
- [x] 路径验证器防止路径遍历攻击（../ 规范化）
- [x] 黑名单模式保护敏感文件（.env、.ssh/*、/etc/passwd 等）
- [x] 任何工具不绕过白名单访问文件系统

### 自动化与按需索引
- [x] RAG 工具支持按需索引（execute_async 方法）
- [x] 索引管理器使用懒加载策略，避免重复索引
- [x] 索引持久化存储到 storage/vectors/ 目录
- [x] 索引创建验证文件类型（仅文本文件）和大小（最大 10MB）
- [x] 系统重启后自动加载已持久化的索引

### 多层防御策略
- [x] 文件访问依次通过白名单、黑名单、大小限制、内容类型验证
- [x] 命令执行限制输出大小（默认最大 100KB）
- [x] 命令参数验证黑名单字符（;, &, |, >, <, `, $, (, ), \n, \r）
- [x] 正则表达式搜索验证复杂度，防止 ReDoS 攻击
- [x] Glob 模式匹配限制最大文件数（默认 100 个）

### 可审计性与透明性
- [x] 所有文件访问操作记录日志
- [x] 所有索引创建记录详细信息（文件路径、分块数量、创建时间）
- [x] 所有工具调用记录执行状态、持续时间
- [x] 文件访问被拒绝时返回明确的拒绝理由
- [x] 提供索引状态查询接口

### 客户端独立性原则 (v1.6.0新增)
- [x] 客户端包含独立的协议定义副本 (clients/cli/protocols/)
- [x] 客户端不依赖src/protocols/中的服务器代码
- [x] 客户端有独立的依赖管理 (clients/cli/pyproject.toml)
- [x] 客户端能够独立安装和部署
- [x] 协议版本检查机制验证兼容性

### 多前端适配器模式原则 (v1.6.0新增)
- [x] 支持CLI、Web、Desktop三种前端类型
- [x] Web前端由服务器直接提供
- [x] CLI客户端使用Python直接运行
- [x] Desktop客户端使用PyInstaller打包成.exe
- [x] 使用适配器模式解耦前端和后端
- [x] 前端应用层依赖适配器层，适配器层依赖服务层

### 配置驱动部署原则 (v1.6.0新增)
- [x] 通过config.yaml管理部署配置
- [x] 支持多层查找（命令行、当前目录、用户目录、默认配置）
- [x] 配置包含服务器连接参数（host、port）
- [x] 包含配置文件模板（config.yaml.example）
- [x] 启动时加载配置并验证

**章程合规状态**: ✅ 所有检查项通过，可以开始实施

## 项目结构

### 文档(此功能)

```
specs/001-cli-client-refactor/
├── plan.md              # 此文件 (/speckit.plan 命令输出)
├── research.md          # 阶段 0 输出 (/speckit.plan 命令)
├── data-model.md        # 阶段 1 输出 (/speckit.plan 命令)
├── quickstart.md        # 阶段 1 输出 (/speckit.plan 命令)
├── contracts/           # 阶段 1 输出 (/speckit.plan 命令)
│   ├── client-api.yaml  # 客户端API契约
│   └── test-scenarios.yaml # 测试场景契约
└── tasks.md             # 阶段 2 输出 (/speckit.tasks 命令)
```

### 源代码(重构后结构)

**结构决策**: 采用单仓库多包（monorepo）架构，客户端、服务器、共享代码分离到顶层目录，支持独立部署。

**当前结构** (重构前):
```
project-root/
├── src/
│   ├── client/          # ❌ 客户端代码混在src中
│   ├── server/          # ❌ 服务器代码混在src中
│   ├── protocols/       # ❌ 协议定义在src中
│   ├── tools/           # ✅ 服务器端工具
│   ├── utils/           # ❌ 工具函数在src中
│   ├── storage/         # ❌ 存储模块在src中
│   └── llm/             # ❌ LLM接口在src中
├── tests/               # ❌ 测试混合在一起
├── config.yaml
└── requirements.txt
```

**目标结构** (重构后):
```
project-root/
├── clients/             # ✅ 所有客户端代码（顶层目录）
│   ├── cli/             # ✅ CLI客户端
│   │   ├── main.py      # 客户端入口
│   │   ├── ui.py        # CLI界面
│   │   ├── nplt_client.py # NPLT协议客户端
│   │   ├── rdt_client.py  # RDT传输客户端
│   │   ├── protocols/   # ✅ 独立的协议定义副本
│   │   │   ├── nplt.py
│   │   │   └── rdt.py
│   │   ├── services/    # ✅ 客户端服务层
│   │   ├── config/      # ✅ 客户端配置
│   │   │   ├── config.yaml
│   │   │   └── config.yaml.example
│   │   ├── tests/       # ✅ 客户端专用测试
│   │   └── pyproject.toml # ✅ 独立依赖管理
│   ├── desktop/         # ⏳ 未来Desktop客户端（预留）
│   └── web/             # ⏳ 未来Web客户端（由服务器提供）
├── server/              # ✅ 服务器代码（从src/server移动）
│   ├── main.py
│   ├── agent.py
│   ├── http_server.py
│   ├── nplt_server.py
│   ├── rdt_server.py
│   ├── tests/           # ✅ 服务器专用测试
│   └── protocols/       # ✅ 服务器端协议定义
│       ├── nplt.py
│       └── rdt.py
├── shared/              # ✅ 共享代码（从src移动）
│   ├── utils/           # 工具函数
│   ├── storage/         # 存储模块
│   ├── llm/             # LLM接口
│   └── tests/           # 共享模块测试
├── src/                 # ✅ 保留用于纯服务器端工具
│   └── tools/           # 服务器端工具（file_upload、semantic_search等）
├── tests/               # ✅ 跨模块集成测试
├── logs/                # 日志目录
├── storage/             # 数据目录
│   └── vectors/         # 向量索引
├── docs/                # 文档目录
│   ├── architecture.md  # 架构文档
│   └── client-guide.md  # 客户端使用指南
├── config.yaml          # 服务器配置（保留）
├── requirements.txt     # 服务器依赖（保留）
├── pyproject.toml       # 项目配置（保留）
└── README.md            # 项目文档（需更新）
```

**重构原则**:
1. **客户端独立**: clients/cli/ 包含完整的协议定义副本，不依赖 src/
2. **协议同步**: 客户端和服务器协议定义必须保持同步，通过版本检查验证
3. **测试分离**: 客户端测试在 clients/cli/tests/，服务器测试在 server/tests/
4. **文档更新**: 更新 README.md 反映新目录结构

## 复杂度跟踪

*仅在章程检查有必须证明的违规时填写*

| 违规 | 为什么需要 | 拒绝更简单替代方案的原因 |
|-----------|------------|-------------------------------------|
| 无 | 无违规 | 此重构完全符合项目章程v1.6.0的所有原则 |

**复杂度评估**: 低-中等
- 重构主要是文件移动和导入路径更新，不涉及重写核心逻辑
- 现有代码质量良好，符合工程标准
- 章程v1.6.0已定义清晰的客户端架构原则

## 阶段 0: 大纲与研究

### 研究任务

由于技术上下文已知且架构已在章程v1.6.0中定义，阶段0研究任务已完成。主要结论：

**决策记录**:

1. **客户端独立架构** (Decision: 采用独立的协议定义副本)
   - **理由**: 支持客户端独立部署，无需整个服务器代码库
   - **替代方案**: 使用共享协议定义 (被拒绝，因为会导致部署复杂度增加)
   - **实施**: 客户端复制 protocols/nplt.py 和 protocols/rdt.py 到 clients/cli/protocols/

2. **测试策略** (Decision: 100%真实测试，零mock)
   - **理由**: 确保CLI客户端与真实后端API和智谱AI的集成正确性
   - **替代方案**: 使用mock模拟后端 (被章程明确禁止)
   - **实施**: 所有测试使用真实服务器和真实智谱API (glm-4-flash)

3. **重构顺序** (Decision: 先验证修复，再重构，最后回归测试)
   - **理由**: 确保重构基线稳定，避免将已知问题带入重构后的代码
   - **替代方案**: 直接重构再测试 (被拒绝，风险高，难以区分重构引入的问题和原有问题)
   - **实施**: 三个阶段顺序执行，每阶段完成并测试通过后提交

4. **目录组织** (Decision: clients/, server/, shared/ 顶层分离)
   - **理由**: 清晰的模块边界，支持独立部署，符合monorepo最佳实践
   - **替代方案**: 保持在src/下 (被拒绝，不符合客户端独立原则)
   - **实施**: 创建新的顶层目录，移动文件，更新所有导入路径

5. **协议版本管理** (Decision: 客户端和服务器协议独立定义，版本检查验证兼容性)
   - **理由**: 允许独立演进，防止不匹配的客户端和服务器通信失败
   - **替代方案**: 共享协议定义 (被拒绝，违背客户端独立原则)
   - **实施**: 在协议定义中添加版本号，连接时验证

**详细研究内容**: 参见 [research.md](./research.md)

## 阶段 1: 设计与合同

### 数据模型

本功能主要涉及目录结构重构，不引入新的数据实体。主要数据模型已存在于现有代码中：

**会话数据模型** (Session):
```python
Session {
    session_id: str           # 会话唯一标识
    client_type: str          # 客户端类型: "cli" | "web" | "desktop"
    user_id: str              # 用户标识
    created_at: datetime      # 创建时间
    messages: List[Message]   # 消息历史
    uploaded_files: List[FileMetadata]  # 已上传文件
    current_model: str        # 当前使用的模型 (e.g., "glm-4-flash")
}
```

**消息数据模型** (Message):
```python
Message {
    role: str                 # "user" | "assistant" | "system"
    content: str              # 消息内容
    timestamp: datetime       # 时间戳
    tool_calls: List[ToolCall]  # 工具调用记录（可选）
    metadata: Dict            # 元数据
}
```

**文件元数据模型** (FileMetadata):
```python
FileMetadata {
    file_id: str              # 文件唯一标识
    filename: str             # 文件名
    size: int                 # 文件大小（字节）
    upload_time: datetime     # 上传时间
    file_path: str            # 服务器存储路径
    indexed: bool             # 是否已索引
}
```

详细数据模型规范: 参见 [data-model.md](./data-model.md)

### API合同

#### 客户端-服务器通信协议

**NPLT协议** (TCP:9999):
```
消息格式: Type(1B) + Seq(2B) + Len(2B) + Data(<=64KB)

消息类型:
- 0x01: CHAT_TEXT        # 聊天文本
- 0x02: AGENT_THOUGHT    # Agent状态（JSON格式）
- 0x03: DOWNLOAD_OFFER   # 文件下载提议（JSON格式）
- 0x04: FILE_METADATA    # 文件元数据（JSON格式）
- 0x05: FILE_DATA        # 文件数据
- 0x10: SESSION_SWITCH   # 会话切换（JSON格式）
- 0x11: HISTORY_REQUEST  # 历史记录请求
- 0x12: HISTORY_RESPONSE # 历史记录响应（JSON格式）
```

**RDT协议** (UDP:9998):
```
数据报格式: Seq(4B) + Ack(4B) + Window(1B) + Flags(1B) + Checksum(2B) + Data(<=1000B)

标志位:
- 0x01: SYN (握手)
- 0x02: ACK (确认)
- 0x04: FIN (结束)
- 0x08: DATA (数据)
```

#### CLI客户端命令API

```
命令格式: /command [arguments...]

命令列表:
- /help                    # 显示帮助
- /quit                    # 退出客户端
- /upload <file> [note]    # 上传文件（可附加说明）
- /model <model_name>      # 切换模型
- /sessions                # 列出所有会话
- /switch <session_id>     # 切换会话
- /new                     # 创建新会话
- /delete <session_id>     # 删除会话
- /history [count]         # 查看历史记录
- /clear                   # 清空当前会话历史
```

#### 测试场景合同

定义12项核心功能的测试场景：

1. **连接测试**:
   - 输入: 启动客户端，连接到 localhost:9999
   - 预期: 显示服务器欢迎消息，无错误

2. **聊天测试**:
   - 输入: "你好"
   - 预期: 调用智谱API，显示AI回复（流式输出）

3. **文件上传测试**:
   - 输入: "/upload test.txt 测试文件"
   - 预期: 文件上传成功，自动索引

4. **文件下载测试**:
   - 输入: "请把配置文件发给我"
   - 预期: Agent发起下载提议，确认后通过RDT协议下载

5. **会话管理测试**:
   - 输入: "/sessions", "/switch <id>", "/new", "/delete <id>"
   - 预期: 会话操作成功，状态正确更新

6. **模型切换测试**:
   - 输入: "/model glm-4.5-flash"
   - 预期: 模型切换成功，后续使用新模型

7. **历史记录测试**:
   - 输入: "/history", "/clear"
   - 预期: 历史记录正确显示和清空

详细API契约: 参见 [contracts/client-api.yaml](./contracts/client-api.yaml)

### 快速入门指南

**环境设置**:

```bash
# 1. 确保Python 3.11和uv已安装
python --version  # 应显示 Python 3.11.x
uv --version

# 2. 配置智谱API Key (测试前必须)
export ZHIPU_API_KEY="your_api_key_here"

# 3. 启动服务器（在一个终端）
python -m server.main

# 4. 运行客户端验证测试（在另一个终端）
cd clients/cli
pytest tests/ -v
```

**重构步骤**:

```bash
# 阶段1: 验证现有功能
cd clients/cli  # 假设已重构
python tests/validate_existing_features.py

# 阶段2: 修复发现的问题
# (根据验证报告手动修复)

# 阶段3: 执行目录重构
python scripts/migrate_to_new_structure.py

# 阶段4: 回归测试
pytest tests/ --regression -v

# 阶段5: 提交每个阶段
git add .
git commit -m "feat: 完成客户端重构阶段X，测试通过率100%"
```

详细快速入门指南: 参见 [quickstart.md](./quickstart.md)

## 阶段 2: 任务分解

*此阶段由 `/speckit.tasks` 命令生成，不在此文件中*

**预期任务类别**:

1. **验证任务** (阶段1):
   - T001: 编写12项功能的真实测试用例
   - T002: 执行功能验证，生成问题报告
   - T003: 修复P0级别问题
   - T004: 修复P1级别问题
   - T005: 回归测试，达到100%通过率

2. **重构任务** (阶段2):
   - T006: 创建新目录结构 (clients/, server/, shared/)
   - T007: 移动客户端文件到 clients/cli/
   - T008: 移动服务器文件到 server/
   - T009: 移动共享代码到 shared/
   - T010: 更新所有导入路径
   - T011: 创建独立的客户端协议定义副本
   - T012: 更新配置文件和脚本
   - T013: 更新文档 (README.md, 架构文档)

3. **测试任务** (阶段3):
   - T014: 运行重构后完整测试套件
   - T015: 执行性能测试，对比重构前后
   - T016: 验证客户端独立部署能力
   - T017: 协议版本兼容性测试
   - T018: 生成最终对比报告

4. **文档任务** (贯穿始终):
   - T019: 更新README.md反映新目录结构
   - T020: 编写架构文档 (docs/architecture.md)
   - T021: 编写客户端使用指南 (docs/client-guide.md)
   - T022: 更新API文档

## 测试策略

### 核心原则

**100%真实测试，零mock**
- 所有测试必须使用真实后端服务器
- 所有LLM调用必须使用真实智谱API (glm-4-flash或glm-4.5-flash)
- 测试前必须验证ZHIPU_API_KEY已配置
- 禁止使用unittest.mock或pytest.mock

### 测试层次

```
┌─────────────────────────────────────────┐
│  E2E测试 (端到端)                        │
│  - 启动真实服务器和客户端                 │
│  - 测试完整用户场景                       │
│  - 使用真实智谱API                       │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  集成测试                                │
│  - 测试客户端-服务器协议通信             │
│  - 测试文件传输 (RDT/NPLT)               │
│  - 测试会话管理                          │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  单元测试                                │
│  - 测试协议编解码                        │
│  - 测试UI渲染                            │
│  - 测试工具函数                          │
└─────────────────────────────────────────┘
```

### 测试覆盖

**12项核心功能 × N种测试场景**:

| 功能 | 单元测试 | 集成测试 | E2E测试 | 性能测试 | 边界测试 |
|------|---------|---------|---------|----------|----------|
| 1. 连接服务器 | ✅ | ✅ | ✅ | - | 网络中断 |
| 2. 聊天消息 | ✅ | ✅ | ✅ | 响应时间 | 超长消息 |
| 3. 文件上传 | ✅ | ✅ | ✅ | 传输速度 | 10MB限制 |
| 4. 文件下载 | ✅ | ✅ | ✅ | 传输速度 | 网络中断 |
| 5. 会话列表 | ✅ | ✅ | ✅ | - | 空列表 |
| 6. 切换会话 | ✅ | ✅ | ✅ | - | 无效ID |
| 7. 新建会话 | ✅ | ✅ | ✅ | - | 会话数限制 |
| 8. 删除会话 | ✅ | ✅ | ✅ | - | 删除当前会话 |
| 9. 切换模型 | ✅ | ✅ | ✅ | - | 无效模型名 |
| 10. 历史记录 | ✅ | ✅ | ✅ | - | 空历史 |
| 11. 清空历史 | ✅ | ✅ | ✅ | - | 已清空 |
| 12. 自动重连 | ✅ | ✅ | ✅ | 重连时间 | 服务器拒绝 |

**覆盖率目标**:
- 代码覆盖率: ≥80%
- 功能覆盖率: 100%
- 分支覆盖率: ≥75%

## 实施里程碑

### 里程碑1: 功能验证与修复 (Week 1)

**目标**: 现有功能100%通过真实测试

```
Day 1-2: 编写真实测试用例
  - 12项功能的测试脚本
  - 测试数据准备
  - API key验证

Day 3-4: 执行验证，生成问题报告
  - 运行所有测试
  - 记录问题清单
  - 分类问题严重程度

Day 5-7: 修复问题
  - 修复P0/P1问题
  - 回归测试
  - 达到100%通过率

交付物:
- 验证报告 (reports/validation_report.md)
- 问题清单 (issues/identified_issues.md)
- 修复记录 (issues/fix_log.md)
- Git提交: "feat: 完成功能验证与修复，测试通过率100%"
```

### 里程碑2: 目录结构重构 (Week 2)

**目标**: 完成客户端独立部署架构

```
Day 1-2: 创建新目录结构
  - 创建 clients/, server/, shared/
  - 移动文件到新位置
  - 创建独立协议副本

Day 3-4: 更新导入路径
  - 批量更新Python导入
  - 更新配置文件
  - 更新脚本和工具

Day 5: 文档更新
  - 更新README.md
  - 编写架构文档
  - 更新API文档

交付物:
- 新目录结构 (clients/, server/, shared/)
- 架构文档 (docs/architecture.md)
- Git提交: "refactor: 完成客户端目录结构重构"
```

### 里程碑3: 回归测试与发布 (Week 3)

**目标**: 验证重构后功能完整性

```
Day 1-2: 完整测试套件
  - 运行所有单元测试
  - 运行集成测试
  - 运行E2E测试

Day 3: 性能测试
  - 对比重构前后性能
  - 验证响应时间<10%差异
  - 生成性能报告

Day 4: 独立部署验证
  - 客户端独立打包
  - 连接远程服务器
  - 协议版本兼容性测试

Day 5: 文档和发布
  - 更新所有文档
  - 生成对比报告
  - Git提交: "test: 完成回归测试，功能完整性验证通过"

交付物:
- 测试报告 (reports/regression_test_report.md)
- 性能报告 (reports/performance_comparison.md)
- 对比报告 (reports/before_after_comparison.md)
- 最终发布: v1.0.0
```

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 现有功能存在严重问题 | 中 | 高 | 优先修复P0问题，设置基线快照 |
| 重构后导入路径错误 | 高 | 中 | 自动化脚本批量更新，充分测试 |
| 协议定义不同步 | 中 | 中 | 实施版本检查机制，自动化同步测试 |
| 性能下降 | 低 | 中 | 性能基线测试，持续监控 |
| 测试覆盖不足 | 中 | 高 | 强制100%功能覆盖，代码审查 |
| API配额不足 | 低 | 低 | 使用免费模型（glm-4-flash），批量测试 |

## 依赖关系

### 外部依赖

- **智谱AI API**: 提供LLM服务 (glm-4-flash, glm-4.5-flash)
  - 要求: 有效的ZHIPU_API_KEY
  - 免费额度: 足够测试使用
  - 验证: 测试启动前检查API key

### 内部依赖

- **服务器代码**: 必须先启动服务器才能测试客户端
- **协议定义**: 客户端和服务器协议必须保持同步
- **配置文件**: config.yaml必须正确配置

### 阶段依赖

```
阶段0 (研究) → 阶段1 (验证修复) → 阶段2 (重构) → 阶段3 (回归测试)
    ↓              ↓                  ↓               ↓
 research.md   问题报告            新目录结构      最终测试报告
               修复记录            更新文档        对比报告
```

## 成功标准

### 定量指标

- ✅ 验证阶段: 100%功能覆盖率
- ✅ 修复阶段: 100%测试通过率，0个P0/P1问题
- ✅ 重构阶段: 100%导入路径正确，0个ImportError
- ✅ 回归阶段: 100%功能完整性，0个回归问题
- ✅ 性能: 重构后响应时间变化<10%
- ✅ 覆盖率: 代码覆盖率≥80%，分支覆盖率≥75%

### 定性指标

- ✅ 客户端可独立部署（不依赖src/目录）
- ✅ 协议定义版本同步
- ✅ 文档完整且准确
- ✅ 符合项目章程v1.6.0所有原则
- ✅ 所有测试使用真实API，零mock

---

**下一步**: 运行 `/speckit.tasks` 生成详细任务分解
