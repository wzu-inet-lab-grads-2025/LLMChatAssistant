# 快速开始指南

**功能**: 001-llm-chat-assistant | **日期**: 2025-12-28

## 概述

本指南帮助您快速搭建和运行智能网络运维助手系统。

## 前置条件

### 必需

- Python 3.11
- uv (Python 包管理器)
- 智谱 AI API Key

### 系统要求

- Linux/macOS/Windows
- 至少 100MB 可用磁盘空间
- 网络连接（调用智谱 API）

## 安装步骤

### 1. 克隆仓库

```bash
git clone <repository-url>
cd LLMChatAssistant
git checkout 001-llm-chat-assistant
```

### 2. 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. 创建虚拟环境

```bash
uv venv --python 3.11
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows
```

### 4. 安装依赖

```bash
uv pip install -e .
```

**核心依赖**:
- `zai-sdk`: 智谱 AI SDK
- `rich`: CLI UI 库
- `numpy`: 向量计算

## 配置

### 1. 创建配置文件

在项目根目录创建 `config.yaml`:

```yaml
# config.yaml
server:
  host: "0.0.0.0"
  port: 9999
  max_clients: 10
  heartbeat_interval: 90

llm:
  model: "glm-4-flash"
  temperature: 0.7
  max_tokens: 2000
  timeout: 30

storage:
  storage_dir: "storage"
  logs_dir: "logs"

logging:
  level: "INFO"
```

### 2. 设置环境变量

创建 `.env` 文件（项目根目录）:

```bash
echo "ZHIPU_API_KEY=your-api-key-here" > .env
```

**重要**: `.env` 文件包含敏感信息，不应提交到版本控制（已在 .gitignore 中）

### 3. 验证配置

```bash
python -m src.utils.config validate
```

输出应显示：`✓ 配置验证通过`

## 配置说明

**配置优先级**: 命令行参数 > 环境变量 > config.yaml

**环境变量覆盖**: 可以通过设置环境变量临时覆盖 config.yaml 中的配置

```bash
# 临时使用不同的模型
ZHIPU_API_KEY="your-key" LLM_MODEL="glm-4.5-flash" python -m src.server.main
```

**配置文件位置**:
- 服务器: `config.yaml` (项目根目录)
- 客户端: `config.client.yaml` (可选，用于指定服务器地址)
```

输出:
```
✓ API Key 已配置
✓ Python 版本: 3.11
✓ uv 已安装
```

## 运行

### 启动服务器

```bash
python -m src.server.main
```

输出:
```
[2025-12-28 10:30:00] [INFO] [SERVER] 服务器启动在 0.0.0.0:9999
[2025-12-28 10:30:00] [INFO] [STORAGE] 初始化存储目录
[2025-12-28 10:30:00] [INFO] [VECTOR] 加载向量索引: 0 个文件
[2025-12-28 10:30:00] [INFO] [LLM] 连接智谱 API: glm-4-flash
[2025-12-28 10:30:00] [INFO] [SERVER] 服务器就绪，等待客户端连接...
```

### 启动客户端

**新开一个终端窗口**:

```bash
python -m src.client.main
```

输出:
```
╭────────────────────────────────────────╮
│     智能网络运维助手 v1.0              │
╰────────────────────────────────────────╯

[2025-12-28 10:30:15] [INFO] [CLIENT] 连接到服务器 127.0.0.1:9999
[2025-12-28 10:30:15] [INFO] [CLIENT] 连接成功
────────────────────────────────────────────────
输入您的消息，输入 /quit 退出，/help 查看帮助
────────────────────────────────────────────────
```

## 使用示例

### 基础对话

```
你: 帮我检查一下服务器内存

AI: [Tool: sys_monitor] 正在读取系统指标...
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

    系统监控结果:
    • CPU 使用率: 45%
    • 内存使用: 8.5GB / 16GB (53%)
    • 磁盘使用: 120GB / 500GB (24%)
```

### 上传文件并检索

```
你: /upload config.yaml

[INFO] 上传文件: config.yaml (2.5 KB)
████████████████████ 100% 完成

