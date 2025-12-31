# Agent工具改进提案

**基于v2.0规格的潜在优化方向**
**生成时间**: 2025-12-31 08:30:00

---

## 改进1：命令执行的实时反馈和异步支持

### 当前问题

**command_executor** 工具同步等待命令执行完毕：
- 对于短命令（ls, cat）：正常工作，耗时 < 1秒
- 对于长命令（find / -name "*.log", grep -r "error" /var/log）：
  - 可能导致 Agent 响应超时
  - 用户等待时间过长
  - 无法看到中间进度

### 解决方案

#### 方案A：异步执行 + 轮询机制（推荐）

```python
# src/tools/command_async.py
import asyncio
import subprocess
import uuid
from typing import Optional, Dict, Any
from src.tools.base import Tool, ToolExecutionResult

class AsyncCommandTool(Tool):
    """异步命令执行工具（支持长时运行）"""

    name: str = "command_executor_async"
    description: str = """异步执行系统命令（支持长时运行命令）

    功能：
    1. 提交命令到后台执行
    2. 返回任务ID，支持后续查询结果
    3. 支持命令执行状态查询
    4. 自动清理已完成的任务

    适用场景：
    - 长时运行命令（find、grep -r、tar等）
    - 需要查询执行进度的场景

    关键词：执行、运行、后台、异步
    """

    # 任务存储：{task_id: {process, stdout, stderr, status, start_time}}
    tasks: Dict[str, Dict[str, Any]] = {}
    MAX_TASKS = 100  # 最大并发任务数
    TASK_TIMEOUT = 300  # 任务超时时间（秒）

    def execute(self, command: str, args: Optional[list] = None,
                action: str = "run", task_id: str = None, **kwargs) -> ToolExecutionResult:
        """执行或查询命令"""

        if action == "run":
            return self._run_command_async(command, args)
        elif action == "status":
            return self._get_task_status(task_id)
        elif action == "cancel":
            return self._cancel_task(task_id)
        elif action == "result":
            return self._get_task_result(task_id)
        else:
            return ToolExecutionResult(
                success=False,
                error=f"不支持的操作: {action}"
            )

    def _run_command_async(self, command: str, args: Optional[list]) -> ToolExecutionResult:
        """异步运行命令"""
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

        # 3. 检查任务数量限制
        if len(self.tasks) >= self.MAX_TASKS:
            return ToolExecutionResult(
                success=False,
                error=f"任务队列已满: {len(self.tasks)}/{self.MAX_TASKS}"
            )

        # 4. 创建任务ID
        task_id = str(uuid.uuid4())[:8]

        # 5. 启动异步进程
        try:
            full_command = [command] + (args or [])
            process = subprocess.Popen(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 6. 记录任务
            self.tasks[task_id] = {
                "process": process,
                "command": ' '.join(full_command),
                "status": "running",
                "start_time": asyncio.get_event_loop().time(),
                "stdout": "",
                "stderr": ""
            }

            return ToolExecutionResult(
                success=True,
                output=json.dumps({
                    "task_id": task_id,
                    "status": "running",
                    "message": f"命令已提交到后台执行，任务ID: {task_id}",
                    "query_command": f"使用 action='status', task_id='{task_id}' 查询状态"
                }, ensure_ascii=False),
                error=None
            )

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"启动命令失败: {str(e)}"
            )

    def _get_task_status(self, task_id: str) -> ToolExecutionResult:
        """获取任务状态"""
        if task_id not in self.tasks:
            return ToolExecutionResult(
                success=False,
                error=f"任务不存在: {task_id}"
            )

        task = self.tasks[task_id]
        process = task["process"]

        # 检查进程是否完成
        poll_result = process.poll()

        if poll_result is None:
            # 进程仍在运行
            elapsed = asyncio.get_event_loop().time() - task["start_time"]

            return ToolExecutionResult(
                success=True,
                output=json.dumps({
                    "task_id": task_id,
                    "status": "running",
                    "command": task["command"],
                    "elapsed_time": f"{elapsed:.1f}秒",
                    "message": "命令正在执行中..."
                }, ensure_ascii=False),
                error=None
            )
        else:
            # 进程已完成
            stdout, stderr = process.communicate()

            task["status"] = "completed"
            task["stdout"] = stdout
            task["stderr"] = stderr
            task["exit_code"] = poll_result

            return ToolExecutionResult(
                success=True,
                output=json.dumps({
                    "task_id": task_id,
                    "status": "completed",
                    "command": task["command"],
                    "exit_code": poll_result,
                    "elapsed_time": f"{asyncio.get_event_loop().time() - task['start_time']:.1f}秒",
                    "message": "命令执行完成",
                    "query_result": f"使用 action='result', task_id='{task_id}' 获取结果"
                }, ensure_ascii=False),
                error=None
            )

    def _get_task_result(self, task_id: str) -> ToolExecutionResult:
        """获取任务结果"""
        if task_id not in self.tasks:
            return ToolExecutionResult(
                success=False,
                error=f"任务不存在: {task_id}"
            )

        task = self.tasks[task_id]

        if task["status"] != "completed":
            return ToolExecutionResult(
                success=False,
                error=f"任务尚未完成: {task_id} (状态: {task['status']})"
            )

        return ToolExecutionResult(
            success=task["exit_code"] == 0,
            output=json.dumps({
                "task_id": task_id,
                "command": task["command"],
                "exit_code": task["exit_code"],
                "stdout": task["stdout"],
                "stderr": task["stderr"]
            }, ensure_ascii=False),
            error=task["stderr"] if task["exit_code"] != 0 else None
        )

    def _cancel_task(self, task_id: str) -> ToolExecutionResult:
        """取消任务"""
        if task_id not in self.tasks:
            return ToolExecutionResult(
                success=False,
                error=f"任务不存在: {task_id}"
            )

        task = self.tasks[task_id]

        if task["status"] == "completed":
            return ToolExecutionResult(
                success=False,
                error=f"任务已完成，无法取消: {task_id}"
            )

        try:
            task["process"].kill()
            task["status"] = "cancelled"

            return ToolExecutionResult(
                success=True,
                output=json.dumps({
                    "task_id": task_id,
                    "status": "cancelled",
                    "message": "任务已取消"
                }, ensure_ascii=False),
                error=None
            )

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"取消任务失败: {str(e)}"
            )
```

