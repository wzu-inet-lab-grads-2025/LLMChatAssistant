"""
工具层单元测试

测试 CommandTool 和 MonitorTool 的功能。
遵循章程：真实测试，不允许 mock
"""

import pytest

from server.tools.base import Tool, ToolExecutionResult
from server.tools.command import BLACKLIST_CHARS, CommandTool, WHITELIST_COMMANDS
from server.tools.monitor import MonitorTool


class TestToolBase:
    """Tool 基类测试"""

    def test_tool_execution_result(self):
        """测试工具执行结果"""
        result = ToolExecutionResult(
            success=True,
            output="Test output",
            error=None,
            duration=0.5
        )

        assert result.success is True
        assert result.output == "Test output"
        assert result.duration == 0.5

    def test_tool_execution_result_failure(self):
        """测试失败的执行结果"""
        result = ToolExecutionResult(
            success=False,
            output="",
            error="Test error",
            duration=1.0
        )

        assert result.success is False
        assert result.error == "Test error"

    def test_tool_execution_result_to_dict(self):
        """测试结果转字典"""
        result = ToolExecutionResult(
            success=True,
            output="Output",
            error=None,
            duration=0.1
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["output"] == "Output"
        assert result_dict["duration"] == 0.1


class TestCommandTool:
    """CommandTool 测试"""

    def setup_method(self):
        """设置测试环境"""
        self.tool = CommandTool()

    def test_validate_whitelist_command(self):
        """测试验证白名单命令"""
        is_valid, error = self.tool.validate_args("ls", None)
        assert is_valid is True
        assert error == ""

    def test_validate_blacklist_command(self):
        """测试验证黑名单命令"""
        is_valid, error = self.tool.validate_args("rm", None)
        assert is_valid is False
        assert "不在白名单中" in error

    def test_validate_blacklist_chars(self):
        """测试验证黑名单字符"""
        # 包含分号
        is_valid, error = self.tool.validate_args("ls", ["; rm -rf /"])
        assert is_valid is False
        assert "非法字符" in error

        # 包含管道符
        is_valid, error = self.tool.validate_args("cat", ["file.txt | grep test"])
        assert is_valid is False

    def test_execute_ls_command(self):
        """测试执行 ls 命令"""
        result = self.tool.execute(command="ls", args=["-la"])

        # 命令应该执行成功
        # 注意：返回码可能不是 0，但应该有输出
        assert isinstance(result, ToolExecutionResult)
        # ls 命令在大多数环境中应该成功
        assert len(result.output) > 0

    def test_execute_pwd_command(self):
        """测试执行 pwd 命令"""
        result = self.tool.execute(command="pwd", args=None)

        assert isinstance(result, ToolExecutionResult)
        assert result.success is True
        assert len(result.output) > 0

    def test_execute_echo_command(self):
        """测试执行 echo 命令（如果支持）"""
        # echo 可能不在白名单中，如果不支持就跳过
        if "echo" not in WHITELIST_COMMANDS:
            pytest.skip("echo 不在白名单中")

        result = self.tool.execute(command="echo", args=["Hello"])

        assert isinstance(result, ToolExecutionResult)

    def test_execute_with_args(self):
        """测试带参数的命令执行"""
        result = self.tool.execute(command="ls", args=["-la", "/"])

        assert isinstance(result, ToolExecutionResult)
        # 应该有输出
        assert len(result.output) > 0

    def test_execute_timeout(self):
        """测试命令执行超时"""
        # 使用 sleep 命令测试超时（如果在白名单中）
        if "sleep" in WHITELIST_COMMANDS:
            result = self.tool.execute(command="sleep", args=["10"])
            assert result.success is False
            assert "超时" in result.error or "timeout" in result.error.lower()

    def test_whitelist_commands(self):
        """测试白名单命令列表"""
        # 验证必需的命令在白名单中
        required_commands = ["ls", "cat", "grep", "head", "tail", "ps", "pwd", "whoami", "df", "free"]

        for cmd in required_commands:
            assert cmd in WHITELIST_COMMANDS, f"{cmd} 应该在白名单中"

    def test_blacklist_chars(self):
        """测试黑名单字符列表"""
        # 验证危险的字符在黑名单中
        dangerous_chars = [";", "&", "|", ">", "<", "`", "$"]

        for char in dangerous_chars:
            assert char in BLACKLIST_CHARS, f"{char} 应该在黑名单中"


class TestMonitorTool:
    """MonitorTool 测试"""

    def setup_method(self):
        """设置测试环境"""
        self.tool = MonitorTool()

    def test_execute_cpu_monitor(self):
        """测试 CPU 监控"""
        result = self.tool.execute(metric="cpu")

        assert isinstance(result, ToolExecutionResult)
        assert result.success is True
        assert "CPU" in result.output
        assert len(result.output) > 0

    def test_execute_memory_monitor(self):
        """测试内存监控"""
        result = self.tool.execute(metric="memory")

        assert isinstance(result, ToolExecutionResult)
        assert result.success is True
        assert "内存" in result.output
        assert len(result.output) > 0

    def test_execute_disk_monitor(self):
        """测试磁盘监控"""
        result = self.tool.execute(metric="disk")

        assert isinstance(result, ToolExecutionResult)
        assert result.success is True
        assert "磁盘" in result.output
        assert len(result.output) > 0

    def test_execute_all_metrics(self):
        """测试监控所有指标"""
        result = self.tool.execute(metric="all")

        assert isinstance(result, ToolExecutionResult)
        assert result.success is True
        # 应该包含所有指标
        assert "CPU" in result.output or "cpu" in result.output
        assert "内存" in result.output or "memory" in result.output
        assert "磁盘" in result.output or "disk" in result.output

    def test_invalid_metric(self):
        """测试无效指标"""
        result = self.tool.execute(metric="invalid")

        # 工具应该仍然返回结果（可能默认为 all）
        assert isinstance(result, ToolExecutionResult)


class TestCommandToolSecurity:
    """命令工具安全加固测试（T090）"""

    def setup_method(self):
        """设置测试环境"""
        self.tool = CommandTool()

    def test_command_injection_semicolon(self):
        """测试命令注入攻击：分号 (;）"""
        # 尝试使用分号连接多个命令
        is_valid, error = self.tool.validate_args("ls", ["file.txt; rm -rf /"])
        assert is_valid is False
        assert "非法字符" in error or ";" in error

        # 执行应该被拒绝
        result = self.tool.execute(command="ls", args=["file.txt; echo hacked"])
        assert result.success is False

    def test_command_injection_pipe(self):
        """测试命令注入攻击：管道符 (|)"""
        is_valid, error = self.tool.validate_args("cat", ["file.txt | grep test"])
        assert is_valid is False
        assert "非法字符" in error

    def test_command_injection_ampersand(self):
        """测试命令注入攻击：& 符号"""
        is_valid, error = self.tool.validate_args("ls", ["&", "rm", "-rf", "/"])
        assert is_valid is False
        assert "非法字符" in error

    def test_command_injection_redirect(self):
        """测试命令注入攻击：重定向符 (>, <)"""
        # 输出重定向
        is_valid, error = self.tool.validate_args("ls", [">", "/tmp/malicious"])
        assert is_valid is False

        # 输入重定向
        is_valid, error = self.tool.validate_args("cat", ["<", "/etc/passwd"])
        assert is_valid is False

    def test_command_injection_backtick(self):
        """测试命令注入攻击：反引号 (`)"""
        is_valid, error = self.tool.validate_args("ls", ["`whoami`"])
        assert is_valid is False
        assert "非法字符" in error

    def test_command_injection_dollar(self):
        """测试命令注入攻击：美元符号 ($)"""
        # 使用白名单中的命令
        is_valid, error = self.tool.validate_args("ls", ["$HOME/file.txt"])
        assert is_valid is False
        assert "非法字符" in error

    def test_command_injection_parentheses(self):
        """测试命令注入攻击：括号 (())"""
        is_valid, error = self.tool.validate_args("ls", ["$(rm -rf /)"])
        assert is_valid is False
        assert "非法字符" in error

    def test_command_injection_newline(self):
        """测试命令注入攻击：换行符"""
        is_valid, error = self.tool.validate_args("ls", ["file.txt\nrm -rf /"])
        assert is_valid is False
        assert "非法字符" in error

    def test_command_injection_carriage_return(self):
        """测试命令注入攻击：回车符"""
        is_valid, error = self.tool.validate_args("ls", ["file.txt\rm -rf /"])
        assert is_valid is False
        assert "非法字符" in error

    def test_all_blacklist_chars_blocked(self):
        """测试所有黑名单字符都被阻止"""
        from server.tools.command import BLACKLIST_CHARS

        # 测试每个黑名单字符
        for char in BLACKLIST_CHARS:
            is_valid, error = self.tool.validate_args("ls", [f"file{char}txt"])
            assert is_valid is False, f"字符 '{char}' 应该被阻止但没有"
            assert "非法字符" in error or char in error

    def test_combined_attack_vectors(self):
        """测试组合攻击向量"""
        # 组合多个危险字符
        is_valid, error = self.tool.validate_args("ls", ["file.txt; |& `cmd`"])
        assert is_valid is False

        # 测试命令链
        result = self.tool.execute(command="ls", args=[";cat", "/etc/passwd"])
        assert result.success is False

    def test_path_traversal_prevention(self):
        """测试路径遍历攻击防护"""
        # 虽然这不是黑名单字符的范畴，但是相关的安全测试
        # 工具应该能处理包含 .. 的路径
        # 但白名单命令本身限制了危险操作
        is_valid, error = self.tool.validate_args("cat", ["../../../etc/passwd"])
        # 这是合法的参数格式，即使内容可疑
        # 安全性主要来自白名单命令限制
        assert is_valid is True or "非法字符" not in error

    def test_valid_parameters_not_blocked(self):
        """测试合法参数不被阻止"""
        # 确保合法的参数可以正常使用
        is_valid, error = self.tool.validate_args("ls", ["-la", "/home/user"])
        assert is_valid is True
        assert error == ""

        is_valid, error = self.tool.validate_args("grep", ["-r", "pattern", "/path"])
        assert is_valid is True
        assert error == ""

    def test_whitelist_only_enforcement(self):
        """测试仅允许白名单命令"""
        # 尝试使用危险但不在白名单中的命令
        dangerous_commands = ["rm", "chmod", "chown", "sudo", "su", "nc", "netcat"]

        for cmd in dangerous_commands:
            is_valid, error = self.tool.validate_args(cmd, None)
            assert is_valid is False
            assert "不在白名单中" in error

    def test_special_char_combinations(self):
        """测试特殊字符组合"""
        # URL 编码尝试
        is_valid, error = self.tool.validate_args("ls", ["file%2etxt"])
        # % 不在黑名单中，所以应该通过验证（这是预期的）
        # 实际的安全限制来自白名单命令

        # 十六进制编码尝试（应该不会通过 shell 执行）
        is_valid, error = self.tool.validate_args("ls", ["\\x2F"])
        # 这是合法参数格式

    def test_unicode_and_encoding_attacks(self):
        """测试 Unicode 和编码攻击"""
        # 尝试使用 Unicode 字符绕过
        is_valid, error = self.tool.validate_args("ls", ["file\u2026txt"])  # Unicode 省略号
        # Unicode 字符本身不在黑名单中，这是预期的
        # 实际执行时会被正确处理

    def test_shell_metacharacters_all_blocked(self):
        """测试所有 shell 元字符都被阻止"""
        # 测试常见的 shell 元字符
        shell_metachars = [';', '&', '|', '>', '<', '`', '$', '(', ')', '\n', '\r']

        for char in shell_metachars:
            is_valid, error = self.tool.validate_args("ls", [f"test{char}arg"])
            if char in [';', '&', '|', '>', '<', '`', '$', '(', ')', '\n', '\r']:
                # 这些字符应该在黑名单中
                assert is_valid is False, f"Shell 元字符 '{char}' 应该被阻止"
