# 变更：增强日志系统

## 为什么

当前日志系统存在客户端日志内容不足（client.log 只有 15KB，远小于 server.log 的 197KB），缺少大模型调用日志记录，导致调试时无法追踪完整的请求-响应流程，定位问题困难。

## 变更内容

- 增强客户端日志记录，覆盖所有关键操作（连接、消息收发、UI交互、文件下载等）
- 添加大模型调用专用日志（包括请求参数、完整响应、流式输出、调用耗时等）
- 在 `shared/utils/logger.py` 中添加 `get_llm_logger()` 函数
- 为客户端网络通信和 UI 交互创建独立的日志记录器
- 支持通过 config.yaml 配置各模块的日志级别

## 影响

- 受影响规范：
  - `cli-ui`（新增客户端日志相关需求）
  - 新增 `llm-logging` 规范
- 受影响代码：
  - `shared/utils/logger.py` - 添加新的日志记录器函数
  - `clients/cli/main.py` - 增强客户端主程序日志
  - `clients/cli/nplt_client.py` - 增强网络通信日志
  - `clients/cli/ui.py` - 增强 UI 交互日志
  - `server/llm/zhipu.py` - 添加大模型调用日志
  - `config.yaml` - 添加日志配置项（可选）

## 兼容性

- 不影响现有功能
- 日志向后兼容
- 可通过日志级别控制日志详细程度（DEBUG/INFO/WARNING/ERROR）

## 验证标准

1. `client.log` 包含完整的客户端操作记录
2. 新增 `llm.log` 文件记录所有大模型调用的输入和输出
3. 可以通过日志追踪完整的请求-响应流程
4. 日志不影响系统性能（异步写入、合理的日志级别）
