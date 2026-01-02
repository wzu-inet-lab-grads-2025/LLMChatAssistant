<!--
同步报告:

版本更改: 1.6.0 → 1.7.0 (MINOR - 添加项目结构原则)

修改的原则: 无

添加的原则:
- 项目结构原则 (Project Structure Principle) - v1.7.0新增

删除的原则: 无

需要更新的模板:
- ✅ .specify/memory/constitution.md - 已更新
- ⚠️ .specify/templates/spec-template.md - MUST添加项目结构约束部分
- ⚠️ .specify/templates/plan-template.md - MUST添加项目结构审查检查项
- ⚠️ .specify/templates/tasks-template.md - MUST添加目录重构任务类型

审查备注 (2026-01-01):
- 确定最终项目结构：前后端分离的monorepo架构
- server/ - 后端服务器（可独立部署），包含llm/, tools/, storage/, utils/
- clients/ - 前端客户端（cli/），只包含UI和通信逻辑
- shared/ - 真正共享的代码（protocols/, utils/）
- storage/ - 运行时数据目录（非代码）
- 删除 src/ - 所有功能已迁移到对应位置
- 关键原则：后端可独立部署、前端轻量级、协议共享、数据存储分离

后续 TODO (更新于 2026-01-01):
- [PENDING] ⏳ 执行目录结构迁移（src/ → server/）
- [PENDING] ⏳ 更新所有导入路径（from src.* → from server.*）
- [PENDING] ⏳ 更新shared/目录结构（保留protocols/和utils/）
- [PENDING] ⏳ 删除整个src/目录
- [PENDING] ⏳ 更新pyproject.toml依赖路径
- [PENDING] ⏳ 验证所有模块导入正确性
- [PENDING] ⏳ 更新文档和脚本中的路径引用
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

当用户访问白名单中的文件时，系统 MUST 自动创建向量索引（如果尚未索引）。semantic_search 工具 MUST 支持按需索引（execute_async 方法），在首次访问文件时自动调用索引管理器创建索引。索引管理器 MUST 使用懒加载策略，避免重复索引已索引的文件。系统 MUST 将索引持久化存储到 storage/vectors/ 目录，并在重启后自动加载。索引创建 MUST 验证文件内容类型（仅允许文本文件）和文件大小（默认最大 10MB）。

**理由**: 自动索引提供透明的用户体验，用户无需手动管理索引。懒加载策略减少不必要的计算和存储开销。按需创建索引只在首次访问时发生，提高系统启动速度。持久化索引确保重启后无需重新索引，提高效率。文件类型和大小验证防止恶意文件导致系统问题。

### 多层防御策略 (Defense in Depth)

