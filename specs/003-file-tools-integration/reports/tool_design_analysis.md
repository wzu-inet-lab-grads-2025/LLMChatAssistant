# Agent工具调用设计问题分析报告

**生成时间**: 2025-12-31 07:35:00
**基于测试**: 功能详细测试报告（91.4%通过率，3个失败案例）

---

## 一、测试失败案例分析

### 案例1: 系统监控 - "查看内存使用情况" ❌

**用户输入**: "查看内存使用情况"
**预期工具**: sys_monitor
**实际工具**: None（未调用工具）

**问题分析**:
1. **提示词示例不完整**: agent.py:387-389只有"内存使用情况"示例，但缺少"查看内存"等动词前缀
2. **"查看"未明确映射**: 提示词中没有明确"查看"、"显示"等动词应使用sys_monitor
3. **LLM理解偏差**: LLM可能认为"查看内存使用情况"是需要直接回答的问题

**当前提示词** (agent.py:387-389):
```python
用户: 内存使用情况
TOOL: sys_monitor
ARGS: {"metric": "memory"}
```

**缺失的示例**:
```python
用户: 查看内存使用情况
TOOL: sys_monitor
ARGS: {"metric": "memory"}

用户: 显示内存
TOOL: sys_monitor
ARGS: {"metric": "memory"}
```

---

### 案例2: 文件上传 - "发送配置文件给你" ❌

**用户输入**: "发送配置文件给你"
**预期工具**: file_upload
**实际工具**: file_semantic_search

**问题分析**:
1. **表述有歧义**: "发送配置文件给你"有两种理解:
   - 理解A: 用户要上传文件 → file_upload ✓
   - 理解B: 用户要下载文件，先搜索 → file_semantic_search → file_download ✓
2. **动词"发送"未明确方向**: "发送给你"（用户→服务器）vs "发给我"（服务器→用户）
3. **工具描述过于简单**: file_upload的description="接收并保存用户上传的文件，支持自动索引"
   - 未明确关键词："上传"、"发送给你"、"传输到服务器"

**当前提示词** (agent.py:411-413):
```python
用户: 我有一个文件要上传
TOOL: file_upload
ARGS: {"filename": "config.yaml", "content": "server:\n  port: 8080", "content_type": "application/yaml"}
```

**问题**:
- 只有一个明确"上传"的示例
- 缺少"发送给你"这种易混淆的示例
- 未区分用户→服务器 vs 服务器→用户

---

### 案例3: RAG检索 - "查找关于日志的文档" ❌

**用户输入**: "查找关于日志的文档"
**预期工具**: rag_search
**实际工具**: file_semantic_search

**根本原因**: **工具职责定义不清** ⚠️

**工具描述对比**:
```python
# rag_search (src/tools/rag.py:23)
description: str = "基于向量索引的语义检索，支持白名单路径自动索引"

# file_semantic_search (src/tools/file_search.py:29)
description: str = "通过自然语言描述语义检索文件"
```

**问题**: 两个工具描述几乎相同！都是"语义检索"，LLM无法区分何时用哪个。

**职责定义**:
- **rag_search**: 检索**文档内容**（README、API文档、配置说明、使用指南等）
- **file_semantic_search**: 检索**文件**（按文件名、路径搜索已上传的文件）

**提示词示例** (agent.py:399-407, 422-424):
```python
### rag_search 示例
用户: 搜索文档中关于配置的说明  # ✓ 明确"文档中"
TOOL: rag_search

用户: 查找关于日志的文档  # ❌ 模糊：是文档内容？还是文件？
TOOL: rag_search  # 预期

### 文件操作示例
用户: 搜索数据库配置文档
TOOL: file_semantic_search  # 实际调用
```

**歧义分析**: "查找关于日志的文档"
- rag_search理解: 搜索文档中关于日志的内容说明
- file_semantic_search理解: 搜索名为"日志"的文档文件

---

## 二、系统提示词问题分析

### 问题1: 工具职责定义不清晰

**位置**: agent.py:302-320

**当前定义**:
```python
## 决策流程

**步骤1: 识别查询类型**
- 系统资源查询（CPU/内存/磁盘使用率、系统状态）→ sys_monitor（优先）
- 具体命令名执行（ls/cat/grep/head/tail/ps/pwd/whoami/df/free）→ command_executor
- 文档/代码搜索（搜索文档、查找说明、检索信息）→ rag_search
- 文件上传（上传文件、发送文件给你）→ file_upload
- 文件下载（下载文件、发给我、把XX文件发给我）→ file_download
- 文件语义检索（搜索XX文件、找找关于XX的文档、有没有XX文档）→ file_semantic_search
- 问候/闲聊 → 直接回答
```