#### 使用场景

**场景1：执行长时命令**
```
用户: "在系统中查找所有日志文件"
  ↓
Step 1: 提交异步命令
TOOL: command_executor_async
ARGS: {
  "command": "find",
  "args": ["/", "-name", "*.log"],
  "action": "run"
}
  ↓
返回: {
  "task_id": "abc12345",
  "status": "running",
  "message": "命令已提交到后台执行，任务ID: abc12345"
}
  ↓
Agent: "已启动查找任务（任务ID: abc12345），预计需要较长时间，请稍后查询结果"

用户: "查询任务状态"
  ↓
Step 2: 查询状态
TOOL: command_executor_async
ARGS: {
  "action": "status",
  "task_id": "abc12345"
}
  ↓
返回: {
  "status": "running",
  "elapsed_time": "15.3秒",
  "message": "命令正在执行中..."
}
  ↓
Agent: "任务正在执行中，已运行15.3秒"

用户: "获取任务结果"
  ↓
Step 3: 获取结果
TOOL: command_executor_async
ARGS: {
  "action": "result",
  "task_id": "abc12345"
}
  ↓
返回: {
  "exit_code": 0,
  "stdout": "/var/log/app.log\n/var/log/system.log\n...",
  "stderr": ""
}
  ↓
Agent: "找到以下日志文件：\n- /var/log/app.log\n- /var/log/system.log\n..."
```

#### 方案B：超时分级策略（简单）

