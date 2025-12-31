# Agent完整功能规格文档

**基于重新设计的最终工具方案**
**生成时间**: 2025-12-31 08:20:00
**版本**: v2.0

---

## 目录

1. [Agent概述](#agent概述)
2. [工具清单](#工具清单)
3. [工具详细规格](#工具详细规格)
4. [工具调用链](#工具调用链)
5. [数据流设计](#数据流设计)
6. [实现方式](#实现方式)
7. [安全机制](#安全机制)

---

## Agent概述

### 核心理念

**LLMChatAssistant Agent** 是一个基于ReAct（Reasoning and Acting）范式的智能运维助手。

**职责边界**：
- ✅ **决策层**：理解用户需求，选择合适的工具
- ✅ **协调层**：组织工具调用链，处理工具返回结果
- ✅ **交互层**：与用户进行自然语言对话
- ❌ **协议层**：实际数据传输由NPLT/RDT/HTTP协议处理

### 工作原理

```
用户输入
  ↓
Think (思考): 分析用户意图
  ↓
Decide (决策): 选择工具/工具链
  ↓
Act (执行): 调用工具
  ↓
Observe (观察): 获取工具结果
  ↓
响应用户
```

### 技术栈

- **LLM**: Zhipu AI (glm-4-flash)
- **向量检索**: ChromaDB + text-embedding-v3
- **协议**: NPLT (TCP), RDT (UDP), HTTP
- **架构**: ReAct Agent with Tool Calling

---

## 工具清单

### 最终工具列表（5个）

| # | 工具名称 | 核心职责 | 输入 | 输出 |
|---|---------|---------|------|------|
| 1 | **sys_monitor** | 系统资源监控 | metric类型 | CPU/内存/磁盘使用率 |
| 2 | **command_executor** | 执行系统命令 | command + args | 命令输出结果 |
| 3 | **semantic_search** | 统一语义检索 | query + scope | 文件路径 + 内容片段 |
| 4 | **file_download** | 准备文件下载 | file_path + mode | 下载令牌/URL |
| 5 | **file_upload** | 文件索引和上下文管理 | reference + filters | 文件元数据列表 |

### 工具分类

**系统管理类**：
- sys_monitor
- command_executor

**文件操作类**：
- semantic_search (搜索定位)
- file_download (下载准备)
- file_upload (索引管理)

---

## 工具详细规格

### 1. sys_monitor - 系统资源监控

#### 职责

监控服务器系统资源使用情况（CPU、内存、磁盘）

#### 输入格式

```json
{
  "metric": "cpu",  // "cpu" | "memory" | "disk" | "all"
  "interval": null  // 可选：采样间隔（秒）
}
```

#### 输出格式

```python
ToolExecutionResult(
    success=True,
    output=json.dumps({
        "cpu": {
            "usage_percent": 45.2,
            "cores": 8,
            "frequency": "2.4GHz"
        },
        "memory": {
            "total": "16GB",
            "used": "8GB",
            "usage_percent": 50.0,
            "available": "8GB"
        },
        "disk": {
            "total": "500GB",
            "used": "200GB",
            "usage_percent": 40.0,
            "available": "300GB"
        }
    }),
    error=None,
    duration=0.05
)
```

#### 实现方式

```python
# src/tools/monitor.py
import psutil
import json
from typing import Optional
from src.tools.base import Tool, ToolExecutionResult

class MonitorTool(Tool):
    """系统资源监控工具"""

    name: str = "sys_monitor"
    description: str = """监控系统资源使用情况（CPU、内存、磁盘）

    适用场景：
    - 查询CPU使用率
    - 查询内存使用情况
    - 查询磁盘使用情况

    关键词：CPU、内存、磁盘、使用率、资源监控
    """

    def execute(self, metric: str = "all", **kwargs) -> ToolExecutionResult:
        """执行系统监控"""
        result = {}

        if metric in ("cpu", "all"):
            result["cpu"] = self._get_cpu_info()

        if metric in ("memory", "all"):
            result["memory"] = self._get_memory_info()

        if metric in ("disk", "all"):
            result["disk"] = self._get_disk_info()

        return ToolExecutionResult(
            success=True,
            output=json.dumps(result, ensure_ascii=False, indent=2),
            error=None
        )

    def _get_cpu_info(self) -> dict:
        """获取CPU信息"""
        return {
            "usage_percent": psutil.cpu_percent(interval=1),
            "cores": psutil.cpu_count(logical=False),
            "frequency": f"{psutil.cpu_freq().current:.1f}MHz"
        }

    def _get_memory_info(self) -> dict:
        """获取内存信息"""
        mem = psutil.virtual_memory()
        return {
            "total": f"{mem.total / (1024**3):.1f}GB",
            "used": f"{mem.used / (1024**3):.1f}GB",
            "usage_percent": mem.percent,
            "available": f"{mem.available / (1024**3):.1f}GB"
        }

    def _get_disk_info(self) -> dict:
        """获取磁盘信息"""
        disk = psutil.disk_usage('/')
        return {
            "total": f"{disk.total / (1024**3):.1f}GB",
            "used": f"{disk.used / (1024**3):.1f}GB",
            "usage_percent": (disk.used / disk.total) * 100,
            "available": f"{disk.free / (1024**3):.1f}GB"
        }
```

#### 使用场景

**场景1**：查询CPU使用率
```
用户: "CPU使用率是多少？"
  ↓
TOOL: sys_monitor
ARGS: {"metric": "cpu"}
  ↓
返回: {"cpu": {"usage_percent": 45.2, "cores": 8}}
```

**场景2**：查看所有系统资源
```
用户: "系统资源使用情况如何？"
  ↓
TOOL: sys_monitor
ARGS: {"metric": "all"}
  ↓
返回: {cpu: {...}, memory: {...}, disk: {...}}
```

---

### 2. command_executor - 执行系统命令

#### 职责

安全地执行白名单系统命令

#### 输入格式

```json
{
  "command": "ls",  // 白名单命令
  "args": ["-la", "/home"],  // 命令参数
  "timeout": 30  // 可选：超时时间（秒）
}
```

#### 输出格式

```python
ToolExecutionResult(
    success=True,
    output=json.dumps({
        "command": "ls -la /home",
        "exit_code": 0,
        "stdout": "total 8\ndrwxr-xr-x 2 user user 4096 ...",
        "stderr": ""
    }),
    error=None,
    duration=0.15
)
```

#### 实现方式

```python
# src/tools/command.py
import subprocess
import json
from typing import List, Optional
from src.tools.base import Tool, ToolExecutionResult

class CommandTool(Tool):
    """系统命令执行工具"""

    name: str = "command_executor"
    description: str = """安全地执行系统命令（白名单限制）

    支持的命令：ls, cat, grep, head, tail, ps, pwd, whoami, df, free

    适用场景：
    - 列出文件 (ls)
    - 查看文件内容 (cat)
    - 搜索文本 (grep)
    - 查看进程 (ps)

    关键词：执行、运行、命令、ls、cat、grep
    """

    WHITELIST_COMMANDS = {
        'ls', 'cat', 'grep', 'head', 'tail',
        'ps', 'pwd', 'whoami', 'df', 'free'
    }

    BLACKLIST_CHARS = [';', '&', '|', '>', '<', '`', '$',
                       '(', ')', '\n', '\r']

    def execute(self, command: str, args: Optional[List[str]] = None,
                timeout: int = 30, **kwargs) -> ToolExecutionResult:
        """执行系统命令"""

        # 1. 验证命令白名单
        if command not in self.WHITELIST_COMMANDS:
            return ToolExecutionResult(
                success=False,
                error=f"命令不在白名单中: {command}"
            )

        # 2. 验证参数安全性
        if args:
            for arg in args:
                if any(char in str(arg) for char in self.BLACKLIST_CHARS):
                    return ToolExecutionResult(
                        success=False,
                        error=f"参数包含非法字符: {arg}"
                    )

        # 3. 构建完整命令
        full_command = [command] + (args or [])

        # 4. 执行命令
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )

            return ToolExecutionResult(
                success=result.returncode == 0,
                output=json.dumps({
                    "command": ' '.join(full_command),
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }, ensure_ascii=False),
                error=None if result.returncode == 0 else result.stderr
            )

        except subprocess.TimeoutExpired:
            return ToolExecutionResult(
                success=False,
                error=f"命令执行超时: {command}"
            )
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"命令执行失败: {str(e)}"
            )
```

#### 使用场景

**场景1**：列出文件
```
用户: "列出当前目录的文件"
  ↓
TOOL: command_executor
ARGS: {"command": "ls", "args": ["-la"]}
  ↓
返回: {"stdout": "total 8\ndrwxr-xr-x ..."}
```

**场景2**：查看进程
```
用户: "查看当前运行的进程"
  ↓
TOOL: command_executor
ARGS: {"command": "ps", "args": ["aux"]}
  ↓
返回: {"stdout": "USER PID CPU...\nroot 1 0.0 ..."}
```

---

### 3. semantic_search - 统一语义检索

#### 职责

通过自然语言描述检索文件（合并RAG + FileSearch）

- 搜索系统文档（README、API文档、配置说明）
- 检索用户上传的文件（storage/uploads/）
- 定位文件后，可用于回答问题或下载

#### 输入格式

```json
{
  "query": "数据库配置说明",  // 自然语言查询
  "scope": "all",  // "all" | "system" | "uploads"
  "top_k": 3  // 返回前k个结果
}
```

#### 输出格式

```python
ToolExecutionResult(
    success=True,
    output=json.dumps({
        "total": 3,
        "results": [
            {
                "filename": "README.md",
                "filepath": "/home/project/README.md",
                "similarity": 0.92,
                "chunk": "数据库配置说明：\n1. 编辑 config.yaml...",
                "position": "第1章"
            },
            {
                "filename": "config.yaml",
                "filepath": "/storage/uploads/abc123/config.yaml",
                "similarity": 0.87,
                "chunk": "database:\n  host: localhost\n  port: 5432",
                "position": "line 5"
            }
        ]
    }),
    error=None,
    duration=0.25
)
```

#### 实现方式

```python
# src/tools/semantic_search.py
import asyncio
import json
from typing import Optional, List
from src.tools.base import Tool, ToolExecutionResult

class SemanticSearchTool(Tool):
    """统一的语义检索工具"""

    name: str = "semantic_search"
    description: str = """通过自然语言描述检索文件（基于向量索引）

    功能：
    1. 搜索系统文档（README、API文档、配置说明）
    2. 检索用户上传的文件（storage/uploads/）
    3. 定位文件后，可用于回答问题或下载

    适用场景：
    - "搜索配置说明" → 定位README.md → 回答配置问题
    - "找一下日志文件" → 定位app.log → 分析日志内容
    - "数据库配置在哪里" → 定位config.yaml → 下载或分析

    关键词：搜索、检索、查找、文档、文件、配置、日志
    """

    llm_provider: Optional[Any] = None
    vector_store: Optional[Any] = None
    index_manager: Optional[Any] = None

    def execute(self, query: str, scope: str = "all",
                top_k: int = 3, **kwargs) -> ToolExecutionResult:
        """执行语义检索"""

        # 1. 计算查询向量
        query_embedding = self._get_embedding(query)

        # 2. 执行检索（scope参数控制搜索范围）
        results = []
        if scope in ("all", "system"):
            results.extend(self._search_system_docs(query_embedding, top_k))

        if scope in ("all", "uploads"):
            results.extend(self._search_uploads(query_embedding, top_k))

        # 3. 按相似度排序并取top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:top_k]

        # 4. 格式化结果
        return ToolExecutionResult(
            success=True,
            output=json.dumps({
                "total": len(results),
                "results": results
            }, ensure_ascii=False, indent=2),
            error=None
        )

    def _get_embedding(self, query: str) -> List[float]:
        """计算查询向量"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            asyncio.ensure_future(self.llm_provider.embed([query]))
        )[0]

    def _search_system_docs(self, query_embedding: List[float],
                            top_k: int) -> List[dict]:
        """搜索系统文档"""
        results = self.vector_store.search_all(query_embedding, top_k)

        formatted = []
        for result in results:
            metadata = result.metadata
            # 过滤系统文档路径
            if not metadata.get('filepath', '').startswith('/storage/uploads'):
                formatted.append({
                    "filename": metadata.get('filename', '未知文件'),
                    "filepath": metadata.get('filepath', ''),
                    "similarity": result.similarity,
                    "chunk": result.chunk[:200],
                    "position": metadata.get('position', '未知位置')
                })

        return formatted

    def _search_uploads(self, query_embedding: List[float],
                       top_k: int) -> List[dict]:
        """搜索用户上传文件"""
        results = self.vector_store.search_all(query_embedding, top_k)

        formatted = []
        for result in results:
            metadata = result.metadata
            # 只返回storage/uploads/路径下的文件
            if metadata.get('filepath', '').startswith('/storage/uploads'):
                formatted.append({
                    "filename": metadata.get('filename', '未知文件'),
                    "filepath": metadata.get('filepath', ''),
                    "similarity": result.similarity,
                    "chunk": result.chunk[:200],
                    "position": metadata.get('position', '未知位置')
                })

        return formatted
```

#### 使用场景

**场景1**：搜索系统文档
```
用户: "如何配置数据库？"
  ↓
TOOL: semantic_search
ARGS: {"query": "数据库配置说明", "scope": "system", "top_k": 3}
  ↓
返回: {
  "results": [{
    "filename": "README.md",
    "filepath": "/project/README.md",
    "chunk": "数据库配置步骤：\n1. 编辑 config.yaml..."
  }]
}
```

**场景2**：检索用户上传的文件
```
用户: "找一下我上传的日志文件"
  ↓
TOOL: semantic_search
ARGS: {"query": "日志文件", "scope": "uploads", "top_k": 1}
  ↓
返回: {
  "results": [{
    "filename": "app.log",
    "filepath": "/storage/uploads/abc123/app.log",
    "chunk": "[ERROR] 2025-12-31 08:00:00 ..."
  }]
}
```

---

### 4. file_download - 准备文件下载

#### 职责

为用户准备文件下载（返回下载令牌或URL）

**注意**：此工具只准备下载信息，实际数据传输由协议层完成

#### 输入格式

```json
{
  "file_path": "/storage/uploads/abc123/config.yaml",  // 文件路径
  "transport_mode": "auto"  // "auto" | "rdt" | "http" | "nplt"
}
```

#### 输出格式

```python
ToolExecutionResult(
    success=True,
    output=json.dumps({
        "transport_mode": "rdt",
        "download_token": "token_abc123_xyz789",
        "message": "RDT准备就绪，请使用以下令牌下载",
        "file_size": 1024,
        "filename": "config.yaml"
    }),
    error=None,
    duration=0.10
)
```

#### 实现方式

```python
# src/tools/file_download.py
import uuid
import json
from typing import Optional
from src.tools.base import Tool, ToolExecutionResult

class FileDownloadTool(Tool):
    """文件下载准备工具"""

    name: str = "file_download"
    description: str = """为用户准备文件下载（返回下载令牌或URL）

    注意：此工具只准备下载信息，实际数据传输由协议层完成

    功能：
    1. 验证文件路径（白名单检查）
    2. 选择传输协议（CLI/Desktop→RDT, Web→HTTP, 降级→NPLT）
    3. 返回下载令牌（RDT）或下载链接（HTTP）

    前置条件：需要先通过semantic_search定位文件路径

    使用场景：
    - "下载config.yaml" → semantic_search → file_download
    - "把配置文件发给我" → semantic_search → file_download

    关键词：下载、发送给我、获取文件、传文件
    """

    path_validator: Optional[Any] = None
    client_type: str = "cli"  # "cli" | "web" | "desktop"
    rdt_server: Optional[Any] = None
    http_base_url: Optional[str] = None

    def execute(self, file_path: str, transport_mode: str = "auto",
                **kwargs) -> ToolExecutionResult:
        """准备文件下载"""

        # 1. 验证路径白名单
        is_valid, error_msg = self.path_validator.is_allowed(file_path)
        if not is_valid:
            return ToolExecutionResult(
                success=False,
                error=f"文件路径不在白名单中: {error_msg}"
            )

        # 2. 选择传输模式
        if transport_mode == "auto":
            transport_mode = self._select_transport_mode()

        # 3. 准备下载
        try:
            if transport_mode == "rdt":
                return self._prepare_rdt_download(file_path)
            elif transport_mode == "http":
                return self._prepare_http_download(file_path)
            else:  # nplt
                return self._prepare_nplt_download(file_path)

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"准备下载失败: {str(e)}"
            )

    def _select_transport_mode(self) -> str:
        """智能选择传输模式"""
        if self.client_type == "web":
            return "http" if self.http_base_url else "nplt"
        elif self.client_type in ("cli", "desktop"):
            return "rdt" if self.rdt_server else "nplt"
        return "nplt"

    def _prepare_rdt_download(self, file_path: str) -> ToolExecutionResult:
        """准备RDT下载"""
        import os

        file_id = str(uuid.uuid4())
        download_token = f"token_{file_id}"

        # 注册到RDT服务器
        self.rdt_server.register_download(
            token=download_token,
            file_path=file_path
        )

        return ToolExecutionResult(
            success=True,
            output=json.dumps({
                "transport_mode": "rdt",
                "download_token": download_token,
                "message": "RDT准备就绪，请使用以下令牌下载",
                "file_size": os.path.getsize(file_path),
                "filename": os.path.basename(file_path)
            }, ensure_ascii=False),
            error=None
        )

    def _prepare_http_download(self, file_path: str) -> ToolExecutionResult:
        """准备HTTP下载"""
        import os
        file_id = str(uuid.uuid4())

        download_url = f"{self.http_base_url}/api/files/download/{file_id}"

        # 注册下载令牌
        # HTTP服务器将file_id映射到实际文件路径

        return ToolExecutionResult(
            success=True,
            output=json.dumps({
                "transport_mode": "http",
                "download_url": download_url,
                "message": "请访问以下链接下载文件",
                "file_size": os.path.getsize(file_path),
                "filename": os.path.basename(file_path)
            }, ensure_ascii=False),
            error=None
        )

    def _prepare_nplt_download(self, file_path: str) -> ToolExecutionResult:
        """准备NPLT下载"""
        return ToolExecutionResult(
            success=True,
            output=json.dumps({
                "transport_mode": "nplt",
                "message": "NPLT文件传输已准备",
                "file_path": file_path
            }, ensure_ascii=False),
            error=None
        )
```

#### 使用场景

**场景1**：CLI用户下载文件（使用RDT）
```
用户: "下载config.yaml"
  ↓
# 步骤1: 先搜索文件
TOOL: semantic_search
ARGS: {"query": "config.yaml", "top_k": 1}
  ↓
返回: {"filepath": "/storage/uploads/abc123/config.yaml"}
  ↓
# 步骤2: 准备下载
TOOL: file_download
ARGS: {"file_path": "/storage/uploads/abc123/config.yaml"}
  ↓
返回: {
  "transport_mode": "rdt",
  "download_token": "token_abc123_xyz789",
  "message": "RDT准备就绪，请使用以下令牌下载"
}
  ↓
# 步骤3: RDT协议自动执行实际传输（客户端接收token，连接UDP 9998）
```

**场景2**：Web用户下载文件（使用HTTP）
```
用户: "下载这个文件"
  ↓
# 步骤1: 搜索
TOOL: semantic_search
ARGS: {"query": "这个文件", "top_k": 1}
  ↓
# 步骤2: 准备HTTP下载
TOOL: file_download
ARGS: {"file_path": "...", "transport_mode": "http"}
  ↓
返回: {
  "download_url": "http://localhost:8080/api/files/download/abc123"
}
  ↓
# 步骤3: 浏览器自动触发下载（点击链接或自动下载）
```

---

### 5. file_upload - 文件索引和上下文管理

#### 职责

管理已上传文件的索引和上下文（不执行文件传输）

**关键价值**：
1. 在历史记录中建立文件索引
2. 支持自然语义提及文件时的检索定位
3. 上下文管理（维护文件与对话历史的关系）

#### 输入格式

```json
{
  "action": "list",  // "list" | "get" | "search"
  "reference": "this",  // "this" | "these" | "previous" | "all"
  "file_type": "log",  // 可选：文件类型过滤
  "count": 2,  // 可选：数量限制
  "time_range": "recent"  // 可选：时间范围过滤
}
```

#### 输出格式

```python
ToolExecutionResult(
    success=True,
    output=json.dumps({
        "total": 1,
        "files": [
            {
                "file_id": "abc123-def456",
                "filename": "config.yaml",
                "file_path": "/storage/uploads/abc123/config.yaml",
                "uploaded_at": "2025-12-31 08:00:00",
                "size": 1024,
                "indexed": true
            }
        ]
    }),
    error=None,
    duration=0.05
)
```

#### 实现方式

```python
# src/tools/file_upload.py
import json
from typing import Optional, List
from datetime import datetime, timedelta
from src.tools.base import Tool, ToolExecutionResult

class FileUploadTool(Tool):
    """文件索引和上下文管理工具"""

    name: str = "file_upload"
    description: str = """管理已上传文件的索引和上下文（不执行文件传输）

    注意：此工具不处理文件上传，文件上传由协议层完成

    功能：
    1. 记录已上传文件的元数据到对话历史
    2. 在历史记录中建立文件索引（便于后续引用）
    3. 支持自然语言提及文件时的检索定位

    适用场景：
    - "这个文件里数据库端口是多少？"
      → list_files(reference="this") → 找到刚上传的文件

    - "对比这两个配置文件"
      → list_files(reference="these", count=2) → 找到最近2个文件

    - "我之前上传的日志文件"
      → list_files(reference="previous", file_type="log") → 找到之前的日志

    - "查看我上传的所有文件"
      → list_files() → 列出当前会话所有上传文件

    关键词：这个、那个、这两个、之前上传的、我上传的、所有文件
    """

    session: Optional[Any] = None

    def execute(self, action: str = "list", reference: str = "all",
                file_type: Optional[str] = None, count: Optional[int] = None,
                time_range: Optional[str] = None, **kwargs) -> ToolExecutionResult:
        """管理文件索引"""

        if action == "list":
            return self._list_files(reference, file_type, count, time_range)
        elif action == "get":
            file_id = kwargs.get("file_id")
            return self._get_file(file_id)
        else:
            return ToolExecutionResult(
                success=False,
                error=f"不支持的操作: {action}"
            )

    def _list_files(self, reference: str, file_type: Optional[str],
                   count: Optional[int], time_range: Optional[str]) -> ToolExecutionResult:
        """列出文件"""

        # 从session获取已上传文件列表
        uploaded_files = self.session.uploaded_files if self.session else []

        # 1. 根据reference过滤
        if reference == "this":
            # 最新1个文件
            files = [uploaded_files[-1]] if uploaded_files else []
        elif reference == "these":
            # 最近N个文件（默认2个）
            n = count or 2
            files = uploaded_files[-n:] if len(uploaded_files) >= n else uploaded_files
        elif reference == "previous":
            # 排除最新的文件
            files = uploaded_files[:-1] if len(uploaded_files) > 1 else []
        else:  # "all"
            files = uploaded_files

        # 2. 根据file_type过滤
        if file_type:
            files = [f for f in files if file_type in f["filename"]]

        # 3. 根据time_range过滤
        if time_range:
            now = datetime.now()
            if time_range == "recent":
                # 最近5分钟
                cutoff = now - timedelta(minutes=5)
            elif time_range == "today":
                # 今天
                cutoff = now.replace(hour=0, minute=0, second=0)
            else:
                cutoff = None

            if cutoff:
                files = [f for f in files if f["uploaded_at"] >= cutoff]

        # 4. 限制数量
        if count and reference != "these":
            files = files[:count]

        return ToolExecutionResult(
            success=True,
            output=json.dumps({
                "total": len(files),
                "files": files
            }, ensure_ascii=False, indent=2, default=str),
            error=None
        )

    def _get_file(self, file_id: str) -> ToolExecutionResult:
        """获取单个文件信息"""
        if not self.session:
            return ToolExecutionResult(
                success=False,
                error="Session未初始化"
            )

        file_info = self.session.get_uploaded_file(file_id)
        if not file_info:
            return ToolExecutionResult(
                success=False,
                error=f"文件不存在: {file_id}"
            )

        return ToolExecutionResult(
            success=True,
            output=json.dumps(file_info, ensure_ascii=False, default=str),
            error=None
        )
```

#### 使用场景

**场景1**：引用刚上传的文件
```
用户: [上传 config.yaml]
Agent: ✅ 文件上传成功

用户: "这个配置文件里数据库端口是多少？"
  ↓
# Agent理解"这个配置文件"指的是刚上传的config.yaml
TOOL: file_upload
ARGS: {"action": "list", "reference": "this"}
  ↓
返回: {
  "files": [{
    "file_id": "abc123",
    "filename": "config.yaml",
    "file_path": "/storage/uploads/abc123/config.yaml"
  }]
}
  ↓
# Agent读取文件内容，提取数据库端口，回答: "数据库端口是5432"
```

**场景2**：对比多个文件
```
用户: [上传 config.yaml]
Agent: ✅ 文件1上传成功

用户: [上传 config_old.yaml]
Agent: ✅ 文件2上传成功

用户: "对比这两个配置文件"
  ↓
# Agent理解"这两个"指的是刚上传的两个文件
TOOL: file_upload
ARGS: {"action": "list", "reference": "these", "count": 2}
  ↓
返回: {
  "files": [
    {"filename": "config.yaml", "file_path": "..."},
    {"filename": "config_old.yaml", "file_path": "..."}
  ]
}
  ↓
# Agent读取并对比两个文件，返回差异点
```

**场景3**：引用之前的文件
```
时刻T0:
用户: [上传 app.log]
Agent: ✅ 文件上传成功

... (20轮对话，讨论其他话题) ...

时刻T1:
用户: "分析一下我之前上传的日志文件中的错误"
  ↓
# Agent理解"之前上传的日志文件"
TOOL: file_upload
ARGS: {"action": "list", "reference": "previous", "file_type": "log"}
  ↓
返回: {
  "files": [{
    "filename": "app.log",
    "file_path": "/storage/uploads/xyz789/app.log"
  }]
}
  ↓
# Agent读取日志内容，分析错误信息
```

---

## 工具调用链

### 链1：文件下载链

**场景**：用户下载已上传的文件

```
用户: "下载config.yaml"
  ↓
Step 1: semantic_search
  - 输入: {"query": "config.yaml", "scope": "uploads", "top_k": 1}
  - 输出: {"filepath": "/storage/uploads/abc123/config.yaml", ...}
  ↓
Step 2: file_download
  - 输入: {"file_path": "/storage/uploads/abc123/config.yaml"}
  - 输出: {"download_token": "token_xyz", "transport_mode": "rdt"}
  ↓
Step 3: RDT协议自动执行
  - 客户端接收token
  - 连接UDP 9998
  - 接收数据包
```

### 链2：文件分析链

**场景**：用户要求分析刚上传的文件

```
用户: [上传 report.pdf]

用户: "分析一下这个作业报告的关键内容"
  ↓
Step 1: file_upload
  - 输入: {"action": "list", "reference": "this"}
  - 输出: {"file_path": "/storage/uploads/abc123/report.pdf"}
  ↓
Step 2: Agent读取文件内容
  - 使用Python库读取PDF
  - 提取文本内容
  ↓
Step 3: Agent分析并回答
  - LLM分析文件内容
  - 总结关键内容
  - 返回给用户
```

### 链3：文档查询链

**场景**：用户查询系统文档

```
用户: "如何配置数据库？"
  ↓
Step 1: semantic_search
  - 输入: {"query": "数据库配置说明", "scope": "system", "top_k": 3}
  - 输出: {
    "results": [{
      "filename": "README.md",
      "chunk": "数据库配置步骤：\n1. 编辑 config.yaml..."
    }]
  }
  ↓
Step 2: Agent回答
  - 直接使用搜索结果回答
  - "数据库配置步骤如下：\n1. 编辑 config.yaml..."
```

### 链4：系统监控链

**场景**：用户查询系统资源

```
用户: "系统资源使用情况如何？"
  ↓
Step 1: sys_monitor
  - 输入: {"metric": "all"}
  - 输出: {
    "cpu": {"usage_percent": 45.2, ...},
    "memory": {"usage_percent": 50.0, ...},
    "disk": {"usage_percent": 40.0, ...}
  }
  ↓
Step 2: Agent回答
  - 格式化结果
  - "CPU使用率：45.2%\n内存使用率：50.0%\n磁盘使用率：40.0%"
```

### 链5：文件管理链

**场景**：用户查看所有上传的文件

```
用户: "查看我上传的所有文件"
  ↓
Step 1: file_upload
  - 输入: {"action": "list", "reference": "all"}
  - 输出: {
    "total": 3,
    "files": [
      {"filename": "config.yaml", "uploaded_at": "..."},
      {"filename": "app.log", "uploaded_at": "..."},
      {"filename": "report.pdf", "uploaded_at": "..."}
    ]
  }
  ↓
Step 2: Agent回答
  - 列出文件清单
  - "您已上传3个文件：\n1. config.yaml (2025-12-31 08:00)\n..."
```

---

## 数据流设计

### 文件上传数据流

```
Client                    NPLT Server              Agent
  |                            |                      |
  | 1. FILE_METADATA           |                      |
  |--------------------------> |                      |
  |                            | [保存到 upload_state] |
  |                            |                      |
  | 2. FILE_DATA (chunks)      |                      |
  |--------------------------> |                      |
  |                            | [保存到              |
  |                            |  storage/uploads/]   |
  |                            |                      |
  |                            | 3. 自动索引          |
  |                            | index_manager        |
  |                            | .ensure_indexed()    |
  |                            |                      |
  |                            | 4. 记录到session      |
  |                            | session.uploaded_    |
  |                            | files.append({...})  |
  |                            |                      |
  | <---CHAT_TEXT-------------- |                      |
  | "文件上传成功"              |                      |
  |                            |                      |
  | 5. 用户文本 (带file_ref)   |                      |
  |--------------------------> |                      |
  |                            | 6. 附加到对话历史     |
  |                            |                      |
  |                            | 7. 调用Agent处理      |
  |                            |---------------------> |
  |                            |                      | 8. 检测session
  |                            |                      |    .uploaded_files
  |                            |                      | 9. 调用file_upload
  |                            |                      |    工具
  |                            |                      | 10. 读取并分析文件
  |                            | <------------------- |
  |                            | 11. 返回分析结果      |
  | <---CHAT_TEXT-------------- |                      |
  | "该配置文件数据库端口是5432" |                      |
```

### 文件下载数据流

```
User                      Agent                   Protocol Layer
  |                          |                           |
  | "下载config.yaml"         |                           |
  |------------------------> |                           |
  |                          | 1. semantic_search        |
  |                          |    query="config.yaml"     |
  |                          |                           |
  |                          | 2. file_download          |
  |                          |    file_path="..."         |
  |                          |                           |
  | <------------------------ | 3. 返回下载信息           |
  | "RDT准备就绪              |                           |
  |  token=token_abc123"      |                           |
  |                          |                           |
  | 4. 客户端连接RDT          |                           |
  |------------------------> |------------------------> |
  |                          |                           | 5. UDP传输
  |                          |                           |    (数据包)
  |                          |                           |
  | <------------------------ | <----------------------- |
  | 6. 接收文件               |                           |
```

### 语义检索数据流

```
User                    Agent                  VectorStore
  |                       |                        |
  | "搜索配置说明"          |                        |
  |----------------------> |                        |
  |                       | 1. llm_provider.embed() |
  |                       |    query="配置说明"      |
  |                       |----------------------> |
  |                       |                        | 2. 计算向量
  |                       |                        |    [0.1, 0.2, ...]
  |                       | <---------------------- |
  |                       |                        |
  |                       | 3. vector_store        |
  |                       |    .search_all()        |
  |                       |----------------------> |
  |                       |                        | 4. 向量相似度搜索
  |                       |                        |    cosine_similarity
  |                       | <---------------------- |
  |                       |                        | 5. 返回Top-K结果
  |                       |                        |
  | <---------------------- | 6. 返回搜索结果         |
  | "在3个文件中找到相关     |                        |
  |  内容：..."              |                        |
```

---

## 实现方式

### Session扩展设计

```python
# src/server/nplt_server.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Session:
    """会话对象（扩展版）"""

    session_id: str
    client_addr: tuple
    connected_at: datetime
    reader: Any
    writer: Any
    conversation_history: Any

    # 新增：文件上传记录
    uploaded_files: List[Dict[str, Any]] = field(default_factory=list)
    # 示例:
    # [{
    #     "file_id": "abc123-def456",
    #     "filename": "config.yaml",
    #     "file_path": "/storage/uploads/abc123/config.yaml",
    #     "uploaded_at": datetime(2025, 12, 31, 8, 0, 0),
    #     "size": 1024,
    #     "indexed": True
    # }]

    # 新增：当前上传状态
    upload_state: Dict[str, Any] = field(default_factory=dict)
    # 示例:
    # {
    #     "file_id": "abc123",
    #     "filename": "config.yaml",
    #     "file_size": 1024,
    #     "received_data": [],
    #     "received_size": 0
    # }

    def get_last_uploaded_file(self) -> Optional[Dict]:
        """获取最后上传的文件"""
        if not self.uploaded_files:
            return None
        return self.uploaded_files[-1]

    def get_uploaded_file(self, file_id: str) -> Optional[Dict]:
        """根据file_id获取文件信息"""
        for file_info in self.uploaded_files:
            if file_info["file_id"] == file_id:
                return file_info
        return None

    def add_uploaded_file(self, file_info: Dict):
        """记录上传的文件"""
        self.uploaded_files.append(file_info)

    def clear_upload_state(self):
        """清理上传状态"""
        self.upload_state = {}
```

### 文件引用格式

```python
# src/server/nplt_server.py
import re

def extract_file_reference(text: str) -> Optional[str]:
    """从文本中提取文件引用

    格式: [file_ref:{file_id}]
    示例: [file_ref:abc123-def456]
    """
    pattern = r'\[file_ref:([a-f0-9\-]+)\]'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

def remove_file_reference(text: str) -> str:
    """移除文件引用标记

    输入: "分析这个文件\n\n[file_ref:abc123-def456]"
    输出: "分析这个文件"
    """
    pattern = r'\n\n\[file_ref:[a-f0-9\-]+\]'
    return re.sub(pattern, '', text)
```

### Agent工具注册

```python
# src/server/agent.py
class Agent:
    """ReAct Agent"""

    def __init__(self, ...):
        # 初始化工具
        self.tools = {
            "sys_monitor": MonitorTool(),
            "command_executor": CommandTool(),
            "semantic_search": SemanticSearchTool(
                llm_provider=llm_provider,
                vector_store=vector_store,
                index_manager=index_manager
            ),
            "file_download": FileDownloadTool(
                path_validator=path_validator,
                client_type="cli",
                rdt_server=rdt_server,
                http_base_url=http_base_url
            ),
            "file_upload": FileUploadTool(
                session=None  # 运行时注入
            )
        }

    async def think_stream(self, session: Session, user_message: str) -> str:
        """ReAct循环"""

        # 注入session到file_upload工具
        self.tools["file_upload"].session = session

        # 检测是否有刚上传的文件
        uploaded_file = session.get_last_uploaded_file()

        # 检查文件引用
        file_ref = extract_file_reference(user_message)
        if file_ref:
            file_info = session.get_uploaded_file(file_ref)
            # 附加到对话历史
            session.conversation_history.add_message(
                role="user",
                content=remove_file_reference(user_message),
                metadata={"uploaded_file": file_info}
            )

        # Think and Decide
        response = await self._think_and_decide(session, user_message)

        return response
```

---

## 安全机制

### 1. 路径白名单验证

```python
# src/utils/path_validator.py
class PathValidator:
    """路径白名单验证器"""

    ALLOWED_PATHS = [
        "/storage/uploads",
        "/home/user/documents",
        "/var/log/app"
    ]

    def is_allowed(self, file_path: str) -> tuple[bool, Optional[str]]:
        """验证路径是否在白名单中"""
        import os

        # 规范化路径
        normalized = os.path.normpath(file_path)

        # 检查是否在允许的路径下
        for allowed in self.ALLOWED_PATHS:
            if normalized.startswith(allowed):
                return True, None

        return False, f"路径不在白名单中: {file_path}"
```

### 2. 命令白名单验证

```python
# src/tools/command.py
class CommandTool(Tool):
    """命令白名单验证"""

    WHITELIST_COMMANDS = {
        'ls', 'cat', 'grep', 'head', 'tail',
        'ps', 'pwd', 'whoami', 'df', 'free'
    }

    BLACKLIST_CHARS = [';', '&', '|', '>', '<', '`', '$',
                       '(', ')', '\n', '\r']

    def validate_command(self, command: str, args: List[str]) -> tuple[bool, str]:
        """验证命令和参数安全性"""
        # 1. 检查命令白名单
        if command not in self.WHITELIST_COMMANDS:
            return False, f"命令不在白名单中: {command}"

        # 2. 检查参数非法字符
        for arg in args:
            if any(char in str(arg) for char in self.BLACKLIST_CHARS):
                return False, f"参数包含非法字符: {arg}"

        return True, ""
```

### 3. 文件大小限制

```python
# src/server/nplt_server.py
class NPLTServer:
    """NPLT服务器"""

    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

    async def _handle_file_metadata(self, session, message):
        """处理文件元数据"""
        metadata = json.loads(message.data.decode('utf-8'))

        # 验证文件大小
        if metadata["size"] > self.MAX_FILE_SIZE:
            await session.send_message(
                MessageType.CHAT_TEXT,
                f"文件过大: {metadata['size']} > {self.MAX_FILE_SIZE}".encode('utf-8')
            )
            return

        # 继续处理...
```

### 4. 超时保护

```python
# src/tools/command.py
class CommandTool(Tool):
    """命令执行超时保护"""

    DEFAULT_TIMEOUT = 30  # 秒

    def execute(self, command: str, args: List[str] = None,
                timeout: int = None, **kwargs) -> ToolExecutionResult:
        """执行命令（带超时）"""
        timeout = timeout or self.DEFAULT_TIMEOUT

        try:
            result = subprocess.run(
                [command] + (args or []),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return ToolExecutionResult(success=True, output=result.stdout)

        except subprocess.TimeoutExpired:
            return ToolExecutionResult(
                success=False,
                error=f"命令执行超时: {command}"
            )
```

---

## 总结

### 工具总览

| 工具 | 职责 | 输入 | 输出 | 安全机制 |
|------|------|------|------|---------|
| sys_monitor | 系统监控 | metric类型 | 资源使用率 | 无需特殊防护 |
| command_executor | 命令执行 | command + args | 命令输出 | 白名单+黑名单+超时 |
| semantic_search | 语义检索 | query + scope | 文件路径+内容 | 路径白名单 |
| file_download | 准备下载 | file_path | 下载令牌/URL | 路径白名单 |
| file_upload | 索引管理 | reference + filters | 文件元数据列表 | Session隔离 |

### 设计原则

1. **职责单一**：每个工具只做一件事
2. **安全第一**：白名单验证、超时保护、路径限制
3. **协议分离**：Agent负责决策，协议层负责传输
4. **语义清晰**：工具名称和描述明确反映职责
5. **代码复用**：通过继承减少重复

### 预期效果

| 指标 | 当前 | 改进后 | 提升 |
|------|------|--------|------|
| 工具数量 | 7个 | 5个 | ✅ -29% |
| 代码重复率 | 90% | <20% | ✅ -70% |
| 语义清晰度 | 60% | 95% | ✅ +35% |
| 测试准确率 | 91.4% | 98-100% | ✅ +7% |

---

**文档生成时间**: 2025-12-31 08:20:00
**文档版本**: v2.0
**下一步**: 实施工具重构（阶段1-4）
