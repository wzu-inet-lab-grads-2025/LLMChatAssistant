# 快速开始指南: 测试全面重构与实现验证

**功能分支**: `001-test-overhaul-validation`
**生成日期**: 2025-12-29
**状态**: 阶段 1 输出

## 概述

本指南提供了测试重构与验证项目的快速开始步骤，包括环境配置、测试执行和常见问题排查。

## 前置要求

### 1. 系统要求

- **操作系统**: Linux/macOS/Windows（推荐 Linux 或 macOS）
- **Python**: 3.11（必需，不兼容其他版本）
- **内存**: 至少 4GB RAM（推荐 8GB）
- **磁盘**: 至少 2GB 可用空间
- **网络**: 能够访问智谱 API（`open.bigmodel.cn`）

### 2. 必需工具

- **uv**: Python 包管理器（用于虚拟环境和依赖管理）
- **Git**: 版本控制（用于克隆仓库）

## 快速开始（5 分钟）

### 步骤 1: 安装依赖（2 分钟）

```bash
# 1. 确认 Python 版本
python --version
# 输出应为: Python 3.11.x

# 2. 安装 uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或使用 pip
pip install uv

# 3. 同步依赖
uv sync
```

### 步骤 2: 配置环境（2 分钟）

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env 文件，填入智谱 API key
nano .env
# 或使用其他编辑器
# vim .env
# code .env

# 内容如下:
ZHIPU_API_KEY=your-api-key-here  # 替换为你的真实 API key
```

**获取智谱 API key**:
1. 访问 [智谱 AI 开放平台](https://open.bigmodel.cn/)
2. 注册/登录账户
3. 进入"API Keys"页面
4. 创建新的 API key
5. 复制 API key（格式：id.secret）

### 步骤 3: 验证配置（1 分钟）

```bash
# 1. 验证配置文件格式
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
# 无输出表示格式正确

# 2. 验证 .env 文件
grep ZHIPU_API_KEY .env
# 应显示: ZHIPU_API_KEY=your-api-key-here

# 3. 验证 API key 格式
python -c "
import os
key = os.getenv('ZHIPU_API_KEY', '')
if '.' not in key:
    print('❌ API key 格式无效（应为 id.secret）')
else:
    print('✅ API key 格式正确')
"

# 4. 测试 API 连接（可选）
python -c "
import asyncio
from src.llm.zhipu import ZhipuProvider

async def test():
    provider = ZhipuProvider(api_key=os.getenv('ZHIPU_API_KEY'))
    try:
        result = await provider.embed(texts=['测试'], model='embedding-3-pro')
        print('✅ API key 有效')
    except Exception as e:
        print(f'❌ API key 无效: {e}')

asyncio.run(test())
"
```

### 步骤 4: 运行测试（10 秒）

```bash
# 快速测试（仅单元测试，< 30 秒）
pytest -m unit -v

# 完整测试（包括集成测试，可能需要 2-5 分钟）
pytest -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html
# 查看: open htmlcov/index.html
```

## 测试执行详解

### 1. 测试分组

项目使用 pytest 标记进行测试分组：

```bash
# 单元测试（快速，无网络调用）
pytest -m unit
# 预期时间: < 30 秒

# 集成测试（需要真实 API）
pytest -m integration
# 预期时间: 1-3 分钟

# 契约测试（协议验证）
pytest -m contract
# 预期时间: < 1 分钟

# 性能测试（验证性能指标）
pytest -m performance
# 预期时间: 1-2 分钟

# 所有测试
pytest -v
# 预期时间: 2-5 分钟

# 排除慢速测试
pytest -m "not slow"
```

### 2. 常用测试命令

```bash
# 详细输出
pytest -vv

# 显示局部变量（失败时）
pytest -l

# 显示完整堆栈跟踪
pytest --tb=long

# 显示打印输出
pytest -s

# 遇到第一个失败就停止
pytest -x

# 失败后继续运行
pytest --maxfail=3

# 重新运行失败的测试
pytest --lf