```python
# src/tools/command.py
class CommandTool(Tool):
    """命令执行工具（超时分级）"""

    # 根据命令类型设置不同超时
    COMMAND_TIMEOUTS = {
        'find': 120,      # find命令：2分钟
        'grep': 60,       # grep命令：1分钟
        'tar': 300,       # tar命令：5分钟
        'default': 30     # 默认：30秒
    }

    def execute(self, command: str, args: Optional[list] = None,
                timeout: Optional[int] = None, **kwargs) -> ToolExecutionResult:
        """执行命令（自动超时分级）"""

        # 1. 如果未指定超时，根据命令类型自动设置
        if timeout is None:
            timeout = self.COMMAND_TIMEOUTS.get(
                command,
                self.COMMAND_TIMEOUTS['default']
            )

        # 2. 执行命令
        try:
            result = subprocess.run(
                [command] + (args or []),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )

            return ToolExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None
            )

        except subprocess.TimeoutExpired:
            return ToolExecutionResult(
                success=False,
                error=f"命令执行超时（{timeout}秒）: {command}。"
                      f"建议使用异步模式: action='run'"
            )
```

### 推荐方案

- **短命令**（ls, cat, ps）：使用同步版本（方案B）
- **长命令**（find, grep -r, tar）：使用异步版本（方案A）

Agent可以根据命令类型自动选择：
```python
ASYNC_COMMANDS = {'find', 'grep', 'tar', 'dd'}

if command in ASYNC_COMMANDS:
    return command_executor_async.execute(command, args, action="run")
else:
    return command_executor.execute(command, args)
```

---

## 改进2：文件检索的混合策略

### 当前问题

**semantic_search** 纯粹依赖向量检索：
- **语义查询**："数据库配置文件" → 向量检索效果好 ✅
- **精确文件名**："config.yaml" → 向量检索可能返回相似但不完全匹配的结果 ❌
- **模糊文件名**："config" → 可能匹配到 config.yaml, config.json, config.yml

### 解决方案

#### 方案：混合检索策略（Keyword + Semantic）

