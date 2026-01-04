# 变更：审阅后端所有功能的实现

## 为什么

当前后端功能已经实现完成，包括ReAct Agent、工具链、聊天功能、文件传输等核心能力，但现有的测试文件都是老旧的，无法反映当前的实现状态。需要删除所有老旧测试，重新编写全面的集成测试来验证这些功能在实际使用智谱API的场景下是否能正确工作。特别需要关注后端与前端的交互、数据持久化、上下文管理、以及Agent意图识别和多工具协作的准确性等关键环节。

## 变更内容

- **删除所有老旧测试文件**（tests/目录下的现有测试）
- 重新设计测试架构和测试用例
- 审阅后端所有核心功能的实现正确性
- 重点测试ReAct Agent的完整工作流程（包括多轮工具调用）
- 验证工具链调用的正确性和可靠性
- 测试聊天功能的流式输出
- **新增：后端与前端的通信测试**
- **新增：历史聊天记录的持久化测试**
- **新增：文件上传、存储、索引的完整流程测试**
- **新增：上下文管理（包括上传文件后的上下文）测试**
- **重点：Agent意图识别测试（区分命令执行、工具调用、直接聊天、多工具协作）**
- 使用真实的智谱API进行端到端测试
- 每个功能至少准备5个不同的测试样例
- 生成详细的测试报告，包括：
  - 测试样例输入
  - 工具链调用情况（如果有）
  - 最终传递给前端的具体结果信息

## 影响范围

- 受影响规范：
  - 新增：testing规范（测试要求和标准）
