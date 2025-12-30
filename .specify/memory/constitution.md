<!--
同步报告:

版本更改: 1.4.1 → 1.4.2 (PATCH - 强化测试真实性原则，禁止mock实现)

修改的原则:
- 测试真实性 (Test Authenticity) → 强化约束，明确禁止所有mock实现，必须使用真实智谱API（glm-4-flash或glm-4.5-flash免费模型）

添加的原则: 无

删除的原则: 无

需要更新的模板:
- ✅ .specify/memory/constitution.md - 已更新
- ⚠️ src/llm/mock.py - MUST删除或标记为DEPRECATED，违反章程原则
- ⚠️ tests/validation/test_agent_comprehensive.py - MUST更新为使用真实ZhipuProvider

审查备注 (2025-12-31):
- 章程明确禁止mock实现和模拟调用
- 智谱AI提供免费模型（glm-4-flash、glm-4.5-flash），必须使用真实API进行测试
- MockLLMProvider违反章程核心原则，必须移除
- 所有LLM相关测试必须配置真实的ZHIPU_API_KEY环境变量
- 测试真实性是不可妥协的原则，确保代码在真实环境中工作

后续 TODO:
- [REQUIRED] 删除src/llm/mock.py文件
- [REQUIRED] 更新tests/validation/test_agent_comprehensive.py使用真实ZhipuProvider
- [REQUIRED] 在.env中配置有效的ZHIPU_API_KEY
- [REQUIRED] 验证所有测试使用真实API运行
- 建议在README中添加API key配置说明，提供免费模型链接
-->

# LLMChatAssistant 项目章程

## 核心原则

### 质量与一致性 (Quality and Consistency)

项目 MUST 保持高质量的代码标准和一致性。所有代码 MUST 遵循统一的编码规范，MUST 经过代码审查，MUST 通过自动化测试。任何偏离质量标准的实现都被明确禁止。每个功能 MUST 确保真实实现了其预期目的，而不允许虚假实现或占位符代码。

**理由**: 质量是项目的基石。一致性使代码更易于维护和协作，防止技术债务的积累。

### 测试真实性 (Test Authenticity)

所有测试 MUST 是真实的测试，绝对不允许使用 mock 测试或模拟实现。涉及大模型调用的测试 MUST 使用真实的智谱 API，具体 MUST 使用免费的 glm-4-flash 或 glm-4.5-flash 模型进行测试，而不允许使用模拟回复或伪造的 LLM Provider。测试 MUST 验证实际功能行为，而不是验证模拟的对象。在运行涉及 LLM 的测试之前，MUST 检查是否已配置有效的 ZHIPU_API_KEY，如果未配置则 MUST 要求用户配置后再继续。绝对禁止创建 MockLLMProvider 或类似的模拟类，所有 LLM 调用 MUST 通过真实的 ZhipuProvider 进行。