**问题**:
- "文档/代码搜索" vs "文件语义检索" → 都有"搜索"、"检索"，容易混淆
- "查找说明" → 可能是rag_search，也可能是file_semantic_search
- 缺少明确的**区分标准**

### 问题2: 示例不够全面

**sys_monitor示例** (agent.py:381-398):
```python
用户: CPU使用情况
TOOL: sys_monitor
ARGS: {"metric": "cpu"}

用户: 内存使用情况
TOOL: sys_monitor
ARGS: {"metric": "memory"}

用户: 磁盘使用情况
TOOL: sys_monitor
ARGS: {"metric": "disk"}

用户: 系统监控
TOOL: sys_monitor
ARGS: {"metric": "all"}
```

**缺失的常见场景**:
- "查看内存"
- "显示CPU使用率"
- "内存怎么样"
- "CPU使用率是多少"
- "检查磁盘空间"

**建议**: 增加10-15个sys_monitor示例，覆盖各种表述方式

### 问题3: "查看"等动词未明确映射

**问题**: "查看"是一个非常常见的动词，但提示词中没有明确它的使用规则

**可能的场景**:
1. "查看文件内容" → command_executor (cat)
2. "查看内存" → sys_monitor
3. "查看进程" → command_executor (ps)
4. "查看当前目录" → command_executor (pwd)

**当前状态**: 依赖LLM自主判断，容易出错

### 问题4: 文件操作方向不明确

**"发送"的方向性**:
- "发送给你"（用户→服务器）→ file_upload
- "发给我"（服务器→用户）→ file_download 或 file_semantic_search → file_download

**当前提示词** (agent.py:415-420):
```python
用户: 把配置文件发给我
TOOL: file_semantic_search
ARGS: {"query": "配置文件", "top_k": 3}
# 找到文件后，再执行:
TOOL: file_download
ARGS: {"file_path": "/home/zhoutianyu/tmp/LLMChatAssistant/storage/uploads/550e8400/config.yaml"}
```

**问题**: 只说明了"发给我"的情况，未说明"发送给你"的情况

---

## 三、工具描述问题分析

### 问题1: rag_search vs file_semantic_search 职责重叠

**工具描述**:
```python
# rag_search
description: str = "基于向量索引的语义检索，支持白名单路径自动索引"

# file_semantic_search
description: str = "通过自然语言描述语义检索文件"
```

**问题**:
1. 都使用"语义检索"，无法区分
2. rag_search强调"白名单路径自动索引"，但file_semantic_search也会检索已索引的文件
3. **缺少使用场景说明**

**改进建议**:
```python
# rag_search
description: str = """检索文档内容（README、API文档、配置说明、使用指南等）
适用场景：
- 搜索配置说明、API文档内容
- 查找使用方法、部署说明
- 检索文档中的特定信息
关键词：文档说明、配置说明、API、使用方法、部署文档"""

# file_semantic_search
description: str = """检索已上传的文件（按文件名、文件路径、文件内容搜索）
适用场景：
- 搜索已上传的文件（用户之前上传的）
- 查找特定文件（配置文件、日志文件等）
- 按文件内容搜索文件
关键词：文件、上传、搜索文件、找文件"""
```

### 问题2: file_upload关键词不明确

**当前描述**:
```python
description: str = "接收并保存用户上传的文件，支持自动索引"
```

**改进建议**:
```python
description: str = """用户上传文件到服务器（用户→服务器）
适用场景：
- 用户明确说"上传"、"发送给你"、"传输到服务器"
- 用户有文件要发送给服务器
关键词：上传、发送给你、传输到服务器、我有文件"""
```

### 问题3: 所有工具缺少"何时使用"的明确说明

**建议**: 为每个工具添加"使用场景"和"关键词"字段

---

## 四、改进建议

### 建议1: 重写系统提示词 - 工具选择决策树

**当前**: 线性列表，容易混淆
**改进**: 树形决策，每个节点有明确的判断条件

