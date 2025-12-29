# 统一文件访问白名单系统 - 使用指南

## 📋 概述

本文档描述了 LLMChatAssistant 的统一文件访问安全系统，该系统为所有工具（CommandTool 和 RAGTool）提供一致的文件访问控制。

## 🎯 核心特性

### 1. 统一的路径白名单
- **配置文件**: `config.yaml` 中的 `file_access.allowed_paths`
- **适用范围**: CommandTool 和 RAGTool
- **支持模式**: 普通路径、glob 通配符

### 2. 自动索引机制
- **按需索引**: 访问白名单中的文件时自动创建向量索引
- **懒加载**: 只在首次访问时建立索引
- **透明化**: 用户无需手动操作，系统自动处理

### 3. 多层安全验证
- **路径白名单**: 只允许访问配置的目录
- **路径黑名单**: 拒绝敏感文件模式
- **文件大小限制**: 防止大文件攻击
- **内容类型验证**: 仅允许文本文件

## 📝 配置说明

### config.yaml 配置示例

```yaml
file_access:
  # 允许访问的目录白名单
  allowed_paths:
    - "./workspace"           # 工作区
    - "./storage/uploads"     # 上传文件目录
    - "/var/log/*.log"        # 系统日志（仅 .log 文件）
    - "/tmp/*.txt"            # 临时文本文件

  # 禁止访问的路径模式（黑名单）
  forbidden_patterns:
    - "*/.ssh/*"              # SSH 密钥
    - "*/.env"                # 环境变量文件
    - "*/.git/config"         # Git 配置
    - "/etc/passwd"           # 系统密码文件
    - "/etc/shadow"           # 系统阴影文件
    - "/etc/*secret*"         # 其他密钥文件

  # RAG 索引配置
  indexing:
    auto_index: true          # 自动索引白名单中的文件
    max_file_size: 10485760   # 最大索引文件大小 (10MB)
    chunk_size: 500           # 文本分块大小
    chunk_overlap: 50         # 分块重叠大小

  # 命令执行限制
  command_limits:
    max_output_size: 102400   # 命令输出最大 100KB
    max_files_per_glob: 100   # glob 匹配最大文件数
```

## 🔒 安全特性

### CommandTool 安全增强

#### 1. 路径白名单验证
```python
# ✅ 允许：路径在白名单中
cat.execute(command="cat", args=["./workspace/config.yaml"])

# ❌ 拒绝：路径不在白名单中
cat.execute(command="cat", args=["/etc/passwd"])
# 返回：ToolExecutionResult(success=False, error="路径不在白名单中: /etc/passwd")
```

#### 2. 黑名单模式匹配
```python
# ❌ 拒绝：匹配黑名单模式
cat.execute(command="cat", args=["./project/.env"])
# 返回：ToolExecutionResult(success=False, error="路径匹配禁止模式: */.env")
```

#### 3. 输出大小限制
```python
# 自动截断大输出
ls.execute(command="ls", args=["-R", "./workspace"])
# 输出："... (输出已截断，共 250000 字节)"
```

### RAGTool 自动索引

#### 按需索引流程
```python
# 1. 用户发起搜索
rag_tool.execute_async(query="数据库配置是什么？", top_k=3)

# 2. 系统自动检查索引
# → 如果 ./workspace/config.yaml 未索引

# 3. 自动创建索引
# → 读取文件内容
# → 验证内容类型（仅文本文件）
# → 文本分块（chunk_size=500）
# → 计算嵌入向量
# → 保存到 storage/vectors/

# 4. 返回搜索结果
```

#### 索引状态查询
```python
# 查询文件索引状态
status = index_manager.get_index_status("./workspace/config.yaml")

# 返回：
# {
#     "file_path": "./workspace/config.yaml",
#     "file_id": "a3f5e2b1...",
#     "indexed": true,
#     "allowed": true,
#     "chunks_count": 12,
#     "created_at": "2025-12-29T10:30:00"
# }
```

## 🚀 使用示例

### 示例 1：基本文件搜索

```python
# 用户：搜索工作区中的配置信息
query = "数据库配置是什么？"

# Agent 调用 RAG 工具
result = await rag_tool.execute_async(query=query, top_k=3)

# 系统自动：
# 1. 检查白名单目录中的文件
# 2. 为未索引的文件创建索引
# 3. 执行语义检索
# 4. 返回相关结果
```

### 示例 2：批量索引

```python
# 批量索引白名单目录
results = await index_manager.batch_index("./workspace", pattern="*.md")

# 返回：
# {
#     "./workspace/README.md": (True, "索引创建成功: 15 个分块"),
#     "./workspace/API.md": (True, "索引创建成功: 28 个分块"),
# }
```

### 示例 3：安全命令执行