# 并行运行（需要 pytest-xdist）
pytest -n auto

# 监视模式（需要 pytest-watch）
pytest-watch
```

### 3. 覆盖率报告

```bash
# 终端覆盖率报告
pytest --cov=src --cov-report=term-missing

# HTML 覆盖率报告
pytest --cov=src --cov-report=html
# 查看: open htmlcov/index.html

# XML 覆盖率报告（用于 CI）
pytest --cov=src --cov-report=xml

# 设置覆盖率阈值（< 90% 则失败）
pytest --cov=src --cov-fail-under=90
```

### 4. 性能测试

```bash
# 运行性能测试
pytest -m performance -v

# 带性能分析的测试（需要 pytest-profiling）
pytest -m performance --profile

# 内存分析（需要 pytest-memray）
pytest -m performance --memray
```

## 环境配置详解

### 1. config.yaml 结构

```yaml
# 服务器配置
server:
  host: "0.0.0.0"           # 监听地址（0.0.0.0 = 所有接口）
  port: 9999                # 监听端口（1024-65535）
  max_clients: 10           # 最大并发客户端数
  heartbeat_interval: 90    # 心跳间隔（秒）
  storage_dir: "storage"    # 存储目录
  logs_dir: "logs"          # 日志目录
  log_level: "INFO"         # 日志级别（DEBUG/INFO/WARNING/ERROR）

# LLM 配置
llm:
  chat_model: "glm-4-flash"      # 聊天模型（glm-4-flash 或 glm-4.5-flash）
  embed_model: "embedding-3-pro" # 嵌入模型
  temperature: 0.7               # 温度参数（0.0-1.0）
  max_tokens: 128000             # 最大 token 数（glm-4-flash 的正确值）
  timeout: 30                    # API 调用超时（秒）
  api_key: "${ZHIPU_API_KEY}"    # API key（从环境变量读取）

# 存储配置
storage:
  storage_dir: "storage"    # 存储根目录
  logs_dir: "logs"          # 日志目录

# 日志配置
logging:
  level: "INFO"             # 日志级别
  format: "%(asctime)s [%(levelname)s] %(message)s"  # 日志格式
```

### 2. .env 文件配置

```bash
# 必需的环境变量
ZHIPU_API_KEY=1234567890.abcdefghijklmnopqrstuvwxyz  # 智谱 API key

# 可选的环境变量
# SERVER_HOST=0.0.0.0            # 覆盖 config.yaml 中的 server.host
# SERVER_PORT=9999               # 覆盖 config.yaml 中的 server.port
# LLM_MODEL=glm-4.5-flash        # 覆盖模型配置
# LOG_LEVEL=DEBUG                # 覆盖日志级别
```

### 3. pytest.ini 配置

```ini
[pytest]
# 测试发现
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 测试路径
testpaths = tests

# 命令行选项
addopts =
    -v                      # 详细输出
    -l                      # 显示局部变量
    --tb=long               # 完整堆栈跟踪
    -s                      # 显示打印输出
    --strict-markers        # 严格标记模式
    --asyncio-mode=auto     # 异步测试

# 标记定义
markers =
    unit: 单元测试（快速，无外部依赖）
    integration: 集成测试（需要真实 API）
    contract: 契约测试（验证协议规范）
    performance: 性能测试（验证性能指标）
    requires_api_key: 需要智谱 API key
    slow: 运行缓慢的测试（需要网络调用）

# 日志配置
log_cli = true
log_cli_level = INFO
log_file = logs/pytest.log
log_file_level = DEBUG
```

## 常见问题排查

### 问题 1: 服务器启动失败

**症状**: `python -m src.server.main` 报错

**可能原因**:
1. 配置文件格式错误
2. API key 未配置或无效
3. 端口已被占用
4. 依赖包未安装

**排查步骤**:

```bash
# 1. 检查配置文件格式
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
# 如果报错，YAML 格式有问题

# 2. 检查 API key
grep ZHIPU_API_KEY .env
# 应显示: ZHIPU_API_KEY=xxx.xxx

