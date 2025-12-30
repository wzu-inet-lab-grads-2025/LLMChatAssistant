# 快速开始指南: 文件操作工具集成到 Agent

**功能**: 003-file-tools-integration
**创建时间**: 2025-12-30

## 概述

本指南将帮助您快速开始使用文件操作工具功能。包括环境准备、基本用法、测试方法和故障排除。

---

## 前置条件

### 1. 环境要求

- **Python**: 3.11
- **包管理器**: uv
- **API Key**: 智谱 API Key（用于向量索引和语义检索）
- **磁盘空间**: 至少 1GB 可用空间

### 2. 配置验证

确保以下配置已正确设置：

```yaml
# config.yaml
file_access:
  allowed_paths:
    - "/home/zhoutianyu/tmp/LLMChatAssistant/**"
    - "/tmp/**"
  forbidden_patterns:
    - "*/.env"
    - "*/.ssh/*"
    - "/etc/passwd"
    - "/etc/shadow"
  auto_index: true
  max_output_size: 102400  # 100KB

zhipu:
  api_key: "${ZHIPU_API_KEY}"
  model: "glm-4-flash"
```

### 3. 环境变量

```bash
# 设置智谱 API Key
export ZHIPU_API_KEY="your_api_key_here"

# 验证
echo $ZHIPU_API_KEY
```

---

## 安装与设置

### 1. 安装依赖

```bash
# 使用 uv 安装依赖（如果尚未安装）
uv sync

# 激活虚拟环境
source .venv/bin/activate
```

### 2. 验证安装

```bash
# 验证 Python 版本
python --version
# 输出: Python 3.11.x

# 验证依赖
python -m pip list | grep zai
# 输出应包含: zai-sdk

# 验证智谱 API Key
python -c "import os; print('API Key 已设置' if os.getenv('ZHIPU_API_KEY') else 'API Key 未设置')"
```

### 3. 创建必要目录

```bash
# 创建存储目录
mkdir -p storage/uploads
mkdir -p storage/vectors
mkdir -p logs

# 验证目录权限
ls -la storage/
```

---

## 基本用法

### 1. 文件上传

**场景**: 用户上传配置文件供 Agent 分析

**用户输入**:
```
我有一个配置文件 config.yaml，内容如下：
server:
  port: 8080
  host: localhost

帮我上传这个文件。
```

**Agent 响应**:
```
好的，我已接收您的文件。

文件信息：
- 文件名: config.yaml
- 大小: 45 字节
- 存储路径: storage/uploads/550e8400-e29b-41d4-a716-446655440000/config.yaml
- 索引状态: 已建立索引

文件已成功上传并建立向量索引，现在可以进行语义检索。
```

**工具调用**:
```python
file_upload_tool.execute(
    filename="config.yaml",
    content="server:\n  port: 8080\n  host: localhost",
    content_type="application/yaml"
)
```

---

### 2. 文件下载

**场景**: 用户请求获取服务器上的配置文件

**用户输入**:
```
把配置文件发给我。
```

**Agent 响应**:
```
我找到了配置文件，现在发送给您。

文件信息：
- 文件名: config.yaml
- 大小: 45 字节

已向您发送下载提议，请在客户端确认接收。
```

**工具调用**:
```python
file_download_tool.execute(
    file_path="storage/uploads/550e8400/config.yaml"
)
```

---

### 3. 语义检索

**场景**: 用户用自然语言搜索文档

**用户输入**:
```
搜索关于数据库配置的文档。
```

**Agent 响应**:
```
在 5 个已索引文件中找到 2 个相关结果：

1. [database_config.yaml] (相似度: 0.92)
   位置: chunk 1
   路径: /home/config/database.yaml
   内容: database:\n  host: localhost\n  port: 5432\n  ...

2. [README.md] (相似度: 0.78)
   位置: chunk 3
   路径: /home/README.md
   内容: ## 数据库配置\n使用 PostgreSQL 数据库...
```

**工具调用**:
```python
file_search_tool.execute(
    query="数据库配置",
    top_k=3
)
```

---

### 4. 串行工具调用

**场景**: 用户请求搜索并下载文件

**用户输入**:
```
把性能分析报告发给我。
```