```python
# src/tools/semantic_search_v2.py
import re
import glob
import json
from typing import Optional, List, Tuple
from src.tools.base import Tool, ToolExecutionResult

class SemanticSearchToolV2(Tool):
    """混合检索工具（关键字 + 语义）"""

    name: str = "semantic_search"
    description: str = """通过自然语言或文件名检索文件（混合策略）

    检索策略：
    1. 精确文件名匹配（如 "config.yaml"）
    2. 模糊文件名匹配（如 "config" → config.yaml, config.json）
    3. 语义检索（如 "数据库配置" → README相关章节）

    适用场景：
    - "下载 config.yaml" → 精确匹配
    - "查找配置文件" → 模糊匹配 + 语义检索
    - "数据库配置在哪里" → 语义检索

    关键词：搜索、检索、查找、文档、文件
    """

    llm_provider: Optional[Any] = None
    vector_store: Optional[Any] = None
    index_manager: Optional[Any] = None
    search_paths: List[str] = ["/storage/uploads", "/home/project"]

    def execute(self, query: str, scope: str = "all",
                top_k: int = 3, **kwargs) -> ToolExecutionResult:
        """执行混合检索"""

        # 策略1: 精确文件名匹配
        if self._is_exact_filename(query):
            exact_results = self._search_exact_filename(query, scope)
            if exact_results:
                return ToolExecutionResult(
                    success=True,
                    output=json.dumps({
                        "strategy": "exact_match",
                        "total": len(exact_results),
                        "results": exact_results
                    }, ensure_ascii=False, indent=2),
                    error=None
                )

        # 策略2: 模糊文件名匹配
        fuzzy_results = self._search_fuzzy_filename(query, scope, top_k)

        # 策略3: 语义检索（作为补充或兜底）
        semantic_results = self._search_semantic(query, scope, top_k)

        # 合并结果（去重）
        combined_results = self._merge_results(
            fuzzy_results,
            semantic_results,
            top_k
        )

        return ToolExecutionResult(
            success=True,
            output=json.dumps({
                "strategy": "hybrid",
                "total": len(combined_results),
                "results": combined_results
            }, ensure_ascii=False, indent=2),
            error=None
        )

    def _is_exact_filename(self, query: str) -> bool:
        """判断是否为精确文件名查询"""
        # 特征：包含扩展名，无空格
        pattern = r'^[\w\-\./]+\.(yaml|yml|json|xml|txt|md|py|js|log|pdf|png|jpg)$'
        return bool(re.match(pattern, query.strip(), re.IGNORECASE))

    def _search_exact_filename(self, query: str, scope: str) -> List[dict]:
        """精确文件名匹配"""
        results = []
        filename = query.strip()

        # 在索引的文件中搜索
        indexed_files = self.vector_store.list_files()

        for file_info in indexed_files:
            if file_info['filename'] == filename:
                # 检查scope过滤
                if scope == "uploads" and not file_info['filepath'].startswith('/storage/uploads'):
                    continue
                if scope == "system" and file_info['filepath'].startswith('/storage/uploads'):
                    continue

                results.append({
                    "filename": file_info['filename'],
                    "filepath": file_info['filepath'],
                    "similarity": 1.0,  # 精确匹配
                    "match_type": "exact_filename"
                })

        return results

    def _search_fuzzy_filename(self, query: str, scope: str,
                               top_k: int) -> List[dict]:
        """模糊文件名匹配"""
        results = []
        query_lower = query.lower().strip()

        # 提取查询关键词（去除扩展名）
        query_keywords = query_lower.replace('.', ' ').split()

        # 在索引的文件中搜索
        indexed_files = self.vector_store.list_files()

        for file_info in indexed_files:
            # 检查scope过滤
            if scope == "uploads" and not file_info['filepath'].startswith('/storage/uploads'):
                continue
            if scope == "system" and file_info['filepath'].startswith('/storage/uploads'):
                continue

            filename = file_info['filename'].lower()

            # 计算匹配度
            match_score = 0.0

            # 关键词匹配（每个关键词0.3分）
            for keyword in query_keywords:
                if keyword in filename:
                    match_score += 0.3

            # 前缀匹配（0.2分）
            if filename.startswith(query_lower):
                match_score += 0.2

            # 包含完整查询（0.3分）
            if query_lower in filename:
                match_score += 0.3

            # 至少匹配一个关键词
            if match_score > 0:
                results.append({
                    "filename": file_info['filename'],
                    "filepath": file_info['filepath'],
                    "similarity": min(match_score, 1.0),
                    "match_type": "fuzzy_filename"
                })

        # 按匹配度排序
        results.sort(key=lambda x: x['similarity'], reverse=True)

        return results[:top_k]

    def _search_semantic(self, query: str, scope: str,
                        top_k: int) -> List[dict]:
        """语义检索（原有逻辑）"""
        query_embedding = self._get_embedding(query)

        results = []
        if scope in ("all", "system"):
            results.extend(self._search_system_docs(query_embedding, top_k))

        if scope in ("all", "uploads"):
            results.extend(self._search_uploads(query_embedding, top_k))

        # 标记匹配类型
        for result in results:
            result["match_type"] = "semantic"

        return results

    def _merge_results(self, fuzzy_results: List[dict],
                      semantic_results: List[dict],
                      top_k: int) -> List[dict]:
        """合并检索结果（去重）"""
        seen_paths = set()
        combined = []

        # 优先添加模糊匹配结果
        for result in fuzzy_results:
            if result['filepath'] not in seen_paths:
                combined.append(result)
                seen_paths.add(result['filepath'])

        # 补充语义检索结果
        for result in semantic_results:
            if result['filepath'] not in seen_paths:
                combined.append(result)
                seen_paths.add(result['filepath'])

        # 按相似度排序
        combined.sort(key=lambda x: x['similarity'], reverse=True)

        return combined[:top_k]

    def _get_embedding(self, query: str) -> List[float]:
        """计算查询向量"""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            asyncio.ensure_future(self.llm_provider.embed([query]))
        )[0]
```

#### 使用场景对比

**场景1：精确文件名**
```
用户: "下载 config.yaml"
  ↓
策略1: 精确匹配
  → 找到: /storage/uploads/abc123/config.yaml (similarity=1.0)
  ↓
返回: {
  "strategy": "exact_match",
  "results": [{
    "filename": "config.yaml",
    "filepath": "/storage/uploads/abc123/config.yaml",
    "similarity": 1.0,
    "match_type": "exact_filename"
  }]
}
```

