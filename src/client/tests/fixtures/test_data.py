"""
测试数据准备脚本
Constitution: 使用真实数据和真实API，禁止使用mock
"""

import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import json


class TestDataGenerator:
    """
    测试数据生成器

    为各种测试场景准备测试数据
    所有文件都是真实文件，用于真实文件传输测试
    """

    def __init__(self, base_dir: str = None):
        """
        初始化测试数据生成器

        Args:
            base_dir: 测试数据基础目录，默认使用临时目录
        """
        if base_dir is None:
            self.base_dir = Path(tempfile.mkdtemp(prefix="llmchat_test_"))
        else:
            self.base_dir = Path(base_dir)

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.created_files: List[Path] = []

    def create_text_file(self, filename: str, content: str, size_kb: float = None) -> Path:
        """
        创建文本测试文件

        Args:
            filename: 文件名
            content: 文件内容（如果指定了size_kb，则会被重复填充）
            size_kb: 文件大小（KB），可选

        Returns:
            文件路径
        """
        filepath = self.base_dir / filename

        if size_kb is not None:
            # 重复内容以达到指定大小
            target_size = int(size_kb * 1024)
            repeated_content = (content * (target_size // len(content) + 1))[:target_size]
            content = repeated_content

        filepath.write_text(content, encoding='utf-8')
        self.created_files.append(filepath)

        return filepath

    def create_config_file(self) -> Path:
        """创建配置测试文件"""
        content = """
# LLMChatAssistant 配置文件示例

server:
  host: "127.0.0.1"
  port: 9999
  rdt_port: 9998
  timeout: 30

llm:
  provider: "zhipu"
  model: "glm-4-flash"
  api_key_env: "ZHIPU_API_KEY"

storage:
  upload_path: "storage/uploads"
  vector_path: "storage/vectors"
  log_path: "logs"

file_access:
  allowed_paths:
    - "/tmp"
    - "./storage"
    - "./test_files"
  max_file_size: 10485760  # 10MB
"""
        return self.create_text_file("config.yaml", content)

    def create_python_file(self) -> Path:
        """创建Python代码测试文件"""
        content = '''
#!/usr/bin/env python3
"""
示例Python脚本 - 用于代码测试
"""


def hello_world():
    """打印Hello World"""
    print("Hello, World!")


def calculate_sum(a: int, b: int) -> int:
    """计算两个数的和"""
    return a + b


if __name__ == "__main__":
    hello_world()
    result = calculate_sum(10, 20)
    print(f"10 + 20 = {result}")
'''
        return self.create_text_file("example.py", content)

    def create_markdown_file(self) -> Path:
        """创建Markdown测试文件"""
        content = """
# LLMChatAssistant 使用指南

## 简介

LLMChatAssistant 是一个智能运维助手，基于大语言模型技术。

## 功能特性

1. **智能对话**: 支持自然语言交互
2. **文件管理**: 上传、下载、索引文件
3. **命令执行**: 安全执行系统命令
4. **语义检索**: 基于向量数据库的语义搜索

## 快速开始

### 启动服务器

```bash
python -m server.main
```

### 启动客户端

```bash
python -m client.main
```

## 常用命令

- `/help`: 显示帮助信息
- `/upload <file>`: 上传文件
- `/sessions`: 列出所有会话
- `/model <name>`: 切换模型

## 注意事项

1. 确保已配置智谱AI API Key
2. 文件大小限制为10MB
3. 支持的文件格式：txt, md, py, yaml, json
"""
        return self.create_text_file("README.md", content)

    def create_json_file(self) -> Path:
        """创建JSON测试文件"""
        data = {
            "project": "LLMChatAssistant",
            "version": "1.0.0",
            "features": [
                "智能对话",
                "文件管理",
                "命令执行",
                "语义检索"
            ],
            "config": {
                "server_port": 9999,
                "rdt_port": 9998,
                "max_file_size": 10485760,
                "default_model": "glm-4-flash"
            }
        }
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return self.create_text_file("metadata.json", content)

    def create_large_file(self, filename: str, size_mb: float) -> Path:
        """
        创建大文件测试（用于边界测试）

        Args:
            filename: 文件名
            size_mb: 文件大小（MB）

        Returns:
            文件路径
        """
        # 创建基础内容
        base_content = "这是一行测试数据，用于生成大文件。\n"
        # 计算需要的大小（KB）
        size_kb = size_mb * 1024
        return self.create_text_file(filename, base_content, size_kb)

    def create_special_filename_files(self) -> Dict[str, Path]:
        """
        创建特殊字符文件名的文件（用于边界测试）

        Returns:
            文件名字典
        """
        files = {}

        # 包含空格的文件名
        files["space"] = self.create_text_file("file with spaces.txt", "包含空格的文件名")

        # 包含中文的文件名
        files["chinese"] = self.create_text_file("测试文件.txt", "中文文件名")

        # 包含特殊字符的文件名
        files["special"] = self.create_text_file("file-with_special.chars.txt", "特殊字符文件名")

        # 包含数字的文件名
        files["number"] = self.create_text_file("file123.txt", "数字文件名")

        return files

    def create_batch_files(self, count: int = 5) -> List[Path]:
        """
        创建一批测试文件

        Args:
            count: 文件数量

        Returns:
            文件路径列表
        """
        files = []
        for i in range(count):
            filename = f"test_file_{i+1:03d}.txt"
            content = f"这是第 {i+1} 个测试文件。\n"
            files.append(self.create_text_file(filename, content))

        return files

    def cleanup(self):
        """清理所有创建的测试文件"""
        for filepath in self.created_files:
            if filepath.exists():
                filepath.unlink()

        if self.base_dir.exists():
            # 删除空目录
            try:
                self.base_dir.rmdir()
            except:
                pass  # 目录不为空，忽略

        self.created_files.clear()

    def get_all_files(self) -> List[Path]:
        """获取所有创建的测试文件"""
        return self.created_files.copy()

    def get_base_dir(self) -> Path:
        """获取测试数据基础目录"""
        return self.base_dir


# 预定义的测试数据集
class StandardTestData:
    """
    标准测试数据集

    提供常用的预定义测试数据
    """

    @staticmethod
    def get_small_text() -> str:
        """获取小文本"""
        return "你好，这是一个测试消息。"

    @staticmethod
    def get_medium_text() -> str:
        """获取中等长度文本"""
        return """
LLMChatAssistant 是一个基于大语言模型的智能运维助手。
它支持多种功能，包括智能对话、文件管理、命令执行等。
系统使用真实的智谱AI API，提供高质量的智能服务。
"""

    @staticmethod
    def get_long_text() -> str:
        """获取长文本"""
        return """
# LLMChatAssistant 系统架构

## 1. 客户端层
- CLI客户端: 基于Python的命令行界面
- 协议实现: NPLT (TCP), RDT (UDP)
- UI渲染: 使用Rich库提供美化界面

## 2. 服务器层
- HTTP服务器: 提供Web界面
- NPLT服务器: 处理聊天和控制消息
- RDT服务器: 处理文件传输

## 3. 智能体层
- Agent核心: 协调工具调用
- 工具集: 系统监控、命令执行、文件操作等
- LLM集成: 智谱AI API (glm-4-flash)

## 4. 存储层
- 文件存储: 本地文件系统
- 向量索引: ChromaDB
- 日志系统: 文件日志

## 5. 通信协议
- NPLT: 基于TCP的自定义二进制协议
- RDT: 基于UDP的可靠数据传输协议
- HTTP: 标准HTTP协议（Web界面）

## 系统特性

1. **真实测试**: 所有测试使用真实API，禁止mock
2. **安全第一**: 文件访问白名单、命令参数黑名单
3. **高可用**: 自动重连、错误恢复
4. **可扩展**: 支持多客户端类型（CLI、Web、Desktop）
"""

    @staticmethod
    def get_test_messages() -> List[Dict[str, Any]]:
        """获取测试消息列表"""
        return [
            {"role": "user", "content": "你好"},
            {"role": "user", "content": "介绍一下系统功能"},
            {"role": "user", "content": "如何上传文件？"},
            {"role": "user", "content": "查看当前会话列表"},
            {"role": "user", "content": "切换到模型glm-4.5-flash"},
        ]


# 便捷函数
def create_standard_test_files(base_dir: str = None) -> TestDataGenerator:
    """
    创建标准测试文件集

    Args:
        base_dir: 基础目录

    Returns:
        测试数据生成器实例
    """
    gen = TestDataGenerator(base_dir)

    # 创建标准文件
    gen.create_config_file()
    gen.create_python_file()
    gen.create_markdown_file()
    gen.create_json_file()

    return gen


if __name__ == "__main__":
    # 测试代码
    print("生成测试数据...")

    gen = create_standard_test_files()

    print(f"测试数据目录: {gen.get_base_dir()}")
    print(f"创建的文件数: {len(gen.get_all_files())}")

    for filepath in gen.get_all_files():
        size = filepath.stat().st_size
        print(f"  - {filepath.name}: {size} bytes")

    print("\n清理测试数据...")
    gen.cleanup()
    print("完成！")