**Agent 执行流程**:

**第1轮 - 搜索文件**:
```
Agent 思考: 用户提到"性能分析报告"，需要先搜索文件。
工具调用: file_semantic_search(query="性能分析报告", top_k=3)
结果: 找到文件 /docs/perf_report.pdf
```

**第2轮 - 下载文件**:
```
Agent 思考: 找到了文件，现在发送给用户。
工具调用: file_download(file_path="/docs/perf_report.pdf")
结果: 已发送下载提议
```

**最终响应**:
```
我找到了性能分析报告，现在发送给您。

文件信息：
- 文件名: perf_report.pdf
- 大小: 1.2 MB
- 相似度: 0.89

已向您发送下载提议，请在客户端确认接收。
```

---

## 测试

### 1. 运行单元测试

```bash
# 测试文件上传工具
python -m pytest tests/unit/tools/test_file_upload.py -v

# 测试文件下载工具
python -m pytest tests/unit/tools/test_file_download.py -v

# 测试语义检索工具
python -m pytest tests/unit/tools/test_file_search.py -v
```

### 2. 运行集成测试

```bash
# 测试完整的文件操作流程
python -m pytest tests/integration/test_file_tools_integration.py -v

# 测试串行工具调用
python -m pytest tests/integration/test_file_tools_integration.py::test_search_and_download -v
```

### 3. 手动测试

**测试文件上传**:

```python
# 创建测试脚本 test_manual_upload.py
from src.tools.file_upload import FileUploadTool

tool = FileUploadTool()
result = tool.execute(
    filename="test.txt",
    content="这是一个测试文件。",
    content_type="text/plain"
)

print(f"成功: {result.success}")
print(f"输出: {result.output}")
```

运行：
```bash
python test_manual_upload.py
```

**测试语义检索**:

```python
# 创建测试脚本 test_manual_search.py
from src.tools.file_search import FileSemanticSearchTool

tool = FileSemanticSearchTool(...)
result = tool.execute(
    query="配置文件",
    top_k=3
)

print(f"成功: {result.success}")
print(f"结果: {result.output}")
```

运行：
```bash
python test_manual_search.py
```

---

## 故障排除

### 1. 文件上传失败

**问题**: 文件上传失败，提示"文件大小超过限制"

**解决方案**:
```python
# 检查文件大小
import os
file_size = os.path.getsize("your_file.txt")
print(f"文件大小: {file_size} 字节")

# 如果超过 10MB，压缩或分割文件
if file_size > 10 * 1024 * 1024:
    print("文件过大，请压缩或分割文件")
```

---

### 2. 语义检索无结果

**问题**: 搜索返回"当前没有已索引的文件"

**解决方案**:
```bash
# 检查索引目录
ls -la storage/vectors/

# 如果为空，手动触发索引
python -c "
from src.storage.index_manager import IndexManager
from src.utils.path_validator import get_path_validator
from src.utils.config import get_config

config = get_config()
validator = get_path_validator(config.file_access)
manager = IndexManager(...)

# 索引文件
manager.ensure_indexed('path/to/your/file.txt')
"

# 验证索引
ls -la storage/vectors/
```

---

### 3. 文件下载被拒绝

**问题**: 下载文件时提示"路径不在白名单中"

**解决方案**:
```yaml
# 编辑 config.yaml，添加路径到白名单
file_access:
  allowed_paths:
    - "/home/zhoutianyu/tmp/LLMChatAssistant/**"
    - "/path/to/your/files/**"  # 添加你的路径
```

---

### 4. API 调用失败

**问题**: 索引或检索时提示"智谱 API 调用失败"

**解决方案**:
```bash
# 检查 API Key
echo $ZHIPU_API_KEY

# 验证 API Key 有效
python -c "
from src.llm.zhipu import ZhipuProvider
provider = ZhipuProvider()
try:
    result = provider.chat(messages=[{'role': 'user', 'content': '你好'}])
    print('API Key 有效')
except Exception as e:
    print(f'API Key 无效: {e}')
"

# 如果无效，重新设置
export ZHIPU_API_KEY="your_new_api_key"
```

---

### 5. 权限错误

**问题**: 文件操作时提示"权限不足"