系统 MUST 实现多层安全验证，任何一层失败都不应导致安全漏洞。文件访问 MUST 依次通过：路径白名单验证、路径黑名单检查、文件大小限制、内容类型验证。命令执行 MUST 限制输出大小（默认最大 100KB），防止内存耗尽。命令参数 MUST 验证是否包含黑名单字符（;, &, |, >, <, `, $, (, ), \n, \r），防止命令注入。正则表达式搜索（grep 工具）MUST 验证正则复杂度，防止 ReDoS 攻击。Glob 模式匹配 MUST 限制最大文件数（默认 100 个），防止 DoS 攻击。工具执行 MUST 实现参数验证机制，防止类型错误和非法参数导致系统异常。工具返回结果 MUST 使用结构化的ToolExecutionResult格式，包含success、output、error、error_type、suggested_fix等字段，支持Agent的错误处理和自我修正。

**理由**: 深度防御策略确保即使一层防御失效，其他层仍能提供保护。例如，即使白名单配置错误，黑名单仍能阻止某些敏感文件访问。输出大小限制防止大文件导致内存耗尽。参数验证防止命令注入和类型错误。正则复杂度检查防止 CPU 耗尽。Glob 限制防止返回数万个文件导致系统崩溃。结构化错误返回使Agent能够理解失败原因并进行自我修正，提升用户体验。

### 可审计性与透明性 (Auditability & Transparency)

所有文件访问操作、索引创建和工具调用 MUST 记录日志。当文件访问被拒绝时，系统 MUST 返回明确的拒绝理由（如"路径不在白名单中"、"路径匹配禁止模式: */.env"）。当自动索引创建时，系统 MUST 记录索引创建的详细信息（文件路径、分块数量、创建时间）。工具执行结果 MUST 包含执行状态、成功/失败标志和持续时间。系统 MUST 提供索引状态查询接口，允许用户检查哪些文件已索引、哪些文件允许访问。工具执行失败时 MUST 返回结构化错误信息（ErrorType枚举），包括错误类型、错误代码、建议修复方案（suggested_fix）和是否可重试（retry_able）。

**理由**: 审计日志对安全合规和问题排查至关重要。明确的拒绝消息帮助用户理解为什么访问被拒绝，以及如何修正配置。索引创建日志帮助用户了解系统行为。详细的执行结果支持调试和性能分析。状态查询接口提供系统透明度，帮助用户理解当前系统状态。结构化错误信息支持Agent的错误处理和自我修正，减少用户困惑，提升系统可用性。

### 多协议传输架构 (Multi-Protocol Transport Architecture)

文件传输 MUST 支持多协议架构以适应不同客户端类型和满足课程设计要求。系统 MUST 实现以下传输协议：RDT（基于UDP的可靠数据传输协议）、HTTP（Web文件下载）、NPLT（基于TCP的流式传输，作为兼容降级方案）。RDT协议 MUST 实现滑动窗口机制、超时重传、CRC16校验和累积ACK确认。CLI客户端 MUST 优先使用RDT协议进行高速文件传输。Desktop客户端（Python GUI应用，如Tkinter/PyQt）MUST 优先使用RDT协议，可降级到HTTP，最后降级到NPLT。Web客户端 MUST 使用HTTP协议进行文件下载（Web客户端实现推迟到未来阶段）。系统 MUST 根据Session的client_type字段（cli/web/desktop）自动选择最优传输协议。当优先协议不可用时，系统 MUST 自动降级到NPLT协议确保兼容性。当前阶段 ONLY 实现CLI客户端的完整文件传输功能，包括RDT协议和NPLT降级方案。Web客户端和Desktop客户端的支持在当前阶段为可选项，其实现推迟到后续阶段。

**理由**: 混合传输架构满足课程RDT协议设计要求（UDP + 滑动窗口 + 可靠性机制），展示对网络协议的理解和实现能力。RDT协议提供高速UDP传输，适合CLI/Desktop客户端的大文件传输场景。HTTP协议支持Web浏览器原生下载，为未来Web客户端提供基础。NPLT协议作为降级方案确保在网络环境限制下仍能完成文件传输。自动协议选择机制确保每个客户端类型获得最优传输体验。Desktop客户端使用Python GUI（而非Electron/Tauri）保持技术栈一致性，Python生态提供完整的GUI框架（Tkinter/PyQt/PySide），可实现完整的UDP支持和原生性能。分阶段实施策略降低初期开发复杂度，优先验证核心RDT功能，确保课程要求的核心功能先完成。这种架构设计既满足了课程设计要求，又为未来的多客户端扩展奠定了基础。

### 数据传输格式标准 (Data Transmission Format Standards)

系统 MUST 根据数据类型选择合适的传输格式，平衡性能、可读性和结构化信息保留。实时聊天消息（单条消息）MUST 使用纯文本格式通过NPLT CHAT_TEXT消息类型传输，包括用户消息、Agent响应、心跳等。实时聊天中的Agent状态更新（如思考过程、工具调用状态）MUST 使用JSON格式通过NPLT AGENT_THOUGHT消息类型传输，支持流式输出的stream_start标记、thinking/tool_call/generating状态类型。历史记录批量传输（HISTORY_REQUEST响应）MUST 使用JSON格式传输，MUST 保留完整的结构化信息，包括role、content、timestamp、tool_calls（工具名称、参数、结果、状态、持续时间）、metadata。文件传输相关消息（FILE_METADATA、DOWNLOAD_OFFER、SESSION_SWITCH等）MUST 使用JSON格式传输，确保结构化数据的完整性。NPLT协议数据字段 MUST 支持UTF-8编码的文本或JSON数据。文件上传 MUST 支持同时传输文件和用户说明（CLI: /upload filepath 用户说明，Web: 上传按钮+文本框）。服务器接收文件后 MUST 自动索引，并将文件元数据记录到Session.uploaded_files，支持后续自然语言引用（"这个文件"、"这些文件"、"之前上传的"）。用户文本MUST附加file_ref标记（[file_ref:{file_id}]），Agent通过Session获取文件信息并处理。

**理由**: 实时聊天使用纯文本格式保持简单高效，减少序列化/反序列化开销，支持实时流式输出（边思考边显示）。Agent状态使用JSON格式支持结构化状态信息（状态类型、内容），便于客户端解析和UI更新。历史记录使用JSON格式保留tool_calls等结构化数据，使客户端能够完整重建对话过程、显示工具调用详情、支持搜索和过滤。文件传输使用JSON格式确保元数据完整性（文件名、大小、会话ID等），支持文件上传下载协调。文件上传同时传输用户说明，提升用户体验，避免"先上传后说明"的繁琐流程。自动索引+Session文件记录支持自然语言文件引用，实现流畅的对话体验。混合格式策略在性能和功能之间取得平衡，实时性强的场景使用文本，需要结构化数据的场景使用JSON。详细协议格式和调用链路参见docs/message-flow-analysis.md和docs/protocol-call-chain.md。

### 工具职责单一原则 (Single Responsibility Principle for Tools)

Agent工具MUST遵循职责单一原则，每个工具只做一件事并做好一件事。工具职责MUST清晰明确，避免功能重叠和职责模糊。系统MUST消除代码重复，功能相同的工具MUST合并或通过继承提取公共逻辑。工具MUST通过描述、输入输出格式明确其职责边界，LLM SHOULD能够根据工具名称和描述准确选择合适的工具。工具职责边界MUST与协议层职责分离，Agent工具负责决策和协调，协议层（NPLT/RDT/HTTP）负责实际数据传输。

**理由**: 职责单一原则降低工具复杂度，提高可维护性。功能重叠导致LLM混淆（如RAG和file_semantic_search代码重复90%），增加测试成本。合并重复工具减少工具数量，简化LLM的决策空间，提升工具选择准确率。职责分离使工具更容易测试和调试，符合软件工程的最佳实践。明确的职责边界防止"工具到底做什么"的歧义，提升系统可用性。

### 协议层分离原则 (Protocol Layer Separation Principle)

Agent工具MUST不参与实际数据传输，数据传输MUST由协议层（NPLT/RDT/HTTP）处理。Agent工具的职责是决策和协调：定位文件（semantic_search）、选择传输协议（file_download._select_transport_mode）、返回下载令牌或URL（file_download）。文件上传由客户端+NPLT Server处理，Agent通过Session.uploaded_files获取文件信息，MUST不调用file_upload工具处理上传。file_download工具MUST只准备下载信息（返回令牌/URL），实际传输由RDT/HTTP协议自动执行。

**理由**: 协议层分离符合关注点分离原则。Agent是决策层，不应该处理底层传输细节。协议层已经实现了完整的传输机制（RDT的滑动窗口、HTTP的浏览器下载、NPLT的流式传输），Agent重复实现这些功能是冗余的。职责分离使系统更容易扩展（添加新协议只需扩展协议层），更容易测试（工具层和协议层独立测试）。避免"Agent工具实际传输文件"的设计错误，如file_upload.execute(filename, content)试图处理文件上传，但实际上文件内容在Agent上下文中无法获取。

### 工具语义清晰原则 (Tool Semantic Clarity Principle)

工具名称和描述MUST清晰反映其职责，避免歧义。工具描述MUST包含：功能说明、适用场景、关键词列表、使用示例（可选）。工具名称SHOULD使用动词_名词格式（如semantic_search、file_download），避免抽象名称。工具描述MUST明确不做什么（如"注意：此工具不处理文件上传，文件上传由协议层完成"）。工具参数名MUST直观易懂（如query、top_k、file_path），避免缩写和技术术语。

**理由**: 清晰的工具语义帮助LLM准确理解工具用途，减少工具选择错误。歧义的描述导致LLM混淆（如RAG的"检索增强生成"和file_semantic_search的"文件语义检索"实际功能相同）。明确的"不做什么"防止误用（如误认为file_upload工具可以处理文件上传）。直观的参数名提升代码可读性，降低使用门槛。

### 代码复用与继承原则 (Code Reuse and Inheritance Principle)

功能相同或相似的工具MUST通过继承提取公共逻辑到基类，避免代码重复。基类MUST定义公共接口和公共实现，子类MUST只实现差异化的部分。代码重复率MUST控制在20%以下，超过此阈值MUST重构。工具继承层次MUST清晰，避免过深继承（继承深度不超过3层）。公共逻辑包括但不限于：参数验证、错误处理、日志记录、结果格式化。

**理由**: 代码重复导致维护成本增加（修改需要同步多处），容易引入不一致的bug。继承提取公共逻辑符合DRY（Don't Repeat Yourself）原则，减少代码量，提高可维护性。控制继承深度防止过度设计，保持系统简单清晰。公共逻辑集中管理，确保所有工具遵循相同的处理流程（如统一的参数验证机制）。

### 混合检索策略原则 (Hybrid Search Strategy Principle)

文件检索工具MUST实施混合检索策略，按优先级依次使用：精确匹配、模糊匹配、语义检索。精确匹配MUST作为第一优先级：当查询包含明确文件名（如"config.yaml"、"app.log"）时，MUST优先进行精确文件名匹配（similarity=1.0）。模糊匹配MUST作为第二优先级：当精确匹配未命中时，MUST进行关键词匹配、前缀匹配、通配符匹配（如"config" → config.yaml、config.json、config.yml）。语义检索MUST作为第三优先级和兜底策略：当精确和模糊匹配均未命中或结果不足时，MUST使用向量语义检索，基于查询内容相似度返回结果。检索结果MUST包含match_type字段（exact_filename、fuzzy_filename、semantic），明确标识匹配方式，便于Agent理解结果来源。检索工具MUST支持scope参数过滤（all/system/uploads），控制检索范围。系统MUST合并多层检索结果并去重，按相似度排序返回top_k结果。

**理由**: 纯向量检索对精确文件名查询效果不佳（如"下载config.yaml"可能返回相似但不完全匹配的结果）。混合检索策略确保精确查询（用户知道确切文件名）直接命中，避免不必要的向量计算。模糊匹配支持部分文件名查询（如"config"），提升用户体验。语义检索作为兜底策略，处理自然语言查询（如"数据库配置在哪里"），保持灵活性。三层策略在准确率和召回率之间取得平衡，整体提升文件检索准确率从90%到98%以上。match_type字段使Agent能够理解结果可信度（精确匹配>模糊匹配>语义匹配），支持更智能的决策。scope过滤防止检索范围过大，提升性能和准确性。

### Agent工具清单规范 (Agent Tool Inventory Specification)

Agent工具MUST精简且必要，工具总数SHOULD控制在5-7个范围内。工具MUST分类清晰：系统管理类（sys_monitor、command_executor）、文件操作类（semantic_search、file_download、file_upload）。系统MUST维护统一的工具清单，明确每个工具的：名称、职责、输入格式、输出格式、安全机制、使用场景。工具清单MUST文档化，存储在docs/目录（如agent_complete_specification.md），并随工具变更同步更新。新增工具MUST经过设计评审，确认：是否确实需要、是否与现有工具重叠、是否遵循职责单一原则。

**理由**: 精简的工具清单降低LLM决策复杂度，提升工具选择准确率。过多的工具（>7个）导致LLM混淆，增加测试成本。工具分类帮助理解工具职责边界，便于维护和扩展。文档化的工具清单提供设计参考，防止"添加相似工具"的重复设计。设计评审机制防止工具数量膨胀，确保每个工具都有明确的必要性。

**当前工具清单（v1.5.1）**：

| 工具名称 | 核心职责 | 输入 | 输出 | 安全机制 |
|---------|---------|------|------|---------|
| sys_monitor | 系统资源监控 | metric类型 | CPU/内存/磁盘使用率 | 无需特殊防护 |
| command_executor | 执行系统命令 | command + args | 命令输出 | 白名单+黑名单+超时 |
| semantic_search | 统一语义检索（混合策略） | query + scope | 文件路径+内容片段 | 路径白名单 |
| file_download | 准备文件下载 | file_path | 下载令牌/URL | 路径白名单 |
| file_upload | 文件索引和上下文管理 | reference + filters | 文件元数据列表 | Session隔离 |

**设计决策记录**：
- 合并RAGTool和FileSemanticSearchTool为SemanticSearchTool（v1.5.0），消除90%代码重复
- 重新定义FileUploadTool为文件索引管理工具（v1.5.0），不处理文件上传（由协议层处理）
- 删除重复工具，工具总数从7个减少到5个（v1.5.0）
- 添加混合检索策略原则（v1.5.1），要求semantic_search实施精确/模糊/语义三层检索

### 项目结构原则 (Project Structure Principle)

项目 MUST 采用前后端分离的monorepo架构，确保模块职责清晰、部署灵活。项目结构 MUST 遵循以下组织原则：

**1. 后端自包含原则 (Backend Self-Containment Principle)**

server/ 目录 MUST 包含所有后端专用代码，MUST 能够作为完整后端独立部署和运行。server/ 目录结构 MUST 包含：
- server/main.py - 服务器入口
- server/agent.py - Agent逻辑
- server/nplt_server.py - NPLT协议服务器
- server/rdt_server.py - RDT文件传输服务器
- server/http_server.py - HTTP服务器
- server/llm/ - LLM集成（仅后端使用）
  - llm/base.py - LLM基础接口
  - llm/zhipu.py - 智谱AI实现
  - llm/models.py - 模型定义
- server/tools/ - 工具实现（仅后端使用）
  - tools/base.py - 工具基类
  - tools/command.py - 命令执行工具
  - tools/monitor.py - 系统监控工具
  - tools/semantic_search.py - 语义检索工具
  - tools/file_upload.py - 文件上传工具
  - tools/file_download.py - 文件下载工具
- server/storage/ - 后端数据存储模块
  - storage/vector_store.py - 向量存储
  - storage/history.py - 对话历史
  - storage/index_manager.py - 索引管理
- server/utils/ - 后端工具函数
  - utils/config.py - 配置管理
  - utils/path_validator.py - 路径验证
- server/protocols/ - 协议实现（与shared/protocols/保持同步）
  - protocols/nplt.py - NPLT协议
  - protocols/rdt.py - RDT协议

**理由**: 后端自包含确保服务器可以独立打包、部署和运行，无需依赖前端代码或其他模块。这种架构支持微服务化演进，后端可以作为独立服务部署在不同服务器上。LLM和工具只在后端使用，集中管理避免版本冲突。存储模块包含业务逻辑（向量存储、对话历史），与运行时数据目录（storage/）分离。

**2. 前端轻量级原则 (Frontend Lightweight Principle)**

clients/ 目录 MUST 只包含前端UI和通信逻辑，MUST 不包含业务逻辑。clients/ 目录结构 MUST 包含：
- clients/cli/ - CLI客户端
  - cli/main.py - 客户端入口
  - cli/ui.py - UI实现
  - cli/nplt_client.py - NPLT协议客户端
  - cli/rdt_client.py - RDT文件传输客户端
  - cli/client_api.py - 客户端API
  - cli/tests/ - 客户端测试
- (未来) clients/web/ - Web客户端
- (未来) clients/desktop/ - Desktop客户端

前端代码 MUST 只负责：
- 用户界面显示和交互
- 协议通信（连接、发送、接收）
- 数据格式转换（协议格式 ↔ UI格式）
- 用户输入处理和验证

前端代码 MUST NOT 包含：
- Agent逻辑
- 工具执行
- LLM调用
- 业务规则

**理由**: 前端轻量级确保客户端可以快速启动、低资源占用。业务逻辑集中在后端，前端只负责展示和通信，职责清晰。这种架构支持多前端（CLI、Web、Desktop）共享相同的后端服务，避免代码重复。前端可以独立开发和迭代，不影响后端逻辑。

**3. 协议共享原则 (Protocol Sharing Principle)**

shared/ 目录 MUST 包含真正前后端共享的代码。shared/ 目录结构 MUST 包含：
- shared/protocols/ - 通信协议定义（前后端都需要）
  - protocols/nplt.py - NPLT协议定义（消息类型、数据格式）
  - protocols/rdt.py - RDT协议定义（包结构、滑动窗口）
- shared/utils/ - 通用工具函数
  - utils/logger.py - 日志工具
  - utils/types.py - 共享类型定义
  - utils/config.py - 配置基础类

shared/ 目录 MUST NOT 包含：
- LLM相关代码（仅在server/中使用）
- 工具实现（仅在server/中使用）
- 业务逻辑（仅在server/中使用）

**理由**: 协议定义是前后端唯一的共享依赖，必须保持一致。将协议放在shared/目录确保前端和服务器使用相同的协议定义，避免不一致导致的通信问题。通用工具（日志、类型）放在shared/避免重复，但业务逻辑（LLM、工具）必须放在server/中，避免前端误用。

**4. 数据存储分离原则 (Data Storage Separation Principle)**

项目 MUST 区分代码模块和运行时数据目录：
- server/storage/ - 后端数据存储模块（代码）
  - storage/vector_store.py - 向量存储实现
  - storage/history.py - 对话历史实现
- storage/ - 运行时数据目录（非代码）
  - storage/vectors/ - 向量索引文件
  - storage/history/ - 对话历史文件
  - storage/uploads/ - 上传文件目录

这种分离确保：
- 代码模块可以独立测试（使用内存存储或mock数据）
- 运行时数据可以独立管理和备份
- 部署时可以灵活配置数据目录位置

**理由**: 代码和数据分离是软件工程的最佳实践。代码模块（.py文件）定义数据结构和操作逻辑，运行时数据目录（vectors/、history/）存储实际数据。这种分离支持：
- 测试灵活性：单元测试可以使用内存存储，集成测试使用真实文件
- 部署灵活性：生产环境可以将数据目录放在高性能磁盘或网络存储
- 备份恢复：只需要备份storage/目录，无需备份代码
- 多实例支持：多个服务器实例可以共享或隔离数据目录

**5. 废弃目录清理原则 (Deprecated Directory Cleanup Principle)**

src/ 目录 MUST 被完全删除，所有功能 MUST 迁移到对应位置：
- src/llm/ → server/llm/（已完成）
- src/tools/ → server/tools/（已完成）
- src/storage/ → server/storage/（代码模块）
- src/utils/ → server/utils/（后端专用）或 shared/utils/（通用工具）
- src/protocols/ → shared/protocols/（已完成）
- src/client/ → clients/cli/（已完成）
- src/server/ → server/（已完成）

删除 src/ 后，项目根目录结构 MUST 为：
```
├── server/          # 后端服务器（可独立部署）
├── clients/         # 前端客户端
├── shared/          # 真正共享的代码（protocols/、utils/）
├── storage/         # 运行时数据目录（vectors/、history/、uploads/）
├── tests/           # 测试代码
├── docs/            # 文档
├── scripts/         # 脚本工具
├── specs/           # 功能规范
├── .specify/        # 项目管理文件
└── pyproject.toml   # 项目配置
```

**理由**: 清晰的目录结构减少认知负担。废弃的src/目录会导致混淆（"我应该在哪个目录写代码？"）。统一的结构使新开发者快速理解项目组织。删除冗余目录减少维护成本（不需要在两个地方同步更改）。

**6. 导入路径规范 (Import Path Standards)**

代码 MUST 使用规范的导入路径：
- 后端代码导入后端模块：`from server.llm.base import LLMProvider`
- 后端代码导入工具：`from server.tools.command import CommandTool`
- 前端代码导入协议：`from shared.protocols.nplt import MessageType`
- 前端代码导入工具：`from shared.utils.logger import get_logger`
- 绝对禁止：`from src.llm.base import LLMProvider`（src/已废弃）

导入路径 MUST 与物理目录结构一致，禁止使用跨层导入（如server/导入clients/）。

**理由**: 规范的导入路径确保代码可读性和可维护性。IDE可以正确解析导入，提供代码补全和跳转功能。跨层导入破坏模块边界，导致紧耦合和不清晰的依赖关系。

### 客户端独立性原则 (Client Independence Principle)

客户端MUST完全独立于服务器代码，拥有自己的协议定义副本。client/目录MUST包含完整的协议定义（client/protocols/nplt.py、client/protocols/rdt.py），MUST不依赖src/protocols/中的服务器代码。客户端MUST有独立的依赖管理（client/pyproject.toml），定义自己的依赖包。客户端MUST能够独立安装和部署，无需服务器代码。客户端协议定义MUST与服务器协议定义保持同步，通过版本检查机制验证兼容性。客户端和服务器MUST独立演进，协议变更时MUST更新双方定义。

**理由**: 客户端独立部署能力是系统架构的关键需求。用户需要在Windows设备上安装CLI或Desktop客户端，连接到远程服务器，而无需整个服务器代码库。独立的协议定义使客户端可以单独分发和打包，降低部署复杂度。独立的依赖管理允许客户端依赖与服务器依赖不同，避免版本冲突。版本检查机制确保协议兼容性，防止不匹配的客户端和服务器通信失败。这种架构支持单仓库多包（monorepo）模式，客户端和服务器在同一仓库中，但可以独立开发和发布。

### 多前端适配器模式原则 (Multi-Frontend Adapter Pattern Principle)

系统MUST实现多前端架构，支持CLI、Web、Desktop三种前端类型。Web前端MUST由服务器直接提供，用户通过浏览器访问，无需独立客户端。CLI客户端MUST使用Python直接运行，支持本地连接（localhost）和远程连接（服务器IP）。Desktop客户端MUST使用PyInstaller打包成独立.exe文件，在Windows设备上安装运行，连接远程服务器。系统MUST使用适配器模式解耦前端和后端：前端应用层（frontends/）依赖适配器层（adapters/），适配器层依赖服务层（services/），服务层依赖协议层（protocols/）和核心层（core/）。每个前端MUST有独立的适配器实现（CLIAdapter、DesktopAdapter），共享相同的服务层和协议层。UI组件MUST可替换（RichUI、DesktopUI），通过UIInterface基类解耦。配置文件MUST支持本地和远程服务器配置（config.yaml中的server.host和server.port）。

**理由**: 多前端架构满足不同用户场景的需求。Web前端无需安装，跨平台使用，适合临时用户。CLI客户端适合开发者和高级用户，支持脚本自动化。Desktop客户端适合普通Windows用户，提供原生GUI体验。适配器模式解耦前端和后端，使新前端可以轻松添加（如未来添加移动端），无需修改核心业务逻辑。共享服务层和协议层避免代码重复，确保所有前端行为一致。可替换的UI组件使前端可以独立优化UI体验，而不影响业务逻辑。配置驱动的服务器连接支持灵活的部署场景（本地开发、远程生产、云服务器）。

### 配置驱动部署原则 (Configuration-Driven Deployment Principle)

客户端MUST通过配置文件（config.yaml）管理所有部署配置。配置文件MUST包含：服务器连接配置（server.host、server.port、server.rdt_port）、连接参数（timeout、auto_reconnect、max_retries）、客户端配置（default_model、max_file_size、log_level）、UI配置（terminal_type、stream_speed、enable_colors）。配置文件MUST支持多层查找：命令行指定（--config）、当前目录（./config/config.yaml）、用户目录（~/.llmchat/config.yaml）、内置默认配置。配置优先级MUST为：命令行参数 > 配置文件 > 默认配置。打包时MUST包含配置文件模板（config.yaml.example），用户首次运行时自动生成默认配置。客户端MUST在启动时加载配置并验证连接参数。

**理由**: 配置驱动部署使客户端可以适应不同环境而无需修改代码。用户可以轻松切换服务器地址（本地测试、远程生产），调整连接参数（超时、重连次数），优化UI体验（流式输出速度、颜色支持）。多层查找机制提供灵活性：开发时使用项目配置，部署时使用系统配置，临时测试使用命令行覆盖。配置模板降低使用门槛，用户可以基于模板快速配置。自动生成默认配置提供良好的首次体验，用户可以立即使用，后续根据需要自定义。配置驱动支持灵活的分发策略：开发版、测试版、生产版可以使用不同的配置文件，无需修改代码。

## 技术约束

- **Python 版本**: MUST 使用 Python 3.11
- **虚拟环境**: MUST 使用 uv 创建和管理虚拟环境
- **LLM SDK**: MUST 使用 zai-sdk 与智谱 AI 集成
- **日志格式**: MUST 使用纯文本 (.log) 格式，存储在 logs 文件夹
- **依赖管理**: 所有依赖 MUST 通过 uv 管理
- **版本控制**: 每个阶段完成并通过测试后 MUST git 提交版本
- **文件访问**: MUST 使用统一的路径白名单控制，配置在 config.yaml 的 file_access.allowed_paths
- **路径验证**: MUST 防止路径遍历攻击（../ 规范化），MUST 验证 glob 模式
- **自动索引**: MUST 支持按需索引，semantic_search 工具 MUST 在首次访问白名单文件时自动创建索引
- **索引存储**: MUST 将向量索引持久化到 storage/vectors/ 目录
- **多层防御**: MUST 实现白名单、黑名单、大小限制、内容类型验证等多层安全机制
- **审计日志**: MUST 记录所有文件访问、索引创建和工具调用操作
- **结构化错误**: 工具执行失败MUST返回ToolExecutionResult，包含ErrorType、suggested_fix、retry_able字段
- **RDT协议**: MUST 实现基于UDP的可靠数据传输，包括滑动窗口（窗口大小5）、超时重传（0.1秒）、CRC16校验和累积ACK
- **多协议路由**: file_download工具 MUST 根据client_type自动选择RDT/HTTP/NPLT协议，优先协议不可用时MUST降级到NPLT
- **Session管理**: Session对象 MUST 包含client_type字段（cli/web/desktop）、uploaded_files字段（List[Dict]）、upload_state字段（Dict）
- **文件上传支持**: MUST 支持文件+用户说明同时发送（CLI: /upload filepath 用户说明，Web: 上传按钮+文本框）
- **文件引用格式**: 用户文本MUST附加file_ref标记（[file_ref:{file_id}]），Agent通过Session.get_uploaded_file()获取文件信息
- **工具职责分离**: Agent工具MUST不处理实际数据传输，协议层（NPLT/RDT/HTTP）负责文件上传/下载的实际数据传输
- **工具数量控制**: 工具总数SHOULD控制在5-7个范围内，功能重复的工具MUST合并
- **代码复用**: 功能相似的工具MUST通过继承提取公共逻辑，代码重复率MUST控制在20%以下
- **混合检索**: semantic_search工具MUST实施精确匹配、模糊匹配、语义检索三层策略，MUST返回match_type字段
- **检索优先级**: 精确匹配（similarity=1.0）→ 模糊匹配（关键词/前缀/通配符）→ 语义检索（向量相似度）
- **检索范围过滤**: semantic_search工具MUST支持scope参数（all/system/uploads），控制检索范围
- **结果去重排序**: 多层检索结果MUST合并去重，按相似度排序返回top_k结果
- **客户端类型**: 当前阶段 ONLY 实现CLI客户端（client_type="cli"），Web和Desktop客户端实现推迟到后续阶段
- **Desktop客户端**: Desktop客户端MUST使用Python GUI框架（Tkinter/PyQt/PySide），MUST支持完整RDT协议UDP通信
- **数据传输格式**: 实时聊天消息MUST使用纯文本，历史记录批量传输MUST使用JSON格式（保留tool_calls、timestamp等结构化数据）
- **协议文档**: 协议格式、消息流和调用链路MUST记录在docs/目录（message-flow-analysis.md、protocol-call-chain.md）
- **工具设计文档**: 工具清单、职责边界、输入输出格式MUST记录在docs/目录（agent_complete_specification.md）
- **项目结构**: MUST遵循前后端分离架构，server/包含所有后端代码，clients/只包含UI和通信，shared/只包含协议和通用工具
- **目录组织**: server/、clients/、shared/、storage/、tests/、docs/、scripts/、specs/、.specify/、pyproject.toml
- **废弃目录**: src/目录MUST被删除，所有功能已迁移到server/、clients/、shared/
- **导入路径**: 后端使用`from server.xxx import`，前端使用`from shared.protocols.xxx import`，禁止使用`from src.xxx import`
- **后端自包含**: server/目录MUST能够独立部署，包含llm/、tools/、storage/、utils/、protocols/
- **前端轻量级**: clients/目录MUST只包含UI和通信逻辑，MUST不包含业务逻辑
- **协议共享**: shared/protocols/ MUST包含前后端共享的协议定义，MUST与server/protocols/保持同步
- **数据分离**: server/storage/是代码模块，storage/是运行时数据目录，两者MUST分离
- **客户端独立性**: 客户端MUST有独立的协议定义副本（client/protocols/），MUST不依赖src/protocols/服务器代码
- **客户端依赖**: 客户端MUST有独立的依赖管理（client/pyproject.toml），MUST能够独立安装和部署
- **协议同步**: 客户端和服务器协议定义MUST保持同步，MUST通过版本检查机制验证兼容性
- **多前端架构**: 系统MUST支持CLI、Web、Desktop三种前端，Web前端由服务器直接提供，CLI和Desktop客户端可独立部署
- **适配器模式**: 前端应用层MUST通过适配器层访问服务层，每个前端MUST有独立的适配器实现（CLIAdapter、DesktopAdapter）
- **配置驱动**: 客户端MUST通过config.yaml管理部署配置，MUST支持多层查找（命令行、当前目录、用户目录、默认配置）
- **PyInstaller打包**: Desktop客户端MUST支持PyInstaller打包成独立.exe文件，MUST包含配置文件模板
- **服务器连接**: 客户端配置MUST支持本地连接（localhost）和远程连接（服务器IP），MUST通过server.host和server.port配置

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
- **文件上传测试**: MUST 测试文件+用户说明同时发送，验证自动索引和Session文件记录
- **文件引用测试**: MUST 测试自然语言文件引用（"这个文件"、"这些文件"、"之前上传的"）
- **工具合并测试**: MUST 测试semantic_search工具同时支持系统文档和用户文件检索（scope参数）
- **工具职责测试**: MUST 测试file_upload工具仅管理索引，不参与实际文件上传
- **结构化错误测试**: MUST 测试工具返回结构化错误（ErrorType、suggested_fix、retry_able）
- **自我修正测试**: MUST 测试Agent根据错误提示进行自我修正和重试
- **混合检索测试**: MUST 测试semantic_search三层检索策略（精确匹配、模糊匹配、语义检索）
- **精确匹配测试**: MUST 测试查询"config.yaml"时直接返回精确匹配（similarity=1.0，match_type=exact_filename）
- **模糊匹配测试**: MUST 测试查询"config"时返回模糊匹配结果（config.yaml、config.json、config.yml）
- **语义检索测试**: MUST 测试查询"数据库配置在哪里"时使用向量语义检索返回相关文档
- **检索优先级测试**: MUST 测试精确匹配优先级高于模糊匹配，模糊匹配优先级高于语义检索
- **match_type字段测试**: MUST 测试检索结果包含match_type字段（exact_filename/fuzzy_filename/semantic）
- **scope过滤测试**: MUST 测试scope参数（all/system/uploads）正确过滤检索范围
- **结果去重测试**: MUST 测试多层检索结果合并去重，不返回重复文件
- **客户端独立性测试**: MUST 测试客户端可以独立安装和运行，不依赖服务器代码
- **协议同步测试**: MUST 测试客户端和服务器协议版本检查，验证兼容性
- **多前端测试**: MUST 测试CLI、Web、Desktop三种前端功能一致性
- **适配器模式测试**: MUST 测试前端通过适配器访问服务层，验证解耦效果
- **配置加载测试**: MUST 测试多层配置查找（命令行、当前目录、用户目录、默认配置）
- **远程连接测试**: MUST 测试客户端连接远程服务器，验证配置文件中的server.host和server.port
- **PyInstaller打包测试**: MUST 测试Desktop客户端打包成.exe后的功能完整性
- **配置文件测试**: MUST 测试配置文件包含所有必需字段，MUST测试首次运行自动生成默认配置
- **项目结构测试**: MUST 测试server/目录能够独立部署，MUST测试clients/目录只包含UI和通信逻辑
- **导入路径测试**: MUST 测试所有导入路径符合规范（禁止from src.xxx import）
- **废弃目录测试**: MUST 验证src/目录已删除，所有功能已迁移到server/、clients/、shared/
- **后端自包含测试**: MUST 测试server/包含所有后端必需代码（llm/、tools/、storage/、utils/、protocols/）
- **协议共享测试**: MUST 测试shared/protocols/与server/protocols/保持同步
- **数据分离测试**: MUST 测试server/storage/（代码模块）和storage/（运行时数据）正确分离

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
- 工具设计变更 MUST 经过设计评审，确认是否符合工具职责单一原则
- 新增工具 MUST 评估是否与现有工具重复，是否可以通过扩展现有工具实现
- 文件检索工具 MUST 验证是否实施混合检索策略（精确/模糊/语义三层）
- 客户端架构变更 MUST 验证是否符合客户端独立性原则
- 多前端实现 MUST 验证是否使用适配器模式解耦前端和后端
- 项目结构变更 MUST 验证是否符合项目结构原则（后端自包含、前端轻量级、协议共享、数据分离）
- 目录重组 MUST 验证是否删除src/目录，所有功能是否正确迁移
- 导入路径变更 MUST 验证是否使用规范路径（server.*、shared.*），禁止使用src.*

**版本**: 1.7.0 | **批准日期**: 2025-12-28 | **最后修正**: 2026-01-01
