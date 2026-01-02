# uploaded_files 持久化功能实现

## 概述

本次更新实现了 `uploaded_files` 的持久化功能，解决了文件引用在会话重连或服务器重启后丢失的问题。

## 问题背景

**之前的问题**:
- `Session.uploaded_files` 仅存在于内存中
- 会话断开后，文件引用列表丢失
- 服务器重启后，无法引用之前上传的文件
- `file_upload` 工具无法访问历史文件

## 解决方案

将 `uploaded_files` 保存到 `ConversationHistory` 中，随会话历史一起持久化到磁盘。

## 实现细节

### 1. 修改 `ConversationHistory` 数据模型

**文件**: [server/storage/history.py](server/storage/history.py)

#### 添加字段

```python
@dataclass
class ConversationHistory:
    session_id: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime
    uploaded_files: List[dict] = field(default_factory=list)  # 新增
```

#### 添加方法

```python
def add_uploaded_file(self, file_info: dict):
    """添加上传的文件（自动去重）"""

def get_uploaded_files(self) -> List[dict]:
    """获取所有上传的文件（返回副本）"""

def remove_uploaded_file(self, file_id: str) -> bool:
    """移除上传的文件"""
```

#### 修改序列化/反序列化

**save() 方法**:
```python
# datetime 对象转为 ISO 字符串
uploaded_files_serialized = []
for file_info in self.uploaded_files:
    file_copy = file_info.copy()
    if isinstance(file_copy.get("uploaded_at"), datetime):
        file_copy["uploaded_at"] = file_copy["uploaded_at"].isoformat()
    uploaded_files_serialized.append(file_copy)

data["uploaded_files"] = uploaded_files_serialized
```

**load() 方法**:
```python
# ISO 字符串转为 datetime 对象
uploaded_files = []
for file_info in data.get("uploaded_files", []):
    file_copy = file_info.copy()
    if "uploaded_at" in file_copy and isinstance(file_copy["uploaded_at"], str):
        file_copy["uploaded_at"] = datetime.fromisoformat(file_copy["uploaded_at"])
    uploaded_files.append(file_copy)
```

### 2. 修改 `NPLTServer` 文件上传处理

**文件**: [server/nplt_server.py](server/nplt_server.py)

#### 文件上传时同步到 ConversationHistory

```python
# 将文件元数据添加到 session 和 conversation_history
file_info = {
    "file_id": uploaded_file.file_id,
    "filename": uploaded_file.filename,
    "file_path": uploaded_file.storage_path,
    "uploaded_at": uploaded_file.uploaded_at,
    "size": uploaded_file.size,
    "indexed": False
}

# 添加到 session
session.add_uploaded_file(file_info)

# 同步到 conversation_history（持久化）
if session.conversation_history:
    session.conversation_history.add_uploaded_file(file_info)
```

#### 会话切换时恢复 uploaded_files

```python
# 加载新会话的上下文
new_history = ConversationHistory.load(target_session_id)
if new_history:
    session.conversation_history = new_history

    # 同步 uploaded_files 到 session
    session.uploaded_files = new_history.get_uploaded_files()
    print(f"已恢复 {len(session.uploaded_files)} 个上传文件")
```

#### 新会话创建时初始化 uploaded_files

```python
# 为客户端连接创建新的对话历史
session.conversation_history = ConversationHistory.create_new(new_session_id)
session.uploaded_files = []  # 新会话的 uploaded_files
```

### 3. 会话保存（已存在）

**文件**: [server/main.py](server/main.py)

现有的会话保存逻辑已经包含 `uploaded_files`，无需修改：

```python
# 保存对话历史到磁盘
session.conversation_history.save()  # 现在会自动保存 uploaded_files
```

## JSON 文件格式

### 会话历史文件示例

**路径**: `storage/history/session_20260102_test-abc.json`

```json
{
  "session_id": "test-abc123-def456",
  "messages": [
    {
      "role": "user",
      "content": "第一条消息",
      "timestamp": "2026-01-02T16:00:00.000000",
      "tool_calls": [],
      "metadata": {}
    }
  ],
  "uploaded_files": [
    {
      "file_id": "abc123-def456",
      "filename": "config.yaml",
      "file_path": "storage/uploads/abc123-def456/config.yaml",
      "size": 1024,
      "uploaded_at": "2026-01-02T16:00:00.000000",
      "indexed": false
    },
    {
      "file_id": "xyz789-uvw012",
      "filename": "log.txt",
      "file_path": "storage/uploads/xyz789-uvw012/log.txt",
      "size": 2048,
      "uploaded_at": "2026-01-02T16:05:00.000000",
      "indexed": true
    }
  ],
  "created_at": "2026-01-02T16:00:00.000000",
  "updated_at": "2026-01-02T16:05:00.000000"
}
```