# 3. 检查端口占用
lsof -i :9999  # Linux/macOS
netstat -ano | findstr :9999  # Windows
# 如果有输出，端口被占用，杀掉进程或更换端口

# 4. 检查依赖
uv pip list | grep zai
# 应显示: zai-sdk x.x.x

# 5. 查看详细错误日志
python -m src.server.main 2>&1 | tee logs/startup.log
```

**修复方案**:

```bash
# 修复配置文件格式（参考上面的 config.yaml 结构）

# 重新设置 API key
nano .env
# 粘贴正确的 API key

# 杀掉占用端口的进程
kill -9 <PID>  # Linux/macOS
taskkill /PID <PID> /F  # Windows

# 重新安装依赖
uv sync --reinstall
```

### 问题 2: API 调用失败（401/403/429）

**症状**: 测试报错 `ZaiError: 401 Unauthorized`

**可能原因**:
1. API key 错误或已过期
2. API 配额已用尽
3. API 调用频率超限

**排查步骤**:

```bash
# 1. 验证 API key 格式
python -c "
import os
key = os.getenv('ZHIPU_API_KEY', '')
parts = key.split('.')
if len(parts) != 2 or not all(parts):
    print('❌ API key 格式错误')
else:
    print('✅ API key 格式正确')
"

# 2. 测试 API 连接
python -c "
import asyncio
from src.llm.zhipu import ZhipuProvider

async def test():
    provider = ZhipuProvider(api_key=os.getenv('ZHIPU_API_KEY'))
    try:
        result = await provider.embed(texts=['测试'], model='embedding-3-pro')
        print('✅ API 调用成功')
    except Exception as e:
        print(f'❌ API 调用失败: {e}')

asyncio.run(test())
"
```

**修复方案**:

```bash
# 1. 重新生成 API key
# 访问 https://open.bigmodel.cn/
# 删除旧 key，创建新 key
# 更新 .env 文件

# 2. 充值或升级套餐
# 检查账户余额和配额

# 3. 减少调用频率
# 使用 pytest 的串行模式（不并行）
pytest -v -n 1
```

### 问题 3: 测试超时

**症状**: 测试运行超过预期时间，最终超时失败

**可能原因**:
1. 网络连接缓慢
2. API 响应慢
3. 超时设置过小

**修复方案**:

```bash
# 1. 增加超时时间
# 编辑 config.yaml
llm:
  timeout: 60  # 增加到 60 秒

# 2. 使用 pytest 超时
pytest --timeout=300  # 全局超时 5 分钟

# 3. 跳过慢速测试
pytest -m "not slow"

# 4. 并行运行（加快整体速度）
pytest -n auto
```

### 问题 4: 覆盖率不足

**症状**: `pytest --cov` 报告覆盖率 < 90%

**可能原因**:
1. 测试用例不足
2. 某些代码分支未覆盖
3. 条件渲染或异常处理未测试

**修复方案**:

```bash
# 1. 查看未覆盖的代码
pytest --cov=src --cov-report=term-missing
# 注意: 行号后面的 "!!!!" 表示未覆盖

# 2. 查看详细 HTML 报告
pytest --cov=src --cov-report=html
open htmlcov/index.html
# 点击具体文件，查看哪些行未覆盖（红色高亮）

# 3. 针对性添加测试
# 为未覆盖的代码分支添加测试用例

# 4. 检查是否有死代码
# 删除永远不会执行的代码
```

### 问题 5: 导入错误

**症状**: `ModuleNotFoundError: No module named 'xxx'`

**可能原因**:
1. 虚拟环境未激活
2. 依赖包未安装
3. Python 路径问题

**修复方案**:

```bash
# 1. 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 2. 重新安装依赖
uv sync --reinstall

# 3. 检查 Python 路径
python -c "import sys; print('\n'.join(sys.path))"

# 4. 添加项目根目录到路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
# 或在 pytest.ini 中配置:
# pythonpath = .
```

### 问题 6: 内存泄漏

**症状**: 长时间运行后内存持续增长

**排查步骤**:

```bash
# 1. 使用内存分析工具
pip install pytest-memray
pytest --memray

