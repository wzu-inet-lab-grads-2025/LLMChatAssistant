# 研究文档: 重构后系统验证

**功能**: 重构后系统验证
**日期**: 2026-01-02
**状态**: 阶段 0 完成

## 概述

本文档记录了对重构后系统验证功能的技术研究和决策。主要关注测试策略、工具选择和实施方法。

## 技术决策

### 决策 1: 测试框架选择

**选择**: pytest

**理由**:
- Python标准测试框架，生态成熟
- 支持异步测试（pytest-asyncio）
- 强大的fixture系统，便于共享测试资源
- 丰富的插件生态（pytest-cov、pytest-html等）
- 项目已有pytest基础设施（tests/目录已使用pytest）
- 支持参数化测试和标记（pytest.mark）

**替代方案**:
- unittest: 功能过于基础，缺乏现代特性
- nose2: 已停止维护，社区不活跃

### 决策 2: 测试组织策略

**选择**: 按功能模块组织（tests/validation/目录）

**理由**:
- 每个用户故事对应一个测试文件，便于定位和维护
- 优先级清晰（P1、P2、P3对应不同文件）
- 支持按优先级选择性执行测试
- 与现有测试结构兼容（tests/validation/已存在）

**测试文件映射**:
- test_agent.py → Agent功能验证（P1，优先级最高）
- test_data_transmission.py → 数据传输验证（P1）
- test_file_operations.py → 文件操作验证（P2）
- test_retrieval.py → 检索功能验证（P2）
- test_history.py → 历史记录验证（P3）

### 决策 3: 真实API测试策略

**选择**: 必须使用真实智谱API，禁止mock

**理由**:
- 章程强制要求（测试真实性原则）
- 真实API测试确保实际环境可用性
- 发现网络、协议、格式等集成问题
- 智谱提供免费模型（glm-4-flash），无额外成本
- 现有conftest.py已验证API key配置

**实施细节**:
- 使用ZHIPU_API_KEY环境变量配置
- conftest.py在pytest_configure中验证API key
- 测试失败时不允许提交代码
- API调用使用免费模型（glm-4-flash或glm-4.5-flash）

### 决策 4: 测试覆盖率要求

**选择**: 每个功能至少5个独立测试样例

**理由**:
- 规范要求（FR-015b）
- 覆盖正常场景和边界情况
- 提供足够的统计显著性
- 平衡测试成本和覆盖率

**测试场景设计**:
- 正常场景（Happy Path）：2-3个样例
- 边界情况：1-2个样例
- 错误场景：1个样例

### 决策 5: 异步测试支持

**选择**: 使用pytest-asyncio

**理由**:
- 现有代码大量使用async/await
- server/agent.py、server/nplt_server.py等都是异步的
- pytest-asyncio提供原生async测试支持
- 现有conftest.py已包含async fixtures（fresh_agent）

**实施细节**:
- 测试函数使用@pytest.mark.asyncio标记
- 使用async def定义测试函数
- 使用await调用异步方法

### 决策 6: 测试报告生成

**选择**: 使用pytest-html和自定义JSON报告

**理由**:
- HTML报告提供可视化测试结果
- JSON报告便于CI/CD集成和自动化分析
- 支持详细记录每个测试的执行状态、持续时间、错误信息

**报告内容**:
- 通过/失败状态
- 执行时间
- 错误堆栈（如失败）
- 测试数据（输入、输出、预期结果）

## 现有代码分析

### 后端架构（server/）

- **agent.py**: ReActAgent实现，使用ZhipuProvider进行LLM调用
- **nplt_server.py**: NPLT协议服务器，处理客户端连接
- **rdt_server.py**: RDT文件传输服务器
- **http_server.py**: HTTP服务器（Web客户端）
- **main.py**: 服务器入口，整合所有协议

**关键依赖**:
- server/llm/zhipu.py - 智谱AI集成
- server/tools/ - 工具实现（semantic_search、file_download等）
- server/storage/ - 存储模块（history、vector_store、index_manager）

### 前端架构（clients/cli/）

- **main.py**: CLI客户端入口
- **nplt_client.py**: NPLT协议客户端
- **rdt_client.py**: RDT文件传输客户端
- **ui.py**: 用户界面实现
- **client_api.py**: 客户端API封装

### 现有测试结构