```python
## 工具选择决策树

**第1层: 是否需要工具？**
- 问候类（你好、谢谢、再见）→ 直接回答
- 抽象问题（你能做什么、介绍自己）→ 直接回答
- 其他 → 继续判断

**第2层: 系统资源查询？**
- 包含关键词（CPU、内存、磁盘、系统状态、资源使用）
- 或者动词（查看、显示、检查、监控）+ 资源词
→ sys_monitor

**第3层: 命令执行？**
- 明确命令名（ls、cat、grep、ps、pwd等）
- 或者"列出文件"（ls）、"查看文件内容"（cat）
→ command_executor

**第4层: 文件操作？**
- 4.1 用户→服务器（上传）？
  - 关键词：上传、发送给你、我有文件、传输到服务器
  → file_upload

- 4.2 服务器→用户（下载）？
  - 4.2.1 已知文件名？
    → file_download

  - 4.2.2 未知文件名，需要搜索？
    → file_semantic_search（先搜索）
    → file_download（后下载）

**第5层: 文档检索？**
- 搜索文档内容（配置说明、API文档、使用方法）
- 关键词：文档说明、配置说明、使用方法、API文档
→ rag_search
```

### 建议2: 增加反例（Negative Examples）

**当前**: 只有正例（应该用什么工具）
**改进**: 增加反例（不应该用什么工具）

```python
## 反例示范

❌ 错误示例

用户: 查看内存使用情况
TOOL: 直接回答"内存使用情况是..."  # ❌ 错误：应该使用sys_monitor

用户: 发送配置文件给你
TOOL: file_semantic_search  # ❌ 错误：这是上传，应该用file_upload

用户: 查找关于日志的文档
TOOL: file_semantic_search  # ❌ 错误：这是检索文档内容，应该用rag_search
```

### 建议3: 为每个工具增加10+示例

**当前**: 每个工具2-5个示例
**改进**: 每个工具10-15个示例，覆盖各种表述

**sys_monitor示例扩充**:
```python
### sys_monitor 示例（系统资源查询）

# 直接表述
用户: CPU使用情况
TOOL: sys_monitor
ARGS: {"metric": "cpu"}

用户: 内存使用情况
TOOL: sys_monitor
ARGS: {"metric": "memory"}

用户: 磁盘使用情况
TOOL: sys_monitor
ARGS: {"metric": "disk"}

# 带"查看"动词
用户: 查看CPU使用率
TOOL: sys_monitor
ARGS: {"metric": "cpu"}

用户: 查看内存
TOOL: sys_monitor
ARGS: {"metric": "memory"}

用户: 查看磁盘空间
TOOL: sys_monitor
ARGS: {"metric": "disk"}

# 带"显示"动词
用户: 显示CPU使用率
TOOL: sys_monitor
ARGS: {"metric": "cpu"}

# 带"检查"动词
用户: 检查系统状态
TOOL: sys_monitor
ARGS: {"metric": "all"}

# 问句形式
用户: CPU使用率是多少？
TOOL: sys_monitor
ARGS: {"metric": "cpu"}

用户: 内存怎么样？
TOOL: sys_monitor
ARGS: {"metric": "memory"}

# 模糊表述
用户: 系统资源
TOOL: sys_monitor
ARGS: {"metric": "all"}

用户: 服务器状态
TOOL: sys_monitor
ARGS: {"metric": "all"}
```

### 建议4: 明确区分rag_search和file_semantic_search

**关键区分点**:
1. **rag_search**: 检索**已索引文档的内容**（README、API文档）
   - 用户想知道"文档中关于X的说明"
   - 重点是"内容"而非"文件"

2. **file_semantic_search**: 检索**已上传的文件**
   - 用户想找到"某个文件"
   - 重点是"文件"而非"内容"

**改进示例**:
```python
### rag_search 示例（文档内容检索）

用户: 搜索文档中关于配置的说明  # ✓ "文档中" + "说明"
TOOL: rag_search
ARGS: {"query": "配置说明"}

用户: 查找API文档  # ✓ "API文档"
TOOL: rag_search
ARGS: {"query": "API"}

用户: 使用方法是什么  # ✓ 查文档内容
TOOL: rag_search
ARGS: {"query": "使用方法"}

用户: 部署说明在哪里  # ✓ 查文档内容
TOOL: rag_search
ARGS: {"query": "部署说明"}

### file_semantic_search 示例（文件检索）

用户: 搜索配置文件  # ✓ "文件"
TOOL: file_semantic_search
ARGS: {"query": "配置文件"}

用户: 找一下日志文件  # ✓ "文件"
TOOL: file_semantic_search
ARGS: {"query": "日志文件"}

用户: 有没有README文件  # ✓ "文件"
TOOL: file_semantic_search
ARGS: {"query": "README"}

用户: 搜索我上传的文档  # ✓ "我上传的"（用户的文件）
TOOL: file_semantic_search
ARGS: {"query": "文档"}
```

