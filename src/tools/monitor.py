"""
系统监控工具模块

提供系统资源监控功能（CPU、内存、磁盘）。
遵循章程：真实实现，不允许虚假实现或占位符
"""

import os
import shutil
from dataclasses import dataclass
from typing import Dict

from .base import Tool, ToolExecutionResult


@dataclass
class MonitorTool(Tool):
    """系统监控工具"""

    name: str = "sys_monitor"
    description: str = "监控系统资源使用情况（CPU、内存、磁盘）"
    timeout: int = 5

    def execute(self, metric: str = "all", **kwargs) -> ToolExecutionResult:
        """执行监控

        Args:
            metric: 监控指标（'cpu', 'memory', 'disk', 'all'）
            **kwargs: 其他参数

        Returns:
            ToolExecutionResult: 监控结果
        """
        try:
            if metric == "cpu" or metric == "all":
                cpu_info = self._get_cpu_info()
                if metric == "cpu":
                    return ToolExecutionResult(
                        success=True,
                        output=cpu_info
                    )

            if metric == "memory" or metric == "all":
                memory_info = self._get_memory_info()
                if metric == "memory":
                    return ToolExecutionResult(
                        success=True,
                        output=memory_info
                    )

            if metric == "disk" or metric == "all":
                disk_info = self._get_disk_info()
                if metric == "disk":
                    return ToolExecutionResult(
                        success=True,
                        output=disk_info
                    )

            # 返回所有信息
            all_info = f"""系统监控结果:

{cpu_info}

{memory_info}

{disk_info}
"""
            return ToolExecutionResult(
                success=True,
                output=all_info.strip()
            )

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"监控失败: {str(e)}"
            )

    def _get_cpu_info(self) -> str:
        """获取 CPU 信息"""
        try:
            # 读取 CPU 负载
            load1, load5, load15 = os.getloadavg()

            # CPU 核心数
            cpu_count = os.cpu_count()

            # 计算 CPU 使用率（基于负载）
            cpu_usage = min(100, (load1 / cpu_count * 100) if cpu_count else 0)

            return f"""CPU 使用率:
  • 使用率: {cpu_usage:.1f}%
  • 负载 (1min/5min/15min): {load1:.2f} / {load5:.2f} / {load15:.2f}
  • 核心数: {cpu_count}"""
        except Exception as e:
            return f"CPU 信息获取失败: {str(e)}"

    def _get_memory_info(self) -> str:
        """获取内存信息"""
        try:
            # 使用 free 命令获取内存信息
            import subprocess
            result = subprocess.run(
                ['free', '-b'],
                capture_output=True,
                text=True,
                check=True
            )

            # 解析输出
            lines = result.stdout.strip().split('\n')
            mem_line = lines[1].split()

            total = int(mem_line[1])
            used = int(mem_line[2])
            available = int(mem_line[6])

            # 转换为 GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            available_gb = available / (1024**3)
            usage_percent = (used / total * 100) if total > 0 else 0

            return f"""内存使用:
  • 总内存: {total_gb:.2f} GB
  • 已使用: {used_gb:.2f} GB ({usage_percent:.1f}%)
  • 可用: {available_gb:.2f} GB"""
        except Exception as e:
            return f"内存信息获取失败: {str(e)}"

    def _get_disk_info(self) -> str:
        """获取磁盘信息"""
        try:
            # 获取根分区磁盘使用情况
            total, used, free = shutil.disk_usage("/")

            # 转换为 GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            usage_percent = (used / total * 100) if total > 0 else 0

            return f"""磁盘使用:
  • 总容量: {total_gb:.2f} GB
  • 已使用: {used_gb:.2f} GB ({usage_percent:.1f}%)
  • 可用: {free_gb:.2f} GB"""
        except Exception as e:
            return f"磁盘信息获取失败: {str(e)}"

    def get_help(self) -> str:
        """获取帮助信息"""
        return """
系统监控工具 - 支持的监控指标:

  cpu    - CPU 使用率和负载
  memory - 内存使用情况
  disk   - 磁盘使用情况
  all    - 所有监控指标（默认）

使用示例:
  - 监控所有: {'metric': 'all'}
  - 监控 CPU: {'metric': 'cpu'}
  - 监控内存: {'metric': 'memory'}
  - 监控磁盘: {'metric': 'disk'}
"""
