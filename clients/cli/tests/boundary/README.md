# 边界测试文档

## 概述

本目录包含边界测试，用于测试系统在各种极端条件下的行为。所有测试遵循项目章程：使用真实API，禁止mock。

## 测试文件

### 1. test_large_files.py
大文件边界测试，验证文件上传的10MB限制。

**测试用例（6个）：**
- `test_upload_1mb_file` - 测试1MB文件上传
- `test_upload_5mb_file` - 测试5MB文件上传
- `test_upload_10mb_file_boundary` - 测试10MB边界值文件上传
- `test_upload_11mb_file_rejected` - 测试11MB文件被拒绝
- `test_multiple_large_files_memory_leak` - 测试多个大文件上传的内存泄漏
- `test_file_integrity_after_upload` - 测试文件上传后的完整性

**验收标准：**
- 1MB、5MB、10MB文件成功上传
- 11MB文件被拒绝
- 内存使用无泄漏（增长在合理范围内）
- 文件完整性验证通过

### 2. test_concurrent_clients.py
并发客户端边界测试，验证服务器在高并发场景下的稳定性。

**测试用例（8个）：**
- `test_two_concurrent_clients` - 测试2个客户端同时连接
- `test_five_concurrent_clients` - 测试5个客户端同时连接
- `test_ten_concurrent_clients` - 测试10个客户端同时连接（达到上限）
- `test_concurrent_file_uploads` - 测试并发文件上传
- `test_concurrent_chat_sessions` - 测试并发聊天会话
- `test_server_stability_under_load` - 测试服务器在高并发下的稳定性
- `test_concurrent_connect_disconnect` - 测试并发连接和断开
- `test_message_order_preservation` - 测试消息顺序保持

**验收标准：**
- 所有客户端成功连接
- 并发操作不冲突
- 服务器保持稳定
- 消息顺序正确

## 运行测试

### 前置条件

1. **启动服务器**（在另一个终端）：
```bash
cd /home/zhoutianyu/tmp/LLMChatAssistant
source .venv/bin/activate
python -m server.main
```

2. **确保环境变量配置**：
```bash
# .env文件需要包含：
ZHIPU_API_KEY=your_api_key_here
```

### 运行所有边界测试

```bash
cd /home/zhoutianyu/tmp/LLMChatAssistant
source .venv/bin/activate

# 运行所有边界测试
pytest src/client/tests/boundary/ -v -m boundary
```

### 运行特定测试文件

```bash
# 运行大文件测试
pytest src/client/tests/boundary/test_large_files.py -v

# 运行并发客户端测试
pytest src/client/tests/boundary/test_concurrent_clients.py -v
```

### 运行单个测试用例

```bash
# 运行特定测试
pytest src/client/tests/boundary/test_large_files.py::TestLargeFiles::test_upload_1mb_file -v

# 运行并发测试
pytest src/client/tests/boundary/test_concurrent_clients.py::TestConcurrentClients::test_two_concurrent_clients -v
```

### 带详细输出的运行

```bash
# 显示print输出
pytest src/client/tests/boundary/ -v -s

# 显示更详细的错误信息
pytest src/client/tests/boundary/ -v -vv
```

## 依赖项

**必需依赖：**
- pytest
- pytest-asyncio
- 项目所有依赖（见requirements.txt）

**可选依赖：**
- psutil（用于内存监控测试，未安装时会跳过相关测试）

## 测试标记

所有测试都标记为 `@pytest.mark.boundary`，可以使用以下命令运行：

```bash
# 只运行边界测试
pytest -m boundary -v

# 排除边界测试
pytest -m "not boundary" -v
```

## 注意事项

1. **服务器必须先启动**：这些测试需要真实的服务器连接
2. **环境变量**：确保ZHIPU_API_KEY已配置
3. **内存使用**：大文件测试会创建临时文件，测试完成后自动清理
4. **执行时间**：边界测试可能需要较长时间，请耐心等待
5. **临时文件**：测试创建的临时文件会自动清理到系统临时目录

## 故障排除

### 测试超时
如果测试超时，检查：
1. 服务器是否正在运行（`netstat -an | grep 9999`）
2. 防火墙是否阻止连接
3. API密钥是否有效

### 导入错误
如果遇到导入错误：
```bash
# 确保使用虚拟环境
source .venv/bin/activate

# 验证Python路径
python -c "import sys; print('\n'.join(sys.path))"
```

### 内存监控测试被跳过
如果看到 "psutil未安装，跳过内存监控测试"：
```bash
pip install psutil
```

## 测试报告

测试运行后会生成详细报告，包括：
- 每个测试的执行状态
- 内存使用情况（如果安装了psutil）
- 文件上传/下载统计
- 服务器会话信息

## 清理

如果测试中断，手动清理临时文件：
```bash
# 清理系统临时目录中的测试文件
rm -rf /tmp/large_files_test_*
rm -rf /tmp/pytest_*
```

## 贡献指南

添加新的边界测试时：
1. 所有测试必须是async函数
2. 使用真实服务器和真实API，禁止mock
3. 添加适当的异常处理和清理逻辑
4. 标记为 `@pytest.mark.boundary`
5. 在本README中记录新的测试用例