# 2. 长时间运行测试
pytest -k "test_long_conversation" --memray

# 3. 查看内存报告
# 生成 memray 报告，分析内存泄漏位置
```

**修复方案**:

```python
# 1. 确保资源正确释放
# 在 tearDown 或 fixture cleanup 中关闭连接、释放资源

@pytest.fixture
async def client():
    client = Client()
    yield client
    await client.close()  # 确保资源释放

# 2. 避免循环引用
# 使用 weakref 或显式删除引用

# 3. 限制缓存大小
# 如果使用缓存，设置最大大小
```

## 测试最佳实践

### 1. 开发工作流

```bash
# 1. 修改代码
vim src/xxx.py

# 2. 快速测试（仅相关单元测试）
pytest tests/unit/test_xxx.py -v

# 3. 如果通过，运行完整测试套件
pytest -v

# 4. 如果全部通过，生成覆盖率报告
pytest --cov=src --cov-report=html

# 5. 提交代码
git add .
git commit -m "feat: 实现功能 X，测试通过"
```

### 2. 调试失败的测试

```bash
# 1. 运行单个失败测试
pytest tests/unit/test_xxx.py::TestClassName::test_method -v

# 2. 使用 pdb 调试
pytest --pdb

# 3. 显示详细输出
pytest -vv -s

# 4. 仅运行上次失败的测试
pytest --lf

# 5. 先运行失败的，再运行其他的
pytest --ff
```

### 3. CI/CD 集成

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Configure environment
        run: |
          echo "ZHIPU_API_KEY=${{ secrets.ZHIPU_API_KEY }}" > .env

      - name: Run tests
        run: pytest --cov=src --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## 性能优化建议

### 1. 加速测试运行

```bash
# 1. 并行运行（需要 pytest-xdist）
pip install pytest-xdist
pytest -n auto

# 2. 只运行修改的测试
pytest --modified

# 3. 跳过慢速测试
pytest -m "not slow"

# 4. 使用缓存（pytest-cache）
pytest --cache-clear  # 清除缓存
pytest --cache-show   # 显示缓存
```

### 2. 减少 API 调用

```bash
# 1. 跳过集成测试
pytest -m "not integration"

# 2. 使用 mock（仅用于开发，不提交）
# pytest --mock-mode=record  # 首次记录
# pytest --mock-mode=replay  # 后续重放

# 3. 批量测试（减少重复 API 调用）
# 将多个独立测试合并为一个
```

### 3. 优化测试数据

```python
# 1. 使用 fixtures 共享数据
@pytest.fixture
def sample_messages():
    return ["消息1", "消息2", "消息3"]

# 2. 使用工厂模式生成测试数据
@pytest.fixture
def message_factory():
    def create_message(content):
        return Message(role="user", content=content)
    return create_message

# 3. 清理测试数据
@pytest.fixture(autouse=True)
def clean_test_data():
    yield
    # 清理临时文件
    shutil.rmtree("tmp", ignore_errors=True)
```

## 下一步

1. **修复服务器启动问题**: 按照 [research.md](./research.md#研究领域-1-服务器启动问题诊断) 修复配置
2. **运行测试套件**: `pytest -v`
3. **查看覆盖率报告**: `open htmlcov/index.html`
4. **提交测试结果**: `git add . && git commit -m "test: 测试通过，覆盖率达标"`

## 获取帮助

- **查看日志**: `tail -f logs/pytest.log`
- **查看完整文档**: [spec.md](./spec.md)
- **查看研究文档**: [research.md](./research.md)
- **查看测试合同**: [contracts/test-contracts.md](./contracts/test-contracts.md)

## 参考资料

- [pytest 官方文档](https://docs.pytest.org/)
- [智谱 AI 开放平台](https://open.bigmodel.cn/)
- [项目章程](../../.specify/memory/constitution.md)
- [001-llm-chat-assistant 规范](../001-llm-chat-assistant/spec.md)
