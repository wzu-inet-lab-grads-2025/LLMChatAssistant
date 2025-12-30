# 研究文档: 文件操作工具集成到 Agent

**功能**: 003-file-tools-integration
**创建时间**: 2025-12-30
**状态**: 已完成

## 研究目标

本研究旨在确定文件操作工具集成的最佳技术方案，包括：
1. 如何将文件上传、下载、检索功能集成到现有的 ReAct Agent 框架
2. 如何实现工具串行调用支持
3. 如何复用现有基础设施（VectorStore、IndexManager、PathValidator）
4. 如何确保安全性和可审计性

## 研究发现

### 1. 现有工具架构分析

**发现**: 现有的 ReAct Agent 使用统一的工具接口（Tool 基类），所有工具都继承自 `src/tools/base.py`。

**关键特点**:
- 工具基类定义了 `name`、`description`、`timeout` 属性
- 抽象方法 `execute(**kwargs)` 必须由子类实现
- 返回统一的 `ToolExecutionResult` 对象（包含 success、output、error、duration）
- 支持参数验证 `validate_args(**kwargs)`

**决策**: 新的文件工具将继承相同的基类，保持架构一致性。

**理由**: 保持接口一致性使得新工具可以无缝集成到现有的工具注册表和 ReAct 循环中。

---

### 2. NPLT 协议文件传输能力

**发现**: 现有的 NPLT 协议已支持文件传输，定义了以下消息类型：
- `DOWNLOAD_OFFER` (0x0C): 文件下载提议
- `FILE_DATA` (0x0D): 文件数据（上传/下载）
- `FILE_METADATA` (0x0E): 文件元数据（文件名、大小等）

**关键特点**:
- 协议支持最大 65535 字节的数据包（v2版本）
- 文件传输分块进行，支持大文件传输
- 先发送元数据，等待用户确认后再传输数据

**决策**: FileDownloadTool 将使用现有的 NPLT 协议发送文件，无需修改协议层。

**理由**: 复用现有协议避免重复开发，确保与客户端的兼容性。

---

### 3. 向量索引集成策略

**发现**: 现有的 RAGTool 已经实现了完整的文件索引和检索功能：
- 使用 IndexManager 管理索引生命周期
- 支持自动索引（execute_async 方法）
- 索引持久化到 storage/vectors/
- 懒加载策略避免重复索引

**关键特点**:
- IndexManager.ensure_indexed(file_path) 确保文件已索引
- VectorStore.search_all() 执行语义检索
- 索引创建时验证文件类型和大小

**决策**: FileUploadTool 将在文件保存后调用 IndexManager.ensure_indexed() 建立索引。FileSemanticSearchTool 将复用 RAGTool 的检索逻辑。

**理由**: 复用现有的索引管理逻辑，避免重复代码，确保索引一致性。

---

### 4. 路径验证和安全控制

**发现**: 现有的 PathValidator 提供了多层安全验证：
- 路径白名单验证（allowed_paths）
- 路径黑名单检查（forbidden_patterns）
- 路径规范化（防止 ../ 路径遍历）
- 文件大小和类型验证

**关键特点**:
- `is_allowed(path)` 方法返回 (bool, str) 元组
- 明确的拒绝消息帮助用户理解问题
- 支持 glob 模式匹配（如 `/var/log/*.log`）

**决策**: FileDownloadTool 和 FileUploadTool 将使用 PathValidator 验证所有文件路径。

**理由**: 统一的安全模型确保所有文件操作遵循相同的安全规则。

---

### 5. ReAct 循环和串行工具调用

**发现**: 现有的 ReAct 循环（src/server/agent.py）已天然支持串行工具调用：
- 最多 5 轮工具调用（max_tool_rounds=5）
- 每轮工具调用结果作为下一轮的输入
- `_think_and_decide()` 方法使用提示词决定下一步操作

**关键特点**:
- 工具调用结果更新 `current_message`
- Agent 自动判断是否需要继续调用工具
- 支持工具调用失败后的降级处理

**决策**: 无需修改 ReAct 循环代码，只需更新 Agent 提示词，添加文件工具的使用说明和示例。

**理由**: 现有架构已支持串行调用，提示词优化即可实现文件操作的串行调用场景。

---

### 6. Agent 提示词工程

**发现**: 现有的 Agent 提示词（agent.py:272-394）包含：
- 工具决策流程（步骤1: 识别查询类型、步骤2: 匹配命令到工具）
- 每个工具的使用示例
- 明确的输出格式要求（TOOL: tool_name、ARGS: {...}）

**关键特点**:
- 使用清晰的决策树帮助 LLM 选择工具
- 提供多个示例减少理解错误
- 限制输出格式避免 LLM 自由发挥

**决策**: 在现有提示词中添加"文件操作场景"部分，包含：
- 文件上传触发条件（用户说"上传文件"、"发送文件给你"）
- 文件下载触发条件（用户说"下载文件"、"发给我"）
- 文件检索触发条件（用户说"搜索XX文件"、"找找关于XX的文档"）
- 串行调用示例（先检索再下载）

**理由**: 提示词工程是最小成本的实现方式，无需修改代码逻辑。

---

## 技术决策总结

| 决策点 | 选择 | 替代方案 | 理由 |
|--------|------|----------|------|
| 工具基类 | 继承现有 Tool 基类 | 创建新的文件工具基类 | 保持架构一致性 |
| 文件传输协议 | 复用 NPLT 协议 | 实现新的文件传输协议 | 避免重复开发，确保兼容性 |
| 向量索引 | 复用 IndexManager | 实现新的索引管理器 | 避免重复代码 |
| 路径验证 | 使用 PathValidator | 实现新的验证逻辑 | 统一安全模型 |
| 串行调用 | 仅更新提示词 | 修改 ReAct 循环代码 | 现有架构已支持，提示词工程更简单 |
| 文件存储 | 复用 storage/uploads/ | 创建新的存储目录 | 与现有 UploadedFile 类一致 |

## 未解决的问题

无。所有技术决策已明确。

## 下一步行动

1. 生成 data-model.md - 定义文件操作相关的数据模型
2. 生成 contracts/file-tools-interface.md - 定义文件工具的接口规范
3. 生成 quickstart.md - 提供快速开始指南
4. 运行 update-agent-context.sh 更新代理上下文
