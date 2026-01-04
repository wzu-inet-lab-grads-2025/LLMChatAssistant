# 技术设计文档

## 上下文

### 当前状态
- 后端功能已实现：ReAct Agent、工具链、聊天、文件传输、会话管理等
- 现有测试文件均为老旧版本，不反映当前实现
- 缺乏全面的集成测试和端到端测试
- 未验证使用真实智谱API的功能正确性
- 智谱glm-4-flash API完全免费，API Key在.env文件中

### 目标
- 删除所有老旧测试，建立全新的测试套件
- 全面审阅后端功能实现，验证正确性
- 重点测试Agent意图识别和多工具协作能力
- 验证后端与前端通信、数据持久化、上下文管理等关键环节
- 使用真实智谱API（glm-4-flash）进行端到端测试
- **优化agent.py的system_prompt，通过多次测试找到最佳版本**
- 生成**极其详细**的测试报告
- **达到至少90%的测试覆盖率**

### 约束
- 必须使用真实的智谱API（glm-4-flash，免费）
- **测试覆盖率目标：≥ 90%**
- 每个功能至少5个测试样例
- 测试报告必须包含尽可能详细的信息（输入、工具调用、API请求/响应、输出等）
- 不能破坏现有代码实现
- **允许优化agent.py的system_prompt**
- 不需要Mock API（直接使用真实API）

## 目标 / 非目标

### 目标
1. **全面审阅后端功能实现（覆盖率≥90%）**
   - 验证ReAct Agent的推理-行动循环
   - 验证所有工具（5个）的正确性
   - 验证聊天功能和流式输出
   - 验证文件传输和索引
   - 验证会话管理和历史持久化
   - **覆盖所有代码分支和边界条件**

2. **重点测试Agent智能能力**
   - 意图识别准确率（目标：≥90%）
   - 多工具协作成功率（目标：≥85%）
   - 上下文管理正确性
   - 错误处理和降级能力

3. **优化Agent的system_prompt**
   - 通过多轮测试找到最佳prompt版本
   - 提高意图识别准确率
   - 提高多工具协作成功率
   - 将最优prompt更新到agent.py

4. **验证数据流和协议**
   - 后端→前端消息传递（NPLT协议）
   - 历史记录持久化（磁盘存储）
   - 文件上传、存储、索引流程
   - 上下文传递（session对象、conversation_history）

5. **生成极其详细的测试报告**
   - 每个测试样例的完整记录（包括API请求/响应原始数据）
   - 问题清单和改进建议
   - 性能指标和覆盖率统计
   - **多个版本的prompt对比**

### 非目标
- 不修改后端核心逻辑（仅优化system_prompt）
- 不进行性能优化
- 不添加新功能
- 不修改NPLT和RDT协议
- 不实现Mock API（直接使用真实API）

## 决策

### 决策1：仅使用真实智谱API（无Mock）

**选择：仅使用真实智谱API（glm-4-flash）**

**理由：**
- glm-4-flash完全免费，无成本顾虑
- 真实API才能验证Agent的实际表现
- 无需维护Mock代码，简化测试架构
- API Key在.env文件中，配置简单

**API使用情况预估：**
- 每个测试样例约2-5次API调用（思考+工具调用决策+最终生成）
- 总测试样例约200-300个
- 总API调用约1000-1500次
- glm-4-flash免费额度完全足够

### 决策2：测试架构设计

**选择：以集成测试为主（≥70%），单元测试为辅（20-30%），少量端到端测试（<10%）**

**理由：**
- 集成测试能验证工具链和Agent协作，覆盖主要功能
- 单元测试用于测试边界条件和异常处理
- 端到端测试验证真实用户场景
- 组合使用能达到90%+覆盖率

**分布策略：**
- 集成测试：70-75%（重点）
- 单元测试：20-25%（边界条件）
- 端到端测试：5-10%（验证通信协议）

### 决策3：测试覆盖率目标90%