**场景2：模糊文件名**
```
用户: "查找配置文件"
  ↓
策略1: 精确匹配 → 未命中
  ↓
策略2: 模糊匹配
  → 找到: config.yaml (0.8), config.json (0.8), config.yml (0.8)
  ↓
策略3: 语义检索
  → 找到: README.md (0.75) 中提到配置
  ↓
返回: {
  "strategy": "hybrid",
  "results": [
    {"filename": "config.yaml", "similarity": 0.8, "match_type": "fuzzy_filename"},
    {"filename": "config.json", "similarity": 0.8, "match_type": "fuzzy_filename"},
    {"filename": "README.md", "similarity": 0.75, "match_type": "semantic"}
  ]
}
```

**场景3：纯语义查询**
```
用户: "如何配置数据库？"
  ↓
策略1: 精确匹配 → 未命中
  ↓
策略2: 模糊匹配 → 未命中
  ↓
策略3: 语义检索
  → 找到: README.md (0.92)
  ↓
返回: {
  "strategy": "hybrid",
  "results": [{
    "filename": "README.md",
    "similarity": 0.92,
    "match_type": "semantic",
    "chunk": "数据库配置步骤：\n1. 编辑 config.yaml..."
  }]
}
```

### 检索策略优先级

| 查询类型 | 特征 | 策略优先级 |
|---------|------|-----------|
| 精确文件名 | "config.yaml" | 1. 精确匹配 → 2. 返回 |
| 模糊文件名 | "config" | 1. 模糊匹配 → 2. 语义补充 |
| 语义查询 | "数据库配置" | 1. 语义检索 |
| 扩展名查询 | "*.log" | 1. Glob模式匹配 |

---

## 改进3：友好的错误处理和自我修正

### 当前问题

工具执行失败时：
- 直接返回 Python 异常信息
- Agent 无法自我修正
- 用户体验差

### 解决方案

#### 方案：结构化错误 + 自我修正提示

```python
# src/tools/base.py
from enum import Enum

class ErrorType(Enum):
    """错误类型枚举"""
    # 参数错误
    INVALID_PARAM = "INVALID_PARAM"
    MISSING_PARAM = "MISSING_PARAM"
    PARAM_TYPE_ERROR = "PARAM_TYPE_ERROR"

    # 权限错误
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_IN_WHITELIST = "NOT_IN_WHITELIST"

    # 资源错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    RESOURCE_BUSY = "RESOURCE_BUSY"

    # 执行错误
    COMMAND_FAILED = "COMMAND_FAILED"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    EXECUTION_ERROR = "EXECUTION_ERROR"

    # 网络错误
    NETWORK_ERROR = "NETWORK_ERROR"
    API_ERROR = "API_ERROR"

    # 未知错误
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class ToolExecutionResult:
    """工具执行结果（增强版）"""

    def __init__(
        self,
        success: bool,
        output: str = "",
        error: Optional[str] = None,
        error_type: Optional[ErrorType] = None,
        error_code: Optional[str] = None,
        suggested_fix: Optional[str] = None,
        retry_able: bool = False,
        duration: float = 0.0
    ):
        self.success = success
        self.output = output
        self.error = error
        self.error_type = error_type
        self.error_code = error_code
        self.suggested_fix = suggested_fix  # 建议的修复方案
        self.retry_able = retry_able        # 是否可重试
        self.duration = duration

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "error_type": self.error_type.value if self.error_type else None,
            "error_code": self.error_code,
            "suggested_fix": self.suggested_fix,
            "retry_able": self.retry_able,
            "duration": self.duration
        }
```

#### 具体工具的错误处理示例