```python
# ✅ 允许：白名单路径
cat.execute(command="cat", args=["./workspace/app.log"])

# ❌ 拒绝：不在白名单
cat.execute(command="cat", args=["/etc/passwd"])
# 错误："路径不在白名单中: /etc/passwd"

# ❌ 拒绝：黑名单模式
cat.execute(command="cat", args=["./project/.env"])
# 错误："路径匹配禁止模式: */.env"
```

## 📊 安全架构

### 文件访问流程

```
用户请求
   ↓
路径白名单验证
   ↓ (通过)
黑名单模式检查
   ↓ (通过)
文件大小验证
   ↓ (通过)
内容类型验证 (仅 RAG)
   ↓ (通过)
[CommandTool] 执行命令
[RAGTool] 自动索引 + 检索
   ↓
返回结果
```

### 自动索引决策树

```
用户搜索文件
   ↓
文件在白名单中？
   ├─ 否 → 拒绝访问
   └─ 是 → 继续
         ↓
     已索引？
       ├─ 是 → 直接检索
       └─ 否 → 检查文件类型
             ↓
         是文本文件？
           ├─ 否 → 拒绝索引
           └─ 是 → 检查文件大小
                 ↓
             文件 < 10MB？
               ├─ 否 → 拒绝索引
               └─ 是 → 创建索引 → 检索
```

## 🔧 配置建议

### 开发环境
```yaml
file_access:
  allowed_paths:
    - "./workspace"
    - "./storage/uploads"
    - "./tests"
    - "/var/log/*.log"

  forbidden_patterns:
    - "*/.env"
    - "*/.ssh/*"
    - "*/node_modules/*"
```

### 生产环境
```yaml
file_access:
  allowed_paths:
    - "/var/log/app/*.log"
    - "/app/config/*.yaml"
    - "/tmp/uploads/*.txt"

  forbidden_patterns:
    - "*/.ssh/*"
    - "*/.env*"
    - "*/private/*"
    - "/etc/*"
    - "/root/*"
```

### 高安全环境
```yaml
file_access:
  allowed_paths:
    - "/app/logs/*.log"      # 仅日志目录
    - "/app/config/*.yaml"   # 仅配置目录

  forbidden_patterns:
    - "*"                    # 默认拒绝所有
    - "*/secret*"            # 额外保护

  indexing:
    auto_index: false        # 禁用自动索引
    max_file_size: 1048576   # 1MB 限制
```

## ⚠️ 安全注意事项

### 1. 路径遍历防护
```python
# ✅ 安全：路径自动规范化
cat.execute(command="cat", args=["./workspace/../../../etc/passwd"])
# 实际访问：/home/user/project/workspace/../../../etc/passwd
# 验证结果：路径不在白名单中 → 拒绝
```

### 2. Glob 攻击防护
```python
# ⚠️ 需要限制 glob 匹配数量
ls.execute(command="ls", args["-R", "/"])
# 可能返回数万个文件
# → max_files_per_glob: 100
```

### 3. ReDoS 防护
```python
# ⚠️ 危险：复杂正则表达式
grep.execute(command="grep", args["-E", "(a+)+", "huge_file.txt"])
# → 需要添加正则复杂度检查
```

### 4. 敏感信息检测
```python
# 建议：自动检测敏感内容
if "password" in content.lower():
    logger.warning("Potential sensitive data in file")
```

## 🧪 测试

### 单元测试
```bash
# 测试路径验证
pytest tests/unit/test_path_validator.py

# 测试索引管理器
pytest tests/unit/test_index_manager.py

# 测试工具安全
pytest tests/unit/test_command_tool.py
pytest tests/unit/test_rag_tool.py
```

### 集成测试
```bash
# 测试完整文件访问流程
pytest tests/integration/test_file_access.py

# 测试自动索引
pytest tests/integration/test_auto_indexing.py
```

## 📈 性能优化

### 1. 索引缓存
```python
# 避免重复索引
if file_id not in vector_store.list_files():
    await index_manager.ensure_indexed(file_path)
```

### 2. 并发索引
```python
# 批量索引时使用并发
import asyncio

tasks = [
    index_manager.ensure_indexed(file)
    for file in file_list
]
await asyncio.gather(*tasks)
```

### 3. 索引持久化
```python
# 索引自动保存到 storage/vectors/
# 重启后自动加载
vector_store = VectorStore()  # 自动加载所有索引
```

## 🎓 最佳实践

1. **最小权限原则**: 只添加必需的路径到白名单
2. **明确路径模式**: 使用具体的 glob 模式而非通配符
3. **定期审计**: 定期检查白名单和索引文件
4. **监控日志**: 记录所有文件访问和索引操作
5. **测试配置**: 在生产环境前测试白名单配置

## 🔗 相关文档

- [配置管理](../config.yaml)
- [工具系统](../src/tools/)
- [向量存储](../src/storage/vector_store.py)
- [路径验证器](../src/utils/path_validator.py)

## 📞 支持

如有问题，请查看：
- [FAQ](./FAQ.md)
- [安全策略](./security-policy.md)
- [Issue 追踪](https://github.com/your-repo/issues)