**理由**: 真实测试确保代码在真实环境中按预期工作。mock 测试可能掩盖真实的集成问题，特别是对于外部依赖如 LLM API。真实 API 测试验证了实际的协议、错误处理和数据格式。智谱AI提供免费的 glm-4-flash 和 glm-4.5-flash 模型（[智谱AI开放平台](https://open.bigmodel.cn/)），无需额外成本即可进行真实测试。使用真实API可以及早发现LLM响应格式、工具调用解析、流式输出等实际问题，这些是mock无法模拟的。

### 文档与可追溯性 (Documentation & Traceability)

所有日志 MUST 写入 logs 文件夹，格式为纯文本 (.log)。每个主要功能、测试运行和错误 MUST 有相应的日志记录，以便追踪和调试。日志 MUST 包含时间戳、操作类型和相关上下文信息。

**理由**: 集中的日志记录使问题可追溯，便于调试和审计。纯文本格式易于阅读和处理，不需要特殊工具。

### 真实集成 (Real Integration)

项目 MUST 使用官方的 zai-sdk Python 包与智谱 AI 进行集成。所有 LLM 调用 MUST 通过真实 API 进行，不允许使用假的或模拟的回复。任何声称与 LLM 交互的功能 MUST 真正调用智谱 API 并返回真实的响应。

**理由**: 使用官方 SDK 确保与智谱 AI 的最佳兼容性和最新特性。真实集成确保开发期间就能发现集成问题，而不是在生产环境中。

### 开发环境标准 (Development Environment Standards)

项目 MUST 使用 uv 创建和管理虚拟环境。Python 版本 MUST 使用 Python 3.11。所有依赖 MUST 通过 uv 安装和管理。开发和测试环境 MUST 保持一致。

**理由**: uv 提供了快速、可靠的依赖管理和虚拟环境创建。固定 Python 版本确保跨环境的一致性。标准化环境减少"在我机器上能工作"的问题。

### 语言规范 (Language Standard)

所有用户回复、代码注释和文档生成 MUST 使用中文。代码中的变量名、函数名等标识符可以使用英文，但所有面向用户的文本、注释和文档 MUST 是中文。这包括但不限于：错误消息、日志输出、API 文档、README 文件和内联代码注释。

**理由**: 使用中文作为项目的主要语言确保了项目与目标用户群体的一致性，提高了可读性和可维护性，使团队成员能够更有效地沟通和协作。

### 版本控制与测试纪律 (Version Control & Testing Discipline)

每完成一个开发阶段并且通过真实且完整的测试后，MUST 使用 git 提交一个版本。阶段的定义包括但不限于：完成设置阶段、完成基础设施阶段、完成某个用户故事、完成重大功能或完成修复工作。测试 MUST 是真实的测试，不允许虚假测试或跳过测试。提交消息 MUST 清晰地描述该阶段完成的工作和测试结果。

**理由**: 分阶段提交确保了项目历史的清晰性和可追溯性。只有在测试通过后才提交保证了每个版本都是稳定和可用的。这种做法使得回滚、分支管理和协作开发更加安全和高效。真实测试确保了提交的质量不会因为测试不充分而受到影响。

### 安全第一原则 (Security First)

所有文件访问操作 MUST 受到统一的安全白名单控制。CommandTool、RAGTool 等所有工具 MUST 使用相同的路径验证机制。绝对禁止绕过白名单访问文件系统中的任意路径。白名单配置 MUST 存储在 config.yaml 的 file_access.allowed_paths 中，支持普通路径和 glob 模式匹配（如 /var/log/*.log）。系统 MUST 维护黑名单模式（file_access.forbidden_patterns）以额外保护敏感文件，包括但不限于：*/.env、*/.ssh/*、/etc/passwd、/etc/shadow、/etc/*secret*。路径验证器 MUST 自动规范化路径（防止 ../ 路径遍历攻击），并验证文件是否在白名单范围内。

**理由**: 统一的安全模型确保所有工具遵循相同的访问规则，防止安全漏洞。白名单机制遵循最小权限原则，默认拒绝所有访问，只明确允许必要的路径。黑名单提供额外保护层，防止误配置导致的敏感文件泄露。路径规范化防止路径遍历攻击。

### 自动化与按需索引 (Automation and Lazy Indexing)

当用户访问白名单中的文件时，系统 MUST 自动创建向量索引（如果尚未索引）。RAG 工具 MUST 支持按需索引（execute_async 方法），在首次访问文件时自动调用索引管理器创建索引。索引管理器 MUST 使用懒加载策略，避免重复索引已索引的文件。系统 MUST 将索引持久化存储到 storage/vectors/ 目录，并在重启后自动加载。索引创建 MUST 验证文件内容类型（仅允许文本文件）和文件大小（默认最大 10MB）。

**理由**: 自动索引提供透明的用户体验，用户无需手动管理索引。懒加载策略减少不必要的计算和存储开销。按需创建索引只在首次访问时发生，提高系统启动速度。持久化索引确保重启后无需重新索引，提高效率。文件类型和大小验证防止恶意文件导致系统问题。

### 多层防御策略 (Defense in Depth)

系统 MUST 实现多层安全验证，任何一层失败都不应导致安全漏洞。文件访问 MUST 依次通过：路径白名单验证、路径黑名单检查、文件大小限制、内容类型验证。命令执行 MUST 限制输出大小（默认最大 100KB），防止内存耗尽。命令参数 MUST 验证是否包含黑名单字符（;, &, |, >, <, `, $, (, ), \n, \r），防止命令注入。正则表达式搜索（grep 工具）MUST 验证正则复杂度，防止 ReDoS 攻击。Glob 模式匹配 MUST 限制最大文件数（默认 100 个），防止 DoS 攻击。

**理由**: 深度防御策略确保即使一层防御失效，其他层仍能提供保护。例如，即使白名单配置错误，黑名单仍能阻止某些敏感文件访问。输出大小限制防止大文件导致内存耗尽。参数验证防止命令注入。正则复杂度检查防止 CPU 耗尽。Glob 限制防止返回数万个文件导致系统崩溃。

### 可审计性与透明性 (Auditability & Transparency)

所有文件访问操作、索引创建和工具调用 MUST 记录日志。当文件访问被拒绝时，系统 MUST 返回明确的拒绝理由（如"路径不在白名单中"、"路径匹配禁止模式: */.env"）。当自动索引创建时，系统 MUST 记录索引创建的详细信息（文件路径、分块数量、创建时间）。工具执行结果 MUST 包含执行状态、成功/失败标志和持续时间。系统 MUST 提供索引状态查询接口，允许用户检查哪些文件已索引、哪些文件允许访问。

**理由**: 审计日志对安全合规和问题排查至关重要。明确的拒绝消息帮助用户理解为什么访问被拒绝，以及如何修正配置。索引创建日志帮助用户了解系统行为。详细的执行结果支持调试和性能分析。状态查询接口提供系统透明度，帮助用户理解当前系统状态。

### 多协议传输架构 (Multi-Protocol Transport Architecture)

文件传输 MUST 支持多协议架构以适应不同客户端类型和满足课程设计要求。系统 MUST 实现以下传输协议：RDT（基于UDP的可靠数据传输协议）、HTTP（Web文件下载）、NPLT（基于TCP的流式传输，作为兼容降级方案）。RDT协议 MUST 实现滑动窗口机制、超时重传、CRC16校验和累积ACK确认。CLI客户端 MUST 优先使用RDT协议进行高速文件传输。Desktop客户端（Python GUI应用，如Tkinter/PyQt）MUST 优先使用RDT协议，可降级到HTTP，最后降级到NPLT。Web客户端 MUST 使用HTTP协议进行文件下载（Web客户端实现推迟到未来阶段）。系统 MUST 根据Session的client_type字段（cli/web/desktop）自动选择最优传输协议。当优先协议不可用时，系统 MUST 自动降级到NPLT协议确保兼容性。当前阶段 ONLY 实现CLI客户端的完整文件传输功能，包括RDT协议和NPLT降级方案。Web客户端和Desktop客户端的支持在当前阶段为可选项，其实现推迟到后续阶段。

**理由**: 混合传输架构满足课程RDT协议设计要求（UDP + 滑动窗口 + 可靠性机制），展示对网络协议的理解和实现能力。RDT协议提供高速UDP传输，适合CLI/Desktop客户端的大文件传输场景。HTTP协议支持Web浏览器原生下载，为未来Web客户端提供基础。NPLT协议作为降级方案确保在网络环境限制下仍能完成文件传输。自动协议选择机制确保每个客户端类型获得最优传输体验。Desktop客户端使用Python GUI（而非Electron/Tauri）保持技术栈一致性，Python生态提供完整的GUI框架（Tkinter/PyQt/PySide），可实现完整的UDP支持和原生性能。分阶段实施策略降低初期开发复杂度，优先验证核心RDT功能，确保课程要求的核心功能先完成。这种架构设计既满足了课程设计要求，又为未来的多客户端扩展奠定了基础。

### 数据传输格式标准 (Data Transmission Format Standards)

系统 MUST 根据数据类型选择合适的传输格式，平衡性能、可读性和结构化信息保留。实时聊天消息（单条消息）MUST 使用纯文本格式通过NPLT CHAT_TEXT消息类型传输，包括用户消息、Agent响应、心跳等。实时聊天中的Agent状态更新（如思考过程、工具调用状态）MUST 使用JSON格式通过NPLT AGENT_THOUGHT消息类型传输，支持流式输出的stream_start标记、thinking/tool_call/generating状态类型。历史记录批量传输（HISTORY_REQUEST响应）MUST 使用JSON格式传输，MUST 保留完整的结构化信息，包括role、content、timestamp、tool_calls（工具名称、参数、结果、状态、持续时间）、metadata。文件传输相关消息（FILE_METADATA、DOWNLOAD_OFFER、SESSION_SWITCH等）MUST 使用JSON格式传输，确保结构化数据的完整性。NPLT协议数据字段 MUST 支持UTF-8编码的文本或JSON数据。

**理由**: 实时聊天使用纯文本格式保持简单高效，减少序列化/反序列化开销，支持实时流式输出（边思考边显示）。Agent状态使用JSON格式支持结构化状态信息（状态类型、内容），便于客户端解析和UI更新。历史记录使用JSON格式保留tool_calls等结构化数据，使客户端能够完整重建对话过程、显示工具调用详情、支持搜索和过滤。文件传输使用JSON格式确保元数据完整性（文件名、大小、会话ID等），支持文件上传下载协调。混合格式策略在性能和功能之间取得平衡，实时性强的场景使用文本，需要结构化数据的场景使用JSON。详细协议格式和调用链路参见docs/message-flow-analysis.md和docs/protocol-call-chain.md。

## 技术约束

- **Python 版本**: MUST 使用 Python 3.11
- **虚拟环境**: MUST 使用 uv 创建和管理虚拟环境
- **LLM SDK**: MUST 使用 zai-sdk 与智谱 AI 集成
- **日志格式**: MUST 使用纯文本 (.log) 格式，存储在 logs 文件夹
- **依赖管理**: 所有依赖 MUST 通过 uv 管理
- **版本控制**: 每个阶段完成并通过测试后 MUST git 提交版本
- **文件访问**: MUST 使用统一的路径白名单控制，配置在 config.yaml 的 file_access.allowed_paths
- **路径验证**: MUST 防止路径遍历攻击（../ 规范化），MUST 验证 glob 模式
- **自动索引**: MUST 支持按需索引，RAG 工具 MUST 在首次访问白名单文件时自动创建索引
- **索引存储**: MUST 将向量索引持久化到 storage/vectors/ 目录
- **多层防御**: MUST 实现白名单、黑名单、大小限制、内容类型验证等多层安全机制
- **审计日志**: MUST 记录所有文件访问、索引创建和工具调用操作
- **RDT协议**: MUST 实现基于UDP的可靠数据传输，包括滑动窗口（窗口大小5）、超时重传（0.1秒）、CRC16校验和累积ACK
- **多协议路由**: file_download工具 MUST 根据client_type自动选择RDT/HTTP/NPLT协议，优先协议不可用时MUST降级到NPLT
- **Session管理**: Session对象 MUST 包含client_type字段（cli/web/desktop），默认值为"cli"
- **客户端类型**: 当前阶段 ONLY 实现CLI客户端（client_type="cli"），Web和Desktop客户端实现推迟到后续阶段
- **Desktop客户端**: Desktop客户端MUST使用Python GUI框架（Tkinter/PyQt/PySide），MUST支持完整RDT协议UDP通信
- **数据传输格式**: 实时聊天消息MUST使用纯文本，历史记录批量传输MUST使用JSON格式（保留tool_calls、timestamp等结构化数据）
- **协议文档**: 协议格式、消息流和调用链路MUST记录在docs/目录（message-flow-analysis.md、protocol-call-chain.md）

## 测试要求

- **真实性**: 所有测试 MUST 是真实测试，不允许 mock
- **API 测试**: 涉及 LLM 的测试 MUST 使用真实的智谱 API
- **API Key 验证**: 运行 LLM 测试前 MUST 验证 API key 已配置
- **功能验证**: 测试 MUST 验证实际功能，不允许虚假测试
- **测试覆盖**: 每个功能 MUST 有相应的测试用例
- **测试纪律**: 测试不通过不允许提交代码
- **安全测试**: MUST 测试路径白名单验证、黑名单匹配、路径遍历防护
- **索引测试**: MUST 测试自动索引创建、懒加载机制、索引持久化
- **边界测试**: MUST 测试文件大小限制、输出大小限制、glob 匹配限制
- **拒绝测试**: MUST 测试非法访问被正确拒绝并返回明确的错误消息
- **RDT协议测试**: MUST 测试滑动窗口、超时重传、CRC16校验、累积ACK机制（当前阶段仅CLI客户端）
- **多协议路由测试**: MUST 测试file_download工具根据client_type选择正确的传输协议
- **协议降级测试**: MUST 测试RDT不可用时自动降级到NPLT协议
- **文件传输测试**: MUST 测试CLI客户端使用RDT协议完整传输文件（上传、下载、校验）
- **数据传输格式测试**: MUST 测试实时聊天使用纯文本格式，历史记录使用JSON格式并保留完整结构化数据

## 治理

### 修正程序

对本章程的任何修正 MUST 遵循以下流程:

1. 提出修正建议并记录理由
2. 更新章程版本号（遵循语义版本控制）
3. 更新所有依赖模板以保持一致性
4. 记录所有更改并更新同步报告
5. 获得批准后应用新章程

### 版本控制

- **MAJOR (主版本)**: 向后不兼容的治理/原则删除或重新定义
- **MINOR (次版本)**: 新原则/部分添加或实质性扩展指导
- **PATCH (补丁版本)**: 澄清、措辞、拼写错误修复、非语义优化

### 合规审查

- 所有代码审查 MUST 验证是否符合章程原则
- 所有功能规范 MUST 与章程约束保持一致
- 所有实施计划 MUST 包含章程合规检查
- 任何偏离原则的决定 MUST 明确记录理由

**版本**: 1.4.2 | **批准日期**: 2025-12-28 | **最后修正**: 2025-12-31
