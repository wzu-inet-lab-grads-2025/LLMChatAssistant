# client-logging Specification

## Purpose
TBD - created by archiving change improve-logging. Update Purpose after archive.
## 需求
### 需求：客户端日志记录器配置

客户端日志系统**必须**使用专门的日志记录器，支持独立的日志文件和可配置的日志级别。系统**应**提供 `get_client_logger()` 函数获取客户端日志记录器，使用 `client` 作为 logger 名称，输出到 `logs/client.log` 文件，默认级别为 INFO，同时支持 DEBUG 级别用于详细调试。

#### 场景：独立的客户端日志记录器

**Given** 客户端模块需要记录日志
**When** 初始化日志系统
**Then** 应使用 `get_client_logger()` 获取专门的客户端日志记录器：
- Logger 名称：`client`（或 `clients.cli`）
- 日志文件：`logs/client.log`
- 默认级别：INFO
- 支持 DEBUG 级别用于详细调试

#### 场景：网络通信日志记录器

**Given** 需要记录网络通信细节
**When** 初始化日志系统
**Then** 应使用独立的网络日志记录器：
- Logger 名称：`client.network`（或 `network`）
- 日志文件：`logs/network.log`
- 默认级别：DEBUG
- 专门记录消息收发、连接状态、心跳等