**覆盖率要求：**
- **总体覆盖率：≥ 90%**
- **关键模块覆盖率：**
  - agent.py：≥ 95%
  - tools/*.py：≥ 90%（每个工具）
  - llm/zhipu.py：≥ 85%
  - nplt_server.py：≥ 90%
  - storage/*.py：≥ 90%

**如何达到90%：**
1. 使用pytest-cov实时监控覆盖率
2. 针对未覆盖的代码分支补充测试
3. 特别关注异常处理分支
4. 测试所有工具的组合场景

### 决策4：测试报告详细程度

**选择：尽可能详细**

**报告内容包括：**
1. **测试样例完整记录**
   - 测试输入
   - API请求原始数据（messages, temperature等）
   - API响应原始数据（choices, usage等）
   - 工具调用决策过程（第1轮、第2轮...）
   - 每个工具的调用参数和返回结果
   - 传递给前端的消息序列（完整NPLT消息）
   - 保存到磁盘的历史记录（完整JSON）
   - 测试结果（通过/失败/部分通过）

2. **统计数据**
   - 总体统计（样例数、通过率、失败率）
   - 意图识别准确率（按场景分类）
   - 多工具协作成功率
   - 测试覆盖率（按模块）
   - 性能指标（响应时间、API使用量）

3. **问题分析**
   - 问题清单（按严重程度）
   - 根因分析
   - 复现步骤
   - 改进建议

4. **Prompt优化记录**
   - 测试的prompt版本
   - 每个版本的测试结果对比
   - 最终选择的prompt及理由

### 决策5：Agent的system_prompt优化策略

**选择：多轮测试迭代优化**

**优化流程：**
1. **第1轮测试**：使用当前prompt
   - 运行所有意图识别和多工具协作测试
   - 记录准确率和错误案例
   - 分析错误原因

2. **第2轮测试**：优化prompt v2
   - 根据第1轮结果优化prompt
   - 重点改进易混淆的场景
   - 重新运行测试，对比结果

3. **第3轮测试**：微调prompt v3（如果需要）
   - 针对剩余问题微调
   - 验证改进效果

4. **最终选择**：选择效果最好的prompt版本
   - 更新到agent.py
   - 在测试报告中说明选择理由

**优化重点：**
- 提高意图识别准确率（目标≥90%）
- 提高多工具协作成功率（目标≥85%）
- 减少误识别（如将"介绍df命令"误判为需要执行df）

**测试方法：**
- 每个prompt版本运行完整的意图识别测试集（15个场景 × 5样例 = 75个测试）
- 每个prompt版本运行完整的多工具协作测试集（5个场景 × 5样例 = 25个测试）
- 对比不同版本的准确率和成功率
- 分析具体错误案例

### 决策6：测试数据管理

**选择：使用fixtures + 测试数据目录 + 随机生成**

**实施策略：**
- 固定测试数据：配置文件、文档等（tests/fixtures/data/）
- 随机生成数据：用户输入、参数组合等（增加覆盖面）
- pytest fixtures管理测试环境和依赖

**测试数据准备：**
```
tests/fixtures/data/
├── config_files/
│   ├── app.yaml
│   ├── database.yaml
│   └── server.conf
├── log_files/
│   ├── application.log
│   ├── error.log
│   └── access.log
├── documents/
│   ├── README.md
│   ├── API.md
│   └── DESIGN.md
└── uploads/
    ├── test_file.txt
    ├── test_data.json
    └── test_image.png
```

## 技术架构

### 测试套件架构

```
tests/
├── fixtures/
│   ├── data/                      # 测试数据
│   ├── conftest.py                # pytest配置
│   └── helpers/
│       ├── client.py              # 模拟NPLT客户端
│       ├── assertions.py          # 测试断言
│       ├── coverage.py            # 覆盖率辅助
│       └── report.py              # 报告生成器
├── unit/                          # 单元测试（20-30%）
│   ├── test_tools.py              # 工具单元测试
│   ├── test_storage.py            # 存储单元测试
│   ├── test_llm.py                # LLM接口测试
│   └── test_protocol.py           # 协议编解码测试
├── integration/                   # 集成测试（70-75%）
│   ├── test_agent_core.py         # Agent核心测试
│   ├── test_agent_intent.py       # 意图识别测试（重点）
│   ├── test_agent_multi_tool.py   # 多工具协作测试（重点）
│   ├── test_agent_prompt_opt.py   # Prompt优化测试（重点）
│   ├── test_tool_command.py       # command_executor测试
│   ├── test_tool_monitor.py       # sys_monitor测试
│   ├── test_tool_semantic_search.py # semantic_search测试
│   ├── test_tool_file_upload.py   # file_upload测试
│   ├── test_tool_file_download.py # file_download测试
│   ├── test_nplt_protocol.py      # NPLT协议测试
│   ├── test_history_persistence.py # 历史持久化测试
│   ├── test_file_lifecycle.py     # 文件生命周期测试
│   ├── test_context_management.py # 上下文管理测试
│   ├── test_file_context.py       # 文件上下文测试
│   ├── test_chat_features.py      # 聊天功能测试
│   └── test_error_handling.py     # 错误处理测试
├── e2e/                           # 端到端测试（5-10%）
│   └── test_client_server_comm.py # 端到端通信测试
├── performance/                   # 性能测试
│   └── test_performance.py
└── reports/                       # 测试报告输出
    ├── test_report.md             # Markdown报告
    ├── test_results.json          # JSON原始数据
    ├── coverage_report/           # 覆盖率报告（HTML）
    └── prompt_comparison.md       # Prompt版本对比
```

### 关键测试组件

#### 1. 模拟NPLT客户端
```python
class MockNPLTClient:
    """模拟NPLT客户端，用于测试后端通信"""
    def __init__(self):
        self.message_history = []  # 记录所有消息

    async def connect(self, host, port):
        """连接到服务器"""

    async def send_message(self, msg_type, data):
        """发送NPLT消息"""
        # 记录到message_history

    async def receive_message(self):
        """接收NPLT消息"""
        # 记录到message_history

    def get_message_history(self):
        """获取所有消息历史（用于验证）"""

    async def disconnect(self):
        """断开连接"""
```

#### 2. API调用记录器
```python
class APICallRecorder:
    """记录所有智谱API的调用详情"""
    def __init__(self):
        self.call_history = []

    def record_call(self, request, response):
        """记录API调用"""
        self.call_history.append({
            'timestamp': datetime.now(),
            'request': {
                'messages': request.messages,
                'temperature': request.temperature,
                'model': request.model
            },
            'response': {
                'content': response.choices[0].message.content,
                'usage': response.usage.model_dump(),
                'raw_response': response.model_dump()
            }
        })

    def get_call_history(self):
        """获取调用历史"""
```

#### 3. 测试辅助函数
```python
def assert_tool_call(actual_tool, expected_tool, actual_args, expected_args, tolerance=None):
    """断言工具调用符合预期"""

def assert_message_format(message):
    """断言NPLT消息格式正确"""

def assert_history_format(history_data):
    """断言历史记录格式正确"""

def assert_coverage_threshold(module_name, threshold=0.90):
    """断言模块达到覆盖率阈值"""
```

### 测试覆盖率监控

**使用pytest-cov实时监控：**
```bash
# 运行测试并生成覆盖率报告
pytest --cov=server --cov-report=html --cov-report=term-missing

# 查看未覆盖的代码行
pytest --cov=server --cov-report=annotate
```

**覆盖率目标检查：**
```python
# conftest.py
@pytest.fixture(autouse=True)
def check_coverage_threshold(request):
    """每个测试模块结束后检查覆盖率"""
    yield
    if request.node.name == 'test_session_finished':
        cov = request.config.pluginmanager.get_plugin('_cov')
        total = cov.coverage._get_type_coverage()['server']
        assert total >= 0.90, f"覆盖率不足90%: {total*100:.1f}%"
```

## Prompt优化策略

### 优化测试设计

**测试集：**
1. **意图识别测试集**（75个测试）
   - 场景A-E各5个样例 = 25个简单测试
   - 场景F（多工具协作）5个场景 × 5样例 = 25个测试
   - 边界案例 25个测试

2. **多工具协作测试集**（25个测试）
   - 5个场景 × 5样例

**优化流程：**

**第1轮（基线）：**
- Prompt版本：当前prompt（agent.py:460-617）
- 运行测试集
- 记录结果：
  - 意图识别准确率
  - 多工具协作成功率
  - 错误案例清单

**第2轮（针对性优化）：**
- 优化方向：
  1. 明确场景A-C的区分标准
  2. 增加多工具协作的示例
  3. 优化负例（不应调用工具的场景）
- 测试改进效果
- 对比第1轮结果

**第3轮（微调）：**
- 如果第2轮有明显改进，继续微调
- 如果第2轮效果不佳，回退到第1轮并尝试不同方向
- 目标：意图识别≥90%，多工具协作≥85%

**最终选择：**
- 选择综合效果最好的版本
- 更新到agent.py
- 在测试报告中详细说明优化过程

### Prompt优化重点

**问题1：场景A-C的混淆**
- 当前问题："查看配置文件"可能被误判为需要semantic_search
- 优化方案：明确"查看/显示/列出"+文件 → command_executor

**问题2：多工具协作的引导**
- 当前问题：Agent可能在第1轮就调用command_executor，而不是先搜索文件
- 优化方案：在示例中明确展示先搜索再执行的流程

**问题3：负例的强化**
- 当前问题："介绍一下df命令"可能误触发工具调用
- 优化方案：增加更多负例，强调"介绍/说明/解释/是什么"等关键词

## 风险 / 权衡

### 风险1：智谱API限流

**风险描述：**
- 短时间内大量API调用可能触发限流
- 测试执行时间较长

**缓解措施：**
- 测试分批执行（按测试类别）
- 每批测试之间增加短暂延迟
- 使用异步测试并发执行（但控制并发数）
- 监控API调用频率，必要时添加延迟

### 风险2：达到90%覆盖率难度较高

**风险描述：**
- 某些代码分支难以触发（如异常处理）
- 需要大量测试用例

**缓解措施：**
- 使用pytest-cov识别未覆盖的代码
- 重点设计测试触发异常分支
- 使用参数化测试增加覆盖面
- 必要时接受部分模块<90%（但总体≥90%）

### 风险3：Prompt优化可能需要多轮

**风险描述：**
- LLM输出有不确定性
- 可能需要3-5轮才能达到目标

**缓解措施：**
- 预留充足时间进行优化
- 每轮测试后仔细分析错误案例
- 使用temperature=0降低随机性
- 关注整体趋势，不过度追求单次结果

### 风险4：测试报告可能非常庞大

**风险描述：**
- 极其详细的报告可能达到数千行
- 难以阅读和维护

**缓解措施：**
- 使用结构化的Markdown格式
- 提供摘要和详细版本
- JSON原始数据单独保存
- 使用脚本生成报告，减少手工工作

## 迁移计划

### 步骤1：清理老旧测试（不可逆，需确认）
```bash
# 删除所有老旧测试
find tests -name "*.py" -type f ! -path "tests/fixtures/*" ! -path "tests/helpers/*" -delete
```

### 步骤2：创建新的测试基础设施
1. 创建测试目录结构
2. 编写conftest.py和fixtures
3. 创建测试辅助工具（client.py, report.py等）
4. 准备测试数据（config, logs, documents）
5. 配置pytest-cov

### 步骤3：实施单元测试（目标：20-30%）
1. 测试工具的边界条件
2. 测试存储模块的异常处理
3. 测试协议编解码
4. 验证覆盖率达标

### 步骤4：实施集成测试（目标：70-75%）
1. **第1优先级：Agent测试**
   - 意图识别测试（75个测试）
   - 多工具协作测试（25个测试）
   - Prompt优化测试（多轮）

2. **第2优先级：工具链测试**
   - 每个工具的集成测试（各25+测试）
   - 工具组合测试

3. **第3优先级：持久化和通信测试**
   - 历史记录测试
   - 文件生命周期测试
   - NPLT协议测试

### 步骤5：实施端到端测试（目标：5-10%）
1. 模拟客户端-服务器完整交互
2. 多客户端并发测试
3. 长时间运行测试

### 步骤6：Prompt优化
1. 运行第1轮测试（当前prompt）
2. 分析结果，设计prompt v2
3. 运行第2轮测试（prompt v2）
4. 对比结果，必要时进行第3轮
5. 选择最佳prompt，更新到agent.py

### 步骤7：生成测试报告
1. 收集所有测试数据
2. 生成覆盖率报告（HTML）
3. 生成Markdown详细报告
4. 生成JSON原始数据
5. 生成Prompt优化对比报告

### 步骤8：问题分析和改进建议
1. 按严重程度分类问题
2. 分析根本原因
3. 提出改进建议
4. 生成最终测试报告

## 待决问题

### 问题1：测试执行时间预估？
- **当前状态：** 200-300个测试样例
- **预估：** 每个测试平均5-10秒（含API调用）
- **总时间：** 30-60分钟（单线程），可并发压缩到15-30分钟

### 问题2：是否需要CI/CD集成？
- **当前状态：** 未决定
- **待讨论：** 是否在GitHub Actions中运行测试
- **决策点：** 测试稳定后考虑集成

### 问题3：测试报告的存储位置？
- **当前状态：** tests/reports/
- **待确认：** 是否需要单独的docs/reports/目录
- **决策点：** 随时调整

### 问题4：Prompt优化的停止条件？
- **当前状态：** 意图识别≥90%，多工具协作≥85%
- **待讨论：** 是否需要更高目标（如95%/90%）
- **决策点：** 根据第1轮测试结果调整