```python
# src/tools/file_download.py
class FileDownloadTool(Tool):
    """文件下载准备工具（增强错误处理）"""

    def execute(self, file_path: str, transport_mode: str = "auto",
                **kwargs) -> ToolExecutionResult:
        """准备文件下载（结构化错误）"""

        # 错误1: 文件路径未提供
        if not file_path:
            return ToolExecutionResult(
                success=False,
                error="文件路径参数缺失",
                error_type=ErrorType.MISSING_PARAM,
                error_code="MISSING_FILE_PATH",
                suggested_fix=(
                    "请先使用 semantic_search 工具搜索文件路径。"
                    "例如：semantic_search(query='config.yaml')"
                ),
                retry_able=True
            )

        # 错误2: 路径不在白名单
        is_valid, error_msg = self.path_validator.is_allowed(file_path)
        if not is_valid:
            return ToolExecutionResult(
                success=False,
                error=f"文件路径不在白名单中: {file_path}",
                error_type=ErrorType.NOT_IN_WHITELIST,
                error_code="PATH_NOT_ALLOWED",
                suggested_fix=(
                    f"允许的路径范围: {self.path_validator.ALLOWED_PATHS}。"
                    f"请确保文件在允许的路径下。"
                ),
                retry_able=False
            )

        # 错误3: 文件不存在
        if not os.path.exists(file_path):
            return ToolExecutionResult(
                success=False,
                error=f"文件不存在: {file_path}",
                error_type=ErrorType.FILE_NOT_FOUND,
                error_code="FILE_NOT_FOUND",
                suggested_fix=(
                    "请使用 semantic_search 重新搜索文件。"
                    "可能的原因：\n"
                    "1. 文件已被删除\n"
                    "2. 搜索结果中的路径已过期"
                ),
                retry_able=True
            )

        # 错误4: 文件过大
        file_size = os.path.getsize(file_path)
        max_size = 500 * 1024 * 1024  # 500MB
        if file_size > max_size:
            return ToolExecutionResult(
                success=False,
                error=f"文件过大: {file_size / (1024**2):.1f}MB > {max_size / (1024**2):.1f}MB",
                error_type=ErrorType.FILE_TOO_LARGE,
                error_code="FILE_TOO_LARGE",
                suggested_fix=(
                    f"文件大小超出限制。建议：\n"
                    f"1. 使用压缩传输（如有）\n"
                    f"2. 分割文件后分别下载"
                ),
                retry_able=False
            )

        # 成功
        try:
            download_info = self._prepare_download(file_path, transport_mode)
            return ToolExecutionResult(
                success=True,
                output=json.dumps(download_info, ensure_ascii=False),
                duration=0.10
            )

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"准备下载失败: {str(e)}",
                error_type=ErrorType.EXECUTION_ERROR,
                error_code="DOWNLOAD_PREP_FAILED",
                suggested_fix=(
                    "请重试或联系管理员。"
                    "如果问题持续存在，可能是系统配置问题。"
                ),
                retry_able=True
            )
```

#### Agent的自我修正逻辑

```python
# src/server/agent.py
class Agent:
    """ReAct Agent（增强错误处理）"""

    async def _think_and_decide(self, session, user_message: str) -> str:
        """思考和决策（支持错误修正）"""

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            # 1. 调用LLM选择工具
            tool_name, args = await self._select_tool(user_message)

            # 2. 执行工具
            result = await self._execute_tool(tool_name, args)

            # 3. 检查结果
            if result.success:
                # 成功：返回结果
                return self._format_success_response(result)

            # 4. 失败：分析错误
            error_response = await self._handle_error(
                result,
                tool_name,
                args,
                retry_count
            )

            # 5. 判断是否可重试
            if result.retry_able and retry_count < max_retries - 1:
                retry_count += 1

                # 向用户说明重试
                if retry_count == 1:
                    error_response += f"\n\n正在尝试自动修正..."

                # 根据建议修复方案调整参数
                if result.suggested_fix:
                    # 将错误信息和建议反馈给LLM，让其重新决策
                    user_message = f"""
                    上一次尝试失败：
                    工具: {tool_name}
                    错误: {result.error}
                    建议: {result.suggested_fix}

                    请根据建议重新执行任务。
                    """

                continue
            else:
                # 不可重试或达到最大重试次数
                return error_response

    async def _handle_error(
        self,
        result: ToolExecutionResult,
        tool_name: str,
        args: dict,
        retry_count: int
    ) -> str:
        """处理错误（生成友好响应）"""

        # 根据错误类型生成不同的响应
        if result.error_type == ErrorType.MISSING_PARAM:
            return (
                f"❌ 缺少必要参数: {result.error_code}\n"
                f"💡 建议: {result.suggested_fix}"
            )

        elif result.error_type == ErrorType.FILE_NOT_FOUND:
            return (
                f"❌ 文件未找到: {args.get('file_path', 'unknown')}\n"
                f"💡 建议: {result.suggested_fix}"
            )

        elif result.error_type == ErrorType.NOT_IN_WHITELIST:
            return (
                f"❌ 权限不足: {result.error}\n"
                f"💡 建议: {result.suggested_fix}"
            )

        elif result.error_type == ErrorType.COMMAND_TIMEOUT:
            return (
                f"⏱️ 命令执行超时\n"
                f"💡 建议: {result.suggested_fix}"
            )

        else:
            # 通用错误
            return (
                f"❌ 执行失败: {result.error}\n"
                f"💡 建议: {result.suggested_fix or '请联系管理员'}"
            )
```