- **tests/validation/features/**: 功能测试（12个测试文件）
- **tests/validation/e2e/**: 端到端测试
- **tests/integration/**: 集成测试（agent、client_server、rdt等）
- **tests/unit/**: 单元测试（llm、storage、tools）
- **tests/contract/**: 契约测试（nplt、rdt协议）

**现有conftest.py特点**:
- 验证ZHIPU_API_KEY环境变量
- 提供fresh_agent fixture（创建新Agent实例）
- 提供fresh_history fixture（创建新对话历史）
- 自动清理测试环境

## 测试策略

### P1功能测试（Agent功能、数据传输）

**test_agent.py** (至少5个测试样例):
1. 简单对话请求 - 验证基本LLM调用
2. 工具调用请求 - 验证Agent正确调用semantic_search、file_download等工具
3. 多步推理请求 - 验证Agent的复杂推理能力
4. 错误输入处理 - 验证错误消息返回而非崩溃
5. 流式输出 - 验证流式响应正确接收

**test_data_transmission.py** (至少5个测试样例):
1. 文本响应传输 - 验证基本文本响应正确显示
2. 特殊字符处理 - 验证中文、标点、换行符等
3. 工具执行结果解析 - 验证工具返回的JSON结构正确解析
4. 错误信息显示 - 验证错误类型识别和友好提示
5. 大数据量传输 - 验证无数据截断

### P2功能测试（文件操作、检索）

**test_file_operations.py** (至少6个测试样例):
1. 文本文件上传下载 - 验证内容完整性
2. 二进制文件上传下载 - 验证数据完整性
3. 大文件处理 - 验证成功或明确错误
4. 不允许的文件类型 - 验证错误提示
5. 网络中断处理 - 验证错误检测和报告
6. 文件内容校验 - 验证MD5/SHA校验和

**test_retrieval.py** (至少5个测试样例):
1. 关键词搜索 - 验证返回包含关键词的文件列表
2. 语义搜索 - 验证返回相关文件并按相关度排序
3. 不存在关键词 - 验证返回空结果而非错误
4. 模糊查询 - 验证部分匹配结果
5. 索引使用 - 验证使用已有索引而不重新索引

### P3功能测试（历史记录）

**test_history.py** (至少3个测试样例):
1. 历史记录保存和查询 - 验证所有历史对话按时间排序
2. 特定会话历史 - 验证特定会话的完整对话内容
3. 服务重启后持久化 - 验证历史记录仍然存在

## 风险和挑战

### 风险 1: API调用成本和速度

**描述**: 每个测试都需要调用真实LLM API，可能增加测试时间和API配额消耗。

**缓解措施**:
- 使用免费模型（glm-4-flash或glm-4.5-flash）
- 优化测试用例，避免冗余API调用
- 使用pytest标记分离快速测试和慢速测试
- CI/CD中可以选择性运行快速测试

### 风险 2: 网络依赖

**描述**: 测试依赖外部API服务，网络问题可能导致测试不稳定。

**缓解措施**:
- 添加合理的超时设置（15秒）
- 实现重试机制（最多3次）
- 记录详细的网络错误日志
- CI/CD中提供网络检查机制

### 风险 3: 测试环境隔离

**描述**: 并发测试可能共享资源（如storage/目录），导致测试干扰。

**缓解措施**:
- 每个测试使用唯一的session_id（UUID）
- conftest.py自动清理测试环境（clean_test_environment fixture）
- 测试文件使用独立的测试存储目录
- 使用pytest-xdist实现进程隔离（如需要）

## 下一步行动

### 阶段 1: 设计

1. **生成data-model.md**: 定义测试用例结构、验证报告格式
2. **生成contracts/**: 定义测试API接口规范（可选）
3. **生成quickstart.md**: 编写测试执行指南

### 阶段 2: 任务分解（由/speckit.tasks完成）

- 分解为可执行的任务
- 定义依赖关系
- 按优先级排序

## 附录: 技术依赖清单

- **pytest**: 核心测试框架
- **pytest-asyncio**: 异步测试支持
- **pytest-html**: HTML测试报告
- **pytest-cov**: 代码覆盖率（可选）
- **zai-sdk**: 智谱AI官方SDK
- **python-dotenv**: 环境变量加载（.env文件）

## 参考资料

- [pytest文档](https://docs.pytest.org/)
- [pytest-asyncio文档](https://pytest-asyncio.readthedocs.io/)
- [智谱AI开放平台](https://open.bigmodel.cn/)
- 项目章程: `.specify/memory/constitution.md`
- 功能规范: `specs/001-refactor-validation/spec.md`