## 使用场景

### 场景 1: 会话内文件引用

```python
# 用户上传文件
用户: 上传 config.yaml
AI: 文件已保存

# 用户引用文件（使用代词）
用户: 这个文件里数据库端口是多少？
AI: [调用 file_upload(reference="this")]
   → 找到 config.yaml
   → [调用 semantic_search("数据库端口")]
   → 端口是 5432
```

### 场景 2: 会话切换后文件引用

```python
# 用户在会话A上传文件
会话A: 上传 app.log
AI: 文件已保存

# 用户切换到会话B
用户: /switch session-b
AI: 已切换到会话B

# 用户切换回会话A
用户: /switch session-a
AI: 已切换到会话A
   → uploaded_files 自动恢复
   → app.log 可引用

# 用户引用文件
用户: 这个文件里有错误吗？
AI: [调用 file_upload(reference="this")]
   → 找到 app.log（从历史恢复）
   → [调用 semantic_search("error")]
   → 找到 3 个错误
```

### 场景 3: 服务器重启后文件引用

```python
# 用户上传文件
用户: 上传 test.py
AI: 文件已保存
uploaded_files 已持久化到 session_20260102_xxx.json

# 服务器重启
$ python3 -m server.main
[INFO] 服务器已启动

# 客户端重连，恢复会话
用户: /switch test-abc
AI: 已切换到会话 test-abc
   → 从磁盘加载 ConversationHistory
   → uploaded_files 自动恢复
   → test.py 可引用

# 用户引用文件
用户: 这个文件是做什么的？
AI: [调用 file_upload(reference="this")]
   → 找到 test.py
   → 分析代码功能
```

## 测试验证

### 运行测试

```bash
PYTHONPATH=. python3 test_uploaded_files_persistence.py
```

### 测试覆盖

1. ✅ **ConversationHistory 持久化测试**
   - 添加文件到历史
   - 保存到磁盘
   - 从磁盘加载
   - 验证数据完整性

2. ✅ **JSON 格式验证测试**
   - 验证 JSON 结构
   - 验证 datetime 序列化
   - 验证所有字段存在

3. ✅ **重复文件处理测试**
   - 验证去重机制
   - 确保不会重复添加

### 测试结果

```
============================================================
测试汇总
============================================================
✓ PASS: test_conversation_history_persistence
✓ PASS: test_json_format
✓ PASS: test_duplicate_files

总计: 3/3 通过

🎉 所有测试通过！
```

## 向后兼容性

### 旧会话文件处理

**旧格式** (无 uploaded_files):
```json
{
  "session_id": "old-session",
  "messages": [...],
  "created_at": "2026-01-01T00:00:00.000000",
  "updated_at": "2026-01-01T00:00:00.000000"
}
```

**加载逻辑**:
```python
# 使用 .get() 方法，默认为空列表
uploaded_files = data.get("uploaded_files", [])
```

✅ **旧会话文件可以正常加载，`uploaded_files` 为空列表**

## 优势总结

### 1. 持久化 ✅
- 文件引用保存到磁盘
- 服务器重启后可恢复
- 会话断开后可恢复

### 2. 透明性 ✅
- 对用户透明
- 对工具透明（`file_upload` 工具无需修改）
- 自动同步

### 3. 数据一致性 ✅
- Session 和 ConversationHistory 双写
- 单一数据源（ConversationHistory）
- 自动去重

### 4. 向后兼容 ✅
- 旧会话文件正常加载
- 渐进式迁移

## 未来优化方向

### 短期优化
1. 添加文件删除功能（同时从 disk 和 history 删除）
2. 添加文件引用计数（支持自动清理）
3. 添加文件大小限制验证

### 中期优化
1. 实现全局文件索引（跨会话文件共享）
2. 添加文件版本管理
3. 实现文件归档策略

### 长期优化
1. 迁移到数据库存储（SQLite）
2. 支持文件分组和标签
3. 实现文件访问权限控制

## 相关文件

- **核心修改**:
  - [server/storage/history.py](server/storage/history.py) - ConversationHistory 数据模型
  - [server/nplt_server.py](server/nplt_server.py) - 文件上传和会话切换逻辑
  - [server/main.py](server/main.py) - 会话保存逻辑（无需修改）

- **测试文件**:
  - [test_uploaded_files_persistence.py](test_uploaded_files_persistence.py) - 持久化功能测试

## 总结

本次更新实现了 `uploaded_files` 的完整持久化功能，解决了文件引用丢失的问题，为用户提供了更好的使用体验。所有测试通过，向后兼容，可以安全部署。
