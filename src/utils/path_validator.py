"""
路径验证模块

提供统一的文件访问白名单验证功能。
支持路径白名单、黑名单和 glob 模式匹配。
"""

import fnmatch
import os
from pathlib import Path
from typing import Optional


class PathValidator:
    """路径验证器"""

    def __init__(self, config):
        """初始化路径验证器

        Args:
            config: FileAccessConfig 配置对象
        """
        self.allowed_paths = config.allowed_paths
        self.forbidden_patterns = config.forbidden_patterns
        self.max_file_size = config.max_file_size

    def is_allowed(self, file_path: str) -> tuple[bool, str]:
        """检查路径是否在允许范围内

        Args:
            file_path: 文件路径（相对或绝对）

        Returns:
            (是否允许, 错误消息)
        """
        # 1. 规范化路径
        try:
            normalized_path = os.path.realpath(file_path)
            if not os.path.exists(normalized_path):
                # 文件不存在，检查父目录是否在白名单中
                normalized_path = os.path.realpath(os.path.dirname(file_path))
        except Exception as e:
            return False, f"路径验证失败: {str(e)}"

        # 2. 检查黑名单（优先级更高）
        for pattern in self.forbidden_patterns:
            if self._match_pattern(normalized_path, pattern):
                return False, f"路径匹配禁止模式: {pattern}"

        # 3. 检查白名单
        for allowed in self.allowed_paths:
            if self._match_allowed(normalized_path, allowed):
                # 4. 额外检查：文件大小
                if os.path.isfile(normalized_path):
                    file_size = os.path.getsize(normalized_path)
                    if file_size > self.max_file_size:
                        return False, f"文件过大 ({file_size} > {self.max_file_size} 字节)"

                return True, ""

        # 不在白名单中
        return False, f"路径不在白名单中: {file_path}"

    def _match_allowed(self, path: str, pattern: str) -> bool:
        """检查路径是否匹配允许模式

        Args:
            path: 规范化的绝对路径
            pattern: 允许的模式（可能包含 glob 通配符）

        Returns:
            是否匹配
        """
        # 处理 glob 模式
        if '*' in pattern or '?' in pattern or '[' in pattern:
            # 获取目录部分
            pattern_dir = os.path.dirname(pattern)
            if not pattern_dir:
                pattern_dir = '.'

            pattern_dir_real = os.path.realpath(pattern_dir)
            path_dir = os.path.dirname(path)

            # 检查目录是否匹配
            if path_dir.startswith(pattern_dir_real):
                # 检查文件名是否匹配 glob 模式
                filename = os.path.basename(path)
                pattern_basename = os.path.basename(pattern)

                if fnmatch.fnmatch(filename, pattern_basename):
                    return True
            return False

        # 处理普通路径
        else:
            pattern_real = os.path.realpath(pattern)
            # 检查是否在允许的目录下（或就是该路径）
            return path == pattern_real or path.startswith(pattern_real + os.sep)

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """检查路径是否匹配黑名单模式

        Args:
            path: 规范化的绝对路径
            pattern: 黑名单模式

        Returns:
            是否匹配
        """
        # 精确匹配
        if path == os.path.realpath(pattern):
            return True

        # Glob 模式匹配
        if '*' in pattern or '?' in pattern:
            return fnmatch.fnmatch(path, pattern)

        # 路径前缀匹配（用于目录模式如 "*/.ssh/*"）
        if '/*' in pattern:
            prefix = pattern.replace('/*', '')
            if path.startswith(os.path.realpath(prefix)):
                return True

        return False

    def expand_glob(self, pattern: str, max_files: int = 100) -> list[str]:
        """展开 glob 模式并返回匹配的文件

        Args:
            pattern: glob 模式（必须在白名单中）
            max_files: 最大返回文件数

        Returns:
            匹配的文件路径列表

        Raises:
            PermissionError: 如果模式不在白名单中
        """
        # 先验证模式是否在白名单中
        pattern_allowed = False
        for allowed in self.allowed_paths:
            if pattern.startswith(allowed.rstrip('*')) or allowed in pattern:
                pattern_allowed = True
                break

        if not pattern_allowed:
            raise PermissionError(f"Glob 模式不在白名单中: {pattern}")

        # 展开 glob
        import glob as glob_module
        matches = glob_module.glob(pattern, recursive=True)

        # 验证每个匹配的文件
        valid_files = []
        for match in matches[:max_files]:
            allowed, _ = self.is_allowed(match)
            if allowed and os.path.isfile(match):
                valid_files.append(match)

        return valid_files

    def get_allowed_extensions(self, path: str) -> list[str]:
        """获取路径允许的文件扩展名

        Args:
            path: 路径模式

        Returns:
            允许的扩展名列表（如 ['.log', '.txt']）
        """
        for allowed in self.allowed_paths:
            if path.startswith(allowed.rstrip('*')):
                # 提取扩展名
                if '.' in allowed:
                    ext = allowed[allowed.rindex('.'):]
                    return [ext]
        return []  # 允许所有扩展名

    def validate_content_type(self, file_path: str) -> bool:
        """验证文件内容类型（仅允许文本文件）

        Args:
            file_path: 文件路径

        Returns:
            是否为文本文件
        """
        if not os.path.isfile(file_path):
            return False

        # 检查文件扩展名
        text_extensions = {
            '.txt', '.log', '.md', '.py', '.js', '.json', '.yaml', '.yml',
            '.xml', '.html', '.css', '.sh', '.bash', '.zsh', '.conf', '.cfg',
            '.ini', '.toml', '.env', '.gitignore', '.dockerignore'
        }

        ext = os.path.splitext(file_path)[1].lower()
        if ext in text_extensions:
            return True

        # 检查文件内容（前 1024 字节）
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                # 检查是否为二进制文件
                if b'\x00' in chunk:
                    return False
                # 尝试解码为 UTF-8
                try:
                    chunk.decode('utf-8')
                    return True
                except UnicodeDecodeError:
                    return False
        except Exception:
            return False

    def sanitize_path(self, path: str) -> str:
        """清理和规范化路径

        Args:
            path: 输入路径

        Returns:
            规范化后的路径
        """
        # 移除危险字符
        path = path.replace('..', '').replace('~', '')

        # 规范化路径
        normalized = os.path.realpath(path)

        return normalized


# 全局路径验证器实例
_validator: Optional[PathValidator] = None


def get_path_validator(config=None) -> PathValidator:
    """获取全局路径验证器实例

    Args:
        config: FileAccessConfig 配置对象（首次调用时需要）

    Returns:
        PathValidator 实例
    """
    global _validator
    if _validator is None:
        if config is None:
            raise ValueError("PathValidator 未初始化，需要提供 config 参数")
        _validator = PathValidator(config)
    return _validator
