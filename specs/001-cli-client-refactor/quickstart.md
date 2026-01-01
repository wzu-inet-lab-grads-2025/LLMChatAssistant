# 快速入门指南: CLI客户端重构与验证

**版本**: 1.0.0
**日期**: 2026-01-01
**分支**: 001-cli-client-refactor

## 概述

本指南提供CLI客户端重构的快速入门，包括环境设置、重构步骤、测试方法和常见问题。

## 前置要求

### 系统要求

- **操作系统**: Linux/macOS/Windows
- **Python版本**: Python 3.11.x
- **包管理器**: uv (推荐) 或 pip
- **Git**: 用于版本控制

### API密钥

**必须配置智谱AI API密钥**（用于真实测试）:

```bash
# 方式1: 环境变量（推荐）
export ZHIPU_API_KEY="your_api_key_here"

# 方式2: .env文件
echo "ZHIPU_API_KEY=your_api_key_here" > .env
```

**获取API密钥**: 访问 [智谱AI开放平台](https://open.bigmodel.cn/) 注册并获取免费API密钥。

## 环境设置

### 1. 克隆仓库并切换分支

```bash
# 克隆仓库（如果还没有）
git clone <repository_url>
cd LLMChatAssistant

# 切换到重构分支
git checkout 001-cli-client-refactor
```

### 2. 安装依赖

```bash
# 使用uv安装依赖（推荐）
uv sync

# 或使用pip
pip install -r requirements.txt
```

### 3. 验证环境

```bash
# 检查Python版本
python --version  # 应显示 Python 3.11.x

# 检查uv版本
uv --version

# 验证API密钥
python -c "import os; print('API Key configured' if os.getenv('ZHIPU_API_KEY') else 'ERROR: API Key not found')"
```

### 4. 启动服务器

```bash
# 在一个终端启动服务器
python -m server.main

# 预期输出:
# [INFO] 服务器启动中...
# [INFO] 服务器监听 0.0.0.0:9999
# [INFO] RDT服务器监听 0.0.0.0:9998
# [INFO] 服务器就绪，等待客户端连接...
```

## 重构流程

### 阶段1: 验证现有功能

**目标**: 使用真实后端API和智谱AI全面验证现有12项CLI功能

#### 步骤1: 运行功能验证测试

```bash
# 在另一个终端运行验证测试
cd clients/cli  # 或 src/client（重构前）
python tests/validate_existing_features.py
```

**测试脚本示例** (`validate_existing_features.py`):

```python
"""
验证现有CLI功能的测试脚本
使用真实后端和智谱AI，禁止mock
"""

import asyncio
import os
from client.main import ClientMain

async def validate_feature(name, test_func):
    """验证单个功能"""
    print(f"\n{'='*60}")
    print(f"测试功能: {name}")
    print('='*60)
    try:
        result = await test_func()
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        return result
    except Exception as e:
        print(f"❌ ERROR: {name} - {e}")
        return False

async def test_connection():
    """测试1: 连接服务器"""
    client = ClientMain(host="127.0.0.1", port=9999)
    connected = await client.connect()
    if connected:
        await client.close()
        return True
    return False

async def test_chat():
    """测试2: 聊天功能（使用真实智谱API）"""
    client = ClientMain(host="127.0.0.1", port=9999)
    if not await client.connect():
        return False

    # 发送测试消息
    response = await client.send_message("你好")

    # 验证响应
    is_valid = (
        response is not None and
        len(response) > 0 and
        "你好" in response or "Hi" in response
    )

    await client.close()
    return is_valid

async def test_file_upload():
    """测试3: 文件上传"""
    # 创建测试文件
    test_file = "test_upload.txt"
    with open(test_file, "w") as f:
        f.write("测试文件内容")

    client = ClientMain(host="127.0.0.1", port=9999)
    if not await client.connect():
        return False

    # 上传文件
    result = await client.upload_file(test_file, "测试说明")

    # 清理
    os.remove(test_file)
    await client.close()

    return result.get("success", False)

# ... 更多测试函数 ...

async def main():
    """运行所有测试"""
    print("开始验证现有CLI功能...")
    print("="*60)

    # 检查API密钥
    if not os.getenv("ZHIPU_API_KEY"):
        print("❌ ERROR: ZHIPU_API_KEY未配置")
        print("请运行: export ZHIPU_API_KEY='your_api_key_here'")
        return

    # 12项功能测试
    tests = [
        ("连接服务器", test_connection),
        ("聊天消息", test_chat),
        ("文件上传", test_file_upload),
        ("文件下载", test_file_download),
        ("会话列表", test_session_list),
        ("切换会话", test_session_switch),
        ("新建会话", test_session_new),
        ("删除会话", test_session_delete),
        ("切换模型", test_model_switch),
        ("历史记录", test_history),
        ("清空历史", test_history_clear),
        ("自动重连", test_auto_reconnect),
    ]

    results = []
    for name, test_func in tests:
        result = await validate_feature(name, test_func)
        results.append((name, result))

    # 生成报告
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    # 保存报告
    with open("validation_report.txt", "w") as f:
        f.write(f"验证时间: {datetime.now()}\n")
        f.write(f"通过率: {passed}/{total}\n\n")
        for name, result in results:
            status = "PASS" if result else "FAIL"
            f.write(f"{status}: {name}\n")

if __name__ == "__main__":
    asyncio.run(main())
```

#### 步骤2: 分析测试结果

```bash
# 查看测试报告
cat validation_report.txt

# 或查看日志
tail -f logs/client.log
```

#### 步骤3: 记录问题

创建问题清单文件 `issues/identified_issues.md`:

```markdown
# 识别的问题清单

## P0级别问题（阻塞功能）

- [ ] 问题1: 描述
  - 复现步骤: ...
  - 实际行为: ...
  - 预期行为: ...
  - 修复建议: ...

## P1级别问题（严重影响）

- [ ] 问题2: 描述
  - ...
```

### 阶段2: 修复问题

根据问题清单逐个修复：

```bash
# 修复问题
# （手动编辑代码）

# 运行回归测试
python tests/validate_existing_features.py

# 验证修复
git diff
```

### 阶段3: 执行目录重构

#### 步骤1: 创建新目录结构

```bash
# 创建顶层目录
mkdir -p clients/cli
mkdir -p clients/desktop
mkdir -p clients/web
mkdir -p shared
mkdir -p server

# 创建子目录
mkdir -p clients/cli/protocols
mkdir -p clients/cli/services
mkdir -p clients/cli/config
mkdir -p clients/cli/tests
mkdir -p server/protocols
mkdir -p server/tests
mkdir -p shared/utils
mkdir -p shared/storage
mkdir -p shared/llm
```

#### 步骤2: 移动文件

```bash
# 移动客户端文件
mv src/client/*.py clients/cli/
mv src/client/protocols/* clients/cli/protocols/

# 移动服务器文件
mv src/server/*.py server/
mv src/server/protocols/* server/protocols/

# 移动共享代码
mv src/utils/* shared/utils/
mv src/storage/* shared/storage/
mv src/llm/* shared/llm/
```

#### 步骤3: 更新导入路径

使用自动化脚本批量更新：

```bash
# 运行导入路径更新脚本
python scripts/update_imports.py
```

**脚本示例** (`update_imports.py`):

```python
"""
批量更新Python导入路径
"""

import os
import re

def update_imports_in_file(filepath):
    """更新单个文件的导入路径"""
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    # 更新客户端导入
    content = re.sub(
        r'from client\.',

import ', 'from clients.cli.', content)
    content = re.sub(
        r'from protocols\.',
        'from clients.cli.protocols.',
        content)

    # 更新服务器导入
    content = re.sub(
        r'from server\.',
        'from server.',
        content)

    # 更新共享代码导入
    content = re.sub(
        r'from utils\.',
        'from shared.utils.',
        content)
    content = re.sub(
        r'from storage\.',
        'from shared.storage.',
        content)
    content = re.sub(
        r'from llm\.',
        'from shared.llm.',
        content)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Updated: {filepath}")
        return True
    return False

def main():
    """遍历所有Python文件并更新导入"""
    for root, dirs, files in os.walk('.'):
        # 跳过虚拟环境和缓存
        dirs[:] = [d for d in dirs if d not in ['.venv', '__pycache__', '.git']]

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                update_imports_in_file(filepath)

if __name__ == "__main__":
    main()
```

#### 步骤4: 创建独立协议副本

```bash
# 复制协议定义到客户端
cp src/protocols/nplt.py clients/cli/protocols/
cp src/protocols/rdt.py clients/cli/protocols/

# 复制协议定义到服务器
cp src/protocols/nplt.py server/protocols/
cp src/protocols/rdt.py server/protocols/
```

#### 步骤5: 更新配置文件

创建 `clients/cli/config/config.yaml.example`:

```yaml
# CLI客户端配置文件示例

server:
  host: "127.0.0.1"
  port: 9999
  rdt_port: 9998
  timeout: 30
  auto_reconnect: true
  max_retries: 3

client:
  default_model: "glm-4-flash"
  max_file_size: 10485760  # 10MB
  log_level: "INFO"

ui:
  terminal_type: "auto"  # auto | vscode | standard
  stream_speed: 0.05     # 流式输出延迟（秒）
  enable_colors: true
```

### 阶段4: 回归测试

```bash
# 运行完整测试套件
cd clients/cli
pytest tests/ -v --tb=short

# 运行性能测试
pytest tests/ --performance -v

# 生成覆盖率报告
pytest tests/ --cov=. --cov-report=html
```

### 阶段5: 文档更新

```bash
# 更新README.md
# （手动编辑 README.md 反映新目录结构）

# 生成架构文档
python scripts/generate_architecture_docs.py

# 更新API文档
# （手动更新 API 文档）
```

## 测试方法

### 单元测试

```bash
# 运行单元测试
pytest tests/unit/ -v

# 示例测试文件: tests/unit/test_protocol.py
import pytest
from clients.cli.protocols.nplt import NPLTMessage

def test_nplt_message_encoding():
    """测试NPLT消息编码"""
    msg = NPLTMessage(type=0x01, seq=1, data=b"Hello")
    encoded = msg.encode()

    assert encoded[0] == 0x01  # Type
    assert encoded[1:3] == (1).to_bytes(2, 'big')  # Seq
    assert len(encoded) == 7  # Header + Data

def test_nplt_message_decoding():
    """测试NPLT消息解码"""
    data = bytes([0x01]) + (1).to_bytes(2, 'big') + (5).to_bytes(2, 'big') + b"Hello"
    msg = NPLTMessage.decode(data)

    assert msg.type == 0x01
    assert msg.seq == 1
    assert msg.data == b"Hello"
```

### 集成测试

```bash
# 运行集成测试
pytest tests/integration/ -v

# 示例测试文件: tests/integration/test_client_server.py
import pytest
from clients.cli.main import ClientMain

@pytest.mark.asyncio
async def test_client_server_communication():
    """测试客户端-服务器通信（真实服务器）"""
    client = ClientMain(host="127.0.0.1", port=9999)

    # 连接测试
    connected = await client.connect()
    assert connected is True

    # 聊天测试
    response = await client.send_message("测试消息")
    assert response is not None
    assert len(response) > 0

    # 清理
    await client.close()
```

### E2E测试

```bash
# 运行E2E测试
pytest tests/e2e/ -v

# 示例测试文件: tests/e2e/test_complete_workflow.py
import pytest
from clients.cli.main import ClientMain

@pytest.mark.e2e
async def test_complete_user_workflow():
    """测试完整的用户工作流程"""
    client = ClientMain(host="127.0.0.1", port=9999)

    # 1. 连接
    assert await client.connect()

    # 2. 聊天
    response = await client.send_message("你好")
    assert response is not None

    # 3. 上传文件
    result = await client.upload_file("test.txt", "测试")
    assert result.get("success")

    # 4. 下载文件
    await client.request_download(result["file_id"])

    # 5. 切换模型
    await client.switch_model("glm-4.5-flash")

    # 6. 清理
    await client.close()
```

## 常见问题

### Q1: ImportError: No module named 'client'

**原因**: 导入路径未更新

**解决**:
```bash
# 运行导入路径更新脚本
python scripts/update_imports.py
```

### Q2: 连接服务器失败

**原因**: 服务器未启动或端口被占用

**解决**:
```bash
# 检查服务器是否启动
ps aux | grep python | grep server

# 检查端口
netstat -an | grep 9999

# 重启服务器
python -m server.main
```

### Q3: API密钥错误

**原因**: ZHIPU_API_KEY未配置或无效

**解决**:
```bash
# 配置API密钥
export ZHIPU_API_KEY="your_api_key_here"

# 验证
python -c "import os; print(os.getenv('ZHIPU_API_KEY'))"
```

### Q4: 测试超时

**原因**: 网络延迟或服务器响应慢

**解决**:
```bash
# 增加测试超时时间
pytest tests/ --timeout=60 -v
```

### Q5: 文件上传失败

**原因**: 文件大小超过限制或路径不在白名单

**解决**:
```bash
# 检查文件大小
ls -lh test.txt

# 检查白名单配置
cat config.yaml | grep allowed_paths
```

## 提交检查清单

每完成一个阶段，确保：

- [ ] 所有测试通过（100%通过率）
- [ ] 代码符合项目规范
- [ ] 日志无错误或异常
- [ ] 文档已更新
- [ ] Git提交消息清晰

**提交示例**:

```bash
git add .
git commit -m "feat: 完成功能验证与修复阶段

- 编写12项功能的真实测试用例
- 识别并修复5个P0/P1问题
- 测试通过率: 100%
- 无mock，全部使用真实API

测试结果:
  ✅ 连接服务器: PASS
  ✅ 聊天消息: PASS
  ✅ 文件上传: PASS
  ✅ 文件下载: PASS
  ✅ 会话管理: PASS
  ✅ 模型切换: PASS
  ✅ 历史记录: PASS
  ✅ 自动重连: PASS

报告: validation_report.txt"
```

## 下一步

完成重构后，可以：

1. **生成最终报告**: `python scripts/generate_final_report.py`
2. **打包客户端**: `python scripts/build_client.py`
3. **部署到生产**: 参见部署文档

## 参考资源

- [项目README](../../README.md)
- [架构文档](../../docs/architecture.md)
- [API契约](./contracts/client-api.yaml)
- [数据模型](./data-model.md)
- [研究文档](./research.md)

---

**需要帮助?** 请查看 [项目文档](../../docs/) 或提交Issue。