- 受影响代码：
  - **tests/** - 删除所有现有测试，重新编写
  - server/agent.py - ReAct Agent核心逻辑（待审阅）
  - server/tools/*.py - 所有工具实现（待审阅）
  - server/llm/zhipu.py - 智谱API集成（待审阅）
  - server/nplt_server.py - 服务器通信协议（待审阅）
  - server/storage/history.py - 历史记录存储（待审阅）
  - server/storage/vector_store.py - 向量存储（待审阅）
  - server/storage/index_manager.py - 索引管理（待审阅）
  - server/main.py - 服务器主入口（待审阅）

## 测试重点

### 1. ReAct Agent功能测试（5+样例）
- 简单对话（无需工具）
- 单工具调用
- 多工具串行调用
- 工具调用失败处理
- 流式输出正确性

### 2. 工具链测试（每个工具5+样例）
- **command_executor** - 10个白名单命令（ls, cat, grep, head, tail, ps, pwd, whoami, df, free）
- **sys_monitor** - CPU/内存/磁盘监控
- **semantic_search** - 混合检索策略（精确→模糊→语义）
- **file_upload** - 文件索引管理
- **file_download** - 文件下载准备

### 3. Agent意图识别和多工具协作测试（重点，15+样例）

**场景A：自然语言描述的命令 → 应调用command_executor**
- "查看当前目录的文件" → command_executor: ls -la
- "列出所有文件" → command_executor: ls -la
- "显示CPU和内存使用情况" → sys_monitor: all（优先使用sys_monitor）
- "显示进程信息" → command_executor: ps aux
- "查看当前目录" → command_executor: pwd

**场景B：直接命令 → 应调用command_executor**
- "ls -la" → command_executor: ls -la
- "df -h" → command_executor: df -h
- "cat config.yaml" → command_executor: cat config.yaml
- "grep error log" → command_executor: grep error log
- "ps aux" → command_executor: ps aux

**场景C：关于命令的询问 → 应直接聊天，不调用工具**
- "介绍一下df指令" → 直接聊天，不调用工具
- "ls命令有什么用" → 直接聊天，不调用工具
- "grep怎么使用" → 直接聊天，不调用工具
- "请解释一下ps aux的含义" → 直接聊天，不调用工具
- "cat和more的区别是什么" → 直接聊天，不调用工具

**场景D：系统状态查询 → 应调用sys_monitor（优先）**
- "系统状态如何" → sys_monitor: all
- "CPU使用率" → sys_monitor: cpu
- "内存情况" → sys_monitor: memory
- "磁盘空间" → sys_monitor: disk
- "监控一下" → sys_monitor: all

**场景E：简单文件检索 → 应调用semantic_search**
- "搜索config.yaml文件" → semantic_search: "config.yaml"（精确匹配）
- "找一下日志文件" → semantic_search: "log"（模糊匹配）
- "关于数据库的文档" → semantic_search: "数据库配置"（语义检索）
- "README文件在哪里" → semantic_search: "README"
- "搜索yaml配置文件" → semantic_search: "yaml"

**场景F：多工具协作场景（重点测试，验证ReAct循环）**
- "查看配置文件内容" → 期望流程：
  1. semantic_search搜索"config.yaml"，找到文件路径
  2. command_executor执行"cat [filepath]"显示内容
- "搜索日志中的错误信息" → 期望流程：
  1. semantic_search搜索"log"文件，找到日志文件路径
  2. command_executor执行"grep 'error' [filepath]"或"grep -i error [filepath]"
- "数据库配置是什么" → 期望流程：
  1. semantic_search搜索"数据库配置"相关文档
  2. 如果找到配置文件，command_executor执行"cat [filepath]"显示内容
  3. 如果找到文档片段，直接基于检索结果回答
- "查看项目的README文档" → 期望流程：
  1. semantic_search搜索"README"
  2. command_executor执行"cat [README路径]"显示内容
- "检查日志文件是否有异常" → 期望流程：
  1. semantic_search搜索".log"文件
  2. command_executor执行"tail -n 50 [logfile]"或"grep 'error\|exception\|fail' [logfile]"

**验证要点：**
- Agent能否正确区分不同场景（命令执行 vs 工具调用 vs 直接聊天）
- 能否正确识别需要多工具协作的场景
- ReAct循环能否正确执行多轮工具调用（最多5轮）
- 每轮工具调用的结果能否正确传递到下一轮决策
- 工具调用的参数是否正确（特别是semantic_search返回的文件路径能否被command_executor正确使用）
- 是否会在不应该调用工具时误调用（如命令介绍类问题）
- system_prompt中的决策流程是否有效

### 4. 后端与前端通信测试（5+样例）
- 验证后端能否正确发送消息给前端
- 测试NPLT协议消息编码/解码
- 验证流式输出的分块传输
- 测试状态通知（thinking、tool_call、generating）
- 验证错误消息的正确传递
- 测试文件下载提议（DOWNLOAD_OFFER）消息

### 5. 历史聊天记录持久化测试（5+样例）
- 验证对话历史正确保存到磁盘（storage/history/）
- 测试会话恢复后历史记录的加载
- 验证工具调用记录的保存（tool_calls字段）
- 测试多会话的历史隔离
- 验证历史记录格式（role, content, timestamp, tool_calls, metadata）
- 测试历史记录的增删改查

### 6. 文件上传、存储、索引测试（5+样例）
- 验证文件上传到storage/uploads/{file_id}/
- 测试文件元数据的保存（filename, file_size, file_id, uploaded_at, indexed）
- 验证白名单文件的自动索引
- 测试索引文件的向量化和存储
- 验证文件索引与session.uploaded_files的关联
- 测试大文件分块上传

### 7. 上下文管理测试（5+样例）
- 验证对话历史正确传递给LLM
- 测试上下文窗口限制（max_turns=5）
- 验证系统提示词的正确注入
- 测试工具调用结果加入上下文
- 验证多轮对话的上下文连贯性

### 8. 上传文件后的上下文管理测试（5+样例）
- 验证uploaded_files通过session对象传递给工具
- 测试文件代词引用的解析（"这个文件"、"这两个文件"、"之前上传的"）
- 验证文件路径在工具中的正确使用
- 测试上传文件后的语义检索
- 验证文件引用跨对话的持久化

### 9. 聊天功能测试（5+样例）
- 正常对话流程
- 流式输出实时性
- 会话管理（创建、切换、删除、列出）
- 自动命名（第3轮对话后触发）
- 会话消息计数

### 10. 错误处理测试（5+样例）
- API调用失败降级
- 工具执行超时
- 参数验证失败
- 网络连接问题
- 文件访问权限问题

## 测试报告格式

每个测试样例的报告必须包含：

```markdown
### 测试样例 X：[测试名称]

**测试类别：** [ReAct Agent/意图识别/多工具协作/工具链/通信/持久化/上下文管理/文件处理/聊天/错误处理]

**测试输入：**
```
[用户输入或操作描述]
```

**预期行为：**
- [步骤1] - [期望的工具/操作]
- [步骤2] - [期望的工具/操作]
- ...

**实际工具链调用情况：**

**第1轮工具调用：**
- 工具名称：[tool_name]
- 调用参数：[args]
- 执行结果：[result]
- 执行时长：[duration]

**第2轮工具调用（如果有）：**
- 工具名称：[tool_name]
- 调用参数：[args]
- 执行结果：[result]
- 执行时长：[duration]

...

**传递给前端的消息序列：**
```json
[
  // 消息1: AGENT_THOUGHT (stream_start)
  {"Type": 3, "Seq": 1, "Len": 45, "Data": "{\"type\":\"thinking\",\"content\":\"正在分析用户意图\"}"},

  // 消息2: AGENT_THOUGHT (tool_call)
  {"Type": 3, "Seq": 2, "Len": 52, "Data": "{\"type\":\"tool_call\",\"content\":\"正在调用工具: semantic_search\"}"},

  // 消息3-N: CHAT_TEXT (streaming)
  {"Type": 1, "Seq": 3, "Len": 20, "Data": "根据搜索结果..."},

  // 最后消息: CHAT_TEXT (empty, stream_end)
  {"Type": 1, "Seq": N, "Len": 0, "Data": ""}
]
```

**历史记录存储：**
```json
{
  "session_id": "uuid",
  "messages": [
    {
      "role": "user",
      "content": "[用户输入]",
      "timestamp": "2025-01-02T12:00:00",
      "tool_calls": []
    },
    {
      "role": "assistant",
      "content": "[AI完整回复]",
      "timestamp": "2025-01-02T12:00:05",
      "tool_calls": [
        {
          "tool_name": "semantic_search",
          "arguments": {"query": "config.yaml", "top_k": 1},
          "result": "[工具结果]",
          "status": "success",
          "duration": 0.52
        }
      ]
    }
  ],
  "uploaded_files": []
}
```

**测试结果：** ✓ 通过 / ✗ 失败 / ⚠ 部分通过

**问题/备注：**
[如果失败，描述具体问题和预期行为的差异；如果通过，记录关键观察；如果部分通过，说明哪些环节正确，哪些有问题]
```

## 预期成果

- **全新的测试套件**（替换所有老旧测试）
- **详细的测试报告**（Markdown格式），包含：
  - 执行摘要（通过率、失败率、问题统计）
  - 每个测试样例的完整记录（输入、多轮工具调用、输出）
  - **意图识别准确率统计**（分类统计：A/B/C/D/E/F场景的识别准确率）
  - **多工具协作成功率**（场景F的测试结果）
  - 发现的问题清单（按严重程度分级：严重/中等/轻微）
  - 改进建议和修复优先级
  - 测试覆盖率统计（功能覆盖率、代码覆盖率）
  - 性能指标（响应时间、成功率、资源使用）
  - **实际行为 vs 预期行为对比表**