**解决方案**:
```bash
# 检查目录权限
ls -la storage/
ls -la storage/uploads/

# 修改权限（如果需要）
chmod 755 storage/uploads
chmod 644 storage/uploads/*

# 检查磁盘空间
df -h
```

---

## 性能优化

### 1. 索引优化

**问题**: 大文件索引很慢

**解决方案**:
```python
# 调整索引超时时间
from src.tools.file_upload import FileUploadTool

tool = FileUploadTool()
tool.timeout = 60  # 增加到 60 秒

# 或者分批索引大文件
# (未来功能)
```

---

### 2. 并发控制

**问题**: 同时上传多个文件时性能下降

**解决方案**:
```python
# 限制并发上传数量
import asyncio

async def upload_files(files):
    semaphore = asyncio.Semaphore(3)  # 最多 3 个并发

    async def upload(file):
        async with semaphore:
            return await upload_file(file)

    tasks = [upload(f) for f in files]
    return await asyncio.gather(*tasks)
```

---

## 日志与调试

### 1. 查看日志

```bash
# 查看文件操作日志
tail -f logs/file_operations.log

# 过滤特定操作
grep "UPLOAD" logs/file_operations.log
grep "DOWNLOAD" logs/file_operations.log
grep "SEARCH" logs/file_operations.log
```

### 2. 启用调试模式

```python
# 在代码中启用调试日志
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('file_operations')
logger.setLevel(logging.DEBUG)
```

### 3. 监控性能

```python
# 记录工具执行时间
import time

start = time.time()
result = tool.execute(...)
duration = time.time() - start

print(f"工具执行时间: {duration:.2f} 秒")
```

---

## 常见问题 (FAQ)

### Q1: 支持哪些文件类型？

**A**: 仅支持文本文件，包括：
- 纯文本 (.txt)
- Markdown (.md)
- YAML (.yaml, .yml)
- JSON (.json)
- XML (.xml)
- Python (.py)
- JavaScript (.js)
- HTML (.html)
- CSS (.css)

不支持二进制文件（图片、视频、可执行文件等）。

---

### Q2: 文件大小限制是多少？

**A**: 最大 10MB。如果文件超过限制，请：
1. 压缩文件（如果可能）
2. 分割文件
3. 联系管理员调整限制

---

### Q3: 如何删除已上传的文件？

**A**: 目前可以通过以下方式：
```bash
# 手动删除
rm -rf storage/uploads/{file_id}/

# 或使用 Python API
from src.storage.files import UploadedFile
file = UploadedFile.load_metadata(file_id)
file.delete()
```

未来版本将提供 `file_delete` 工具。

---

### Q4: 语义检索的准确率如何？

**A**: 取决于多个因素：
- 查询描述的清晰度
- 文件内容的相关性
- 向量索引的质量

建议：
- 使用具体的查询词
- 避免过于宽泛的描述
- 尝试不同的查询方式

---

### Q5: 如何提高文件传输速度？

**A**:
1. 检查网络连接
2. 减小文件大小
3. 使用有线网络而非无线
4. 避免高峰时段

---

## 进阶用法

### 1. 批量上传

```python
# 批量上传多个文件
files = [
    ("file1.txt", "content1"),
    ("file2.txt", "content2"),
    ("file3.txt", "content3")
]

for filename, content in files:
    result = file_upload_tool.execute(
        filename=filename,
        content=content
    )
    print(f"{filename}: {result.success}")
```

### 2. 自定义检索

```python
# 使用更高的相似度阈值
result = file_search_tool.execute(
    query="数据库配置",
    top_k=5  # 返回更多结果
)

# 或者只查找特定类型的文件
# (未来功能)
```

---

## 获取帮助

如果遇到问题：

1. **查看日志**: `logs/file_operations.log`
2. **检查配置**: `config.yaml`
3. **运行测试**: `python -m pytest tests/`
4. **查看文档**: `specs/003-file-tools-integration/`
5. **提交 Issue**: 联系开发团队

---

## 更新日志

### v1.0 (2025-12-30)

- 初始版本
- 支持文件上传、下载、语义检索
- 支持串行工具调用
- 完整的安全验证和日志记录