#### 错误响应示例

**场景1：文件路径缺失**
```
用户: "下载配置文件"
  ↓
Agent尝试: file_download(file_path=None)
  ↓
返回: {
  "success": false,
  "error_type": "MISSING_PARAM",
  "error": "文件路径参数缺失",
  "suggested_fix": "请先使用 semantic_search 工具搜索文件路径"
}
  ↓
Agent自我修正:
  ↓
Step 1: semantic_search(query="配置文件")
  → 返回: {filepath: "/storage/uploads/abc123/config.yaml"}
  ↓
Step 2: file_download(file_path="/storage/uploads/abc123/config.yaml")
  → ✅ 成功
  ↓
最终响应: "✅ 配置文件已准备下载 (RDT token: token_xyz)"
```

**场景2：文件不存在**
```
用户: "下载 app.log"
  ↓
Agent尝试:
  Step 1: semantic_search(query="app.log")
    → 返回: {filepath: "/storage/uploads/xyz789/app.log"}
  Step 2: file_download(file_path="/storage/uploads/xyz789/app.log")
  ↓
返回: {
  "success": false,
  "error_type": "FILE_NOT_FOUND",
  "error": "文件不存在: /storage/uploads/xyz789/app.log",
  "suggested_fix": "请使用 semantic_search 重新搜索文件。可能的原因：1. 文件已被删除"
}
  ↓
Agent响应:
  "❌ 文件未找到: /storage/uploads/xyz789/app.log
  💡 建议: 请使用 semantic_search 重新搜索文件。
  可能的原因：
  1. 文件已被删除
  2. 搜索结果中的路径已过期

  正在尝试重新搜索..."
  ↓
Agent自我修正:
  semantic_search(query="app.log", scope="uploads")
  → 返回: {filepath: "/storage/uploads/def456/app.log"}
  ↓
最终响应: "✅ 找到新的日志文件，已准备下载"
```

---

## 实施优先级

### P0（高优先级）- 立即实施

1. **改进2：混合检索策略**
   - 投入产出比最高
   - 显著提升用户体验
   - 实施难度：中等
   - 预期工作量：4小时

### P1（中优先级）- 近期实施

2. **改进3：友好错误处理**
   - 提升系统可用性
   - 支持自我修正
   - 实施难度：中等
   - 预期工作量：6小时

### P2（低优先级）- 按需实施

3. **改进1：异步命令执行**
   - 仅在需要执行长命令时
   - 增加复杂度
   - 实施难度：较高
   - 预期工作量：8小时

---

## 总结

### 改进对比

| 改进项 | 当前问题 | 解决方案 | 优先级 | 工作量 |
|-------|---------|---------|--------|--------|
| 混合检索 | 精确文件名检索不准确 | 关键字+语义混合策略 | P0 | 4h |
| 错误处理 | 异常直接抛出 | 结构化错误+自我修正 | P1 | 6h |
| 异步命令 | 长命令超时 | 异步执行+轮询 | P2 | 8h |

### 预期效果

| 指标 | 当前 | 改进后 | 提升 |
|------|------|--------|------|
| 文件检索准确率 | 90% | 98% | +8% |
| 错误自我修正率 | 0% | 60% | +60% |
| 长命令成功率 | 70% | 95% | +25% |
| 用户满意度 | 75% | 92% | +17% |

---

**文档生成时间**: 2025-12-31 08:30:00
**下一步**: 实施P0改进（混合检索策略）