[INFO] 文件已建立索引

你: config.yaml 中的数据库配置是什么？

AI: 根据 config.yaml 的内容，数据库配置如下:

    database:
      host: localhost
      port: 5432
      name: myapp_db
      user: admin
      password: ***
```

### 文件下载

```
你: 帮我下载最新的错误日志

AI: 我发现有错误日志文件: error.log (2.5 MB)

    [?] AI 准备发送文件: error.log (2.5 MB)
    接收下载? [y/n]

你: y

[INFO] 接收文件: error.log
窗口: [0] [1] [2] [3] [4]
进度: ████████████░░░░░░░ 50% (1.25 MB/s)
重传: 2 次

[INFO] 文件接收完成，保存到: ./error.log
```

## 命令参考

### 客户端命令

| 命令 | 描述 |
|------|------|
| `/help` | 显示帮助信息 |
| `/upload <file>` | 上传文件到服务器 |
| `/model <name>` | 切换聊天模型 (glm-4-flash / glm-4.5-flash) |
| `/history` | 查看对话历史 |
| `/clear` | 清空当前会话历史 |
| `/quit` | 退出客户端 |

### 服务器命令

| 命令 | 描述 |
|------|------|
| `Ctrl+C` | 优雅关闭服务器 |

## 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_llm.py
pytest tests/integration/test_agent.py

# 查看测试覆盖率
pytest --cov=src --cov-report=html
```

### 协议测试

```bash
# NPLT 协议测试
pytest tests/contract/test_nplt.py

# RDT 协议测试
pytest tests/contract/test_rdt.py
```

**注意**: 所有测试需要有效的智谱 API Key。

## 故障排除

### 问题 1: API Key 未配置

**错误信息**:
```
ConfigurationError: ZHIPU_API_KEY 未设置
```

**解决方案**:
```bash
export ZHIPU_API_KEY="your-api-key"
```

### 问题 2: 连接服务器失败

**错误信息**:
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**解决方案**:
1. 确认服务器已启动: `ps aux | grep python`
2. 检查端口占用: `netstat -an | grep 9999`
3. 查看服务器日志: `tail -f logs/server.log`

### 问题 3: API 调用失败

**错误信息**:
```
APIError: 401 Unauthorized
```

**解决方案**:
1. 验证 API Key 有效性
2. 检查 API 配额: 智谱 AI 控制台
3. 查看网络连接

### 问题 4: 文件上传失败

**错误信息**:
```
FileValidationError: 文件大小超过 10MB 限制
```

**解决方案**:
1. 压缩文件
2. 分割成小文件
3. 修改配置（如果需要）

## 目录结构

```
LLMChatAssistant/
├── src/                  # 源代码
├── tests/                # 测试
├── specs/                # 规范文档
│   └── 001-llm-chat-assistant/
│       ├── plan.md       # 实施计划
│       ├── research.md   # 研究文档
│       ├── data-model.md # 数据模型
│       └── contracts/    # 协议规范
├── storage/              # 运行时数据
│   ├── vectors/          # 向量索引
│   ├── history/          # 对话历史
│   └── uploads/          # 上传文件
├── logs/                 # 日志文件
├── pyproject.toml        # 项目配置
└── README.md             # 项目说明
```

## 开发工作流

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发和测试

```bash
# 编写代码
# 编写测试
pytest tests/...
```

### 3. 提交代码

```bash
git add .
git commit -m "feat: add your feature"
git push
```

### 4. 版本控制检查点

完成每个阶段后：

1. 运行测试: `pytest`
2. 确保所有测试通过
3. 提交版本: `git commit -m "docs: complete phase X - tests passing"`

## 下一步

- 查看 [data-model.md](data-model.md) 了解数据结构
- 查看 [contracts/](contracts/) 了解协议规范
- 查看 [research.md](research.md) 了解技术选择
- 运行 `/speckit.tasks` 生成实施任务

## 获取帮助

- 查看项目 README
- 查看文档: `docs/`
- 提交 Issue: GitHub Issues
