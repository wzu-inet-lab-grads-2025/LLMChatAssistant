"""
Agent功能验证测试模块

本模块包含Agent功能的全面验证测试，使用真实的智谱API进行测试。
"""

from tests.validation.test_framework import (
    TestCase,
    AcceptanceScenario,
    PerformanceMetrics,
    ValidationResult,
    TestResult,
    TestSuite,
)

from tests.validation.test_reporter import TestReporter

__all__ = [
    # 测试框架基础类
    "TestCase",
    "AcceptanceScenario",
    "PerformanceMetrics",
    "ValidationResult",
    "TestResult",
    "TestSuite",
    # 测试报告生成器
    "TestReporter",
]