### 建议5: 明确文件操作的方向性

**上传 vs 下载**:
```python
### file_upload 示例（用户→服务器）

用户: 我有一个文件要上传  # ✓ 明确"上传"
TOOL: file_upload
ARGS: {"filename": "config.yaml", "content": "...", "content_type": "application/yaml"}

用户: 发送文件给你  # ✓ "发送给你" = 上传
TOOL: file_upload
ARGS: {"filename": "log.txt", "content": "...", "content_type": "text/plain"}

用户: 传输配置到服务器  # ✓ "到服务器"
TOOL: file_upload
ARGS: {...}

### file_download 示例（服务器→用户）

用户: 把配置文件发给我  # ✓ "发给我" = 下载
TOOL: file_semantic_search
ARGS: {"query": "配置文件", "top_k": 3}
# 找到文件后，再执行:
TOOL: file_download
ARGS: {"file_path": "/path/to/config.yaml"}

用户: 下载README文件  # ✓ 明确"下载"
TOOL: file_download
ARGS: {"file_path": "/path/to/README.md"}
```

---

## 五、改进优先级

### P0 (紧急) - 影响10%+准确率
1. ✅ **明确rag_search vs file_semantic_search的职责**
   - 更新工具描述
   - 增加对比示例
   - 添加反例

2. ✅ **增加sys_monitor示例**
   - 覆盖"查看"、"显示"、"检查"等动词
   - 覆盖问句形式
   - 至少10个示例

### P1 (重要) - 影响5-10%准确率
3. ✅ **明确文件操作方向**
   - 区分"发送给你"（上传）vs "发给我"（下载）
   - 增加file_upload和file_download的示例
   - 添加工具链示例（先search后download）

4. ✅ **改进工具描述**
   - 添加"适用场景"
   - 添加"关键词"
   - 添加"何时不用此工具"

### P2 (优化) - 影响<5%准确率
5. ⚠️ **重写决策流程**
   - 从线性列表改为树形决策
   - 每个节点有明确判断条件

6. ⚠️ **增加反例示范**
   - 展示常见错误
   - 说明为什么错误

---

## 六、预期改进效果

**当前**: 91.4%准确率 (32/35)

**改进后预期**:
- P0改进: +4% (解决案例1和案例3) → 95.4%
- P1改进: +2.5% (解决案例2及类似) → 97.9%
- P2改进: +1.1% (优化边缘案例) → 99%

**目标**: ≥98%准确率（34-35/35通过）

---

## 七、实施计划

### 阶段1: 快速修复（P0）
**时间**: 立即执行
**内容**:
1. 更新工具描述（rag_search、file_semantic_search）
2. 增加sys_monitor示例（10个）
3. 增加rag_search vs file_semantic_search对比示例
**预期**: 准确率提升至94-95%

### 阶段2: 系统优化（P1）
**时间**: 阶段1完成后
**内容**:
1. 明确文件操作方向（上传vs下载）
2. 增加file_upload和file_download示例
3. 添加工具链示例
**预期**: 准确率提升至97-98%

### 阶段3: 精细化优化（P2）
**时间**: 阶段2完成后
**内容**:
1. 重写决策流程（树形结构）
2. 增加反例示范
3. 增加边缘案例示例
**预期**: 准确率提升至98-99%

---

## 八、验证方法

### 测试用例扩充
**当前**: 35个测试用例
**扩充**: 50-70个测试用例

**新增测试类别**:
1. **动词前缀测试**: "查看"、"显示"、"检查"、"监控"
2. **方向性测试**: "发送给你" vs "发给我"
3. **文档检索测试**: 区分文档内容 vs 文件
4. **边缘案例**: 模糊表述、多义词

### 回归测试
每次改进后：
1. 运行完整测试套件
2. 确保之前通过的测试仍然通过
3. 新增测试用例验证改进效果

---

**报告生成时间**: 2025-12-31 07:35:00
**分析者**: Claude Code
**基于测试**: 功能详细测试报告（91.4%通过率）
**下一步**: 执行阶段1快速修复（P0）
