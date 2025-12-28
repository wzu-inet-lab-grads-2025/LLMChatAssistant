# RDT 协议规范

**版本**: 3.0 | **日期**: 2025-12-28

## 概述

RDT (Reliable Data Transfer) 是一个基于滑动窗口的可靠数据传输协议，运行在 UDP 之上，用于在不可靠的网络上传输文件。本实现基于经典的 RDT 3.0 协议，添加了滑动窗口机制以提高传输效率。

## 协议设计目标

1. **可靠性**: 通过序列号、校验和、ACK 确保数据完整传输
2. **性能**: 滑动窗口机制提高吞吐量
3. **鲁棒性**: 超时重传机制处理丢包
4. **简单性**: 清晰的状态机和协议格式

## 数据包格式

### 包结构

```
+--------+--------+----------+
| Seq    | Check  | Data     |
| 2 Bytes| 2 Bytes| <=1024 Bytes|
+--------+--------+----------+
```

### 字段说明

| 字段 | 大小 | 类型 | 描述 |
|------|------|------|------|
| Seq | 2 Bytes | uint16 | 序列号，范围 0-65535，大端序 |
| Check | 2 Bytes | uint16 | CRC16 校验和 |
| Data | 0-1024 Bytes | bytes | 文件数据块 |

**总包大小**: 4 + Data.Length 字节（最大 1028 字节）

### 序列号规则

- 序列号从 0 开始递增
- 每个数据包序列号唯一
- 发送方和接收方独立维护序列号

### 校验和计算

```python
def crc16(data: bytes) -> int:
    """计算 CRC16 校验和"""
    crc = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc
```

## 确认机制

### ACK 包格式

```
+--------+--------+
| Seq    | Check  |
| 2 Bytes| 2 Bytes|
+--------+--------+
```

**ACK 包说明**:
- `Seq`: 确认的序列号（表示已收到此序列号及之前的所有包）
- `Check`: ACK 包的校验和

### ACK 规则

1. **累积确认**: ACK Seq=N 表示已收到 0 到 N 的所有包
2. **重复 ACK**: 接收方重复发送 ACK 表示未收到新包
3. **选择性 ACK**: 未来可扩展为 NACK 机制

## 滑动窗口

### 窗口参数

- **窗口大小 (N)**: 5 个包
- **最大包大小**: 1024 字节
- **窗口滑动**: 收到 ACK 时滑动

### 窗口结构

```
发送方窗口:
[已发送已确认] [已发送未确认] [可发送] [不可发送]
  0..base-1    base..next-1   next..base+N-1  base+N..

例如: base=5, next=8, N=5
已发送已确认: 0-4
已发送未确认: 5-7 (3 个包)
可发送: 8-9 (2 个包)
不可发送: 10+
```

### 窗口滑动条件

1. **正常滑动**: 收到 ACK=base，窗口右移 1 位
2. **批量滑动**: 收到 ACK=base+k，窗口右移 k 位
3. **不滑动**: 未收到新 ACK，窗口不动

## 发送方状态机

### 状态定义

```
            发送数据包
  +-----------------------------+
  v                             |
[SENDING] ----超时----> [RESEND] ----重传成功----> [SENDING]
  |                       ^
  +---收到ACK------------------+
```

### 状态描述

| 状态 | 描述 | 条件 |
|------|------|------|
| SENDING | 发送数据包 | 初始状态，或重传后 |
| RESEND | 超时重传 | SendBase 包超时 |

### 发送方逻辑

```python
class RDTSender:
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.send_base = 0      # 窗口基序列号
        self.next_seq = 0       # 下一个序列号
        self.packets = {}       # 已发送的包
        self.acked = set()      # 已确认的包
        self.timeout_start = None  # 超时计时起点

    def can_send(self) -> bool:
        """检查是否可以发送新包"""
        return self.next_seq < self.send_base + self.window_size

    def send(self, data: bytes):
        """发送数据包"""
        if not self.can_send():
            raise Exception("窗口已满")

        packet = RDTPacket(seq=self.next_seq, data=data)
        self.packets[self.next_seq] = packet
        udp_send(packet.encode())

        if self.send_base == self.next_seq:
            self.timeout_start = time.time()

        self.next_seq += 1

    def on_ack(self, ack_seq: int):
        """处理 ACK"""
        if ack_seq >= self.send_base:
            # 滑动窗口
            old_base = self.send_base
            self.send_base = ack_seq + 1

            # 清理已确认的包
            for seq in range(old_base, self.send_base):
                self.acked.add(seq)
                if seq in self.packets:
                    del self.packets[seq]

            # 如果还有未确认的包，重启计时
            if self.send_base < self.next_seq:
                self.timeout_start = time.time()

    def check_timeout(self, timeout=0.1):
        """检查超时（仅对 SendBase 计时）"""
        if self.send_base < self.next_seq:  # 有未确认的包
            if self.timeout_start and time.time() - self.timeout_start > timeout:
                # 超时，重传 SendBase
                packet = self.packets[self.send_base]
                udp_send(packet.encode())
                self.timeout_start = time.time()
```

## 接收方状态机

### 状态定义

```
[WAITING] ----收到数据包----> [RECEIVING]
                                    |
                               校验和验证
                                    |
                        +-----------+-----------+
                        |                       |
                      通过                    失败
                        |                       |
                     发送ACK                丢弃包
                        |
                        v
                   [WAITING]
```

### 状态描述

| 状态 | 描述 |
|------|------|
| WAITING | 等待接收数据包 |
| RECEIVING | 处理接收的数据包 |

### 接收方逻辑

```python
class RDTReceiver:
    def __init__(self):
        self.expected_seq = 0   # 期望的序列号
        self.received_data = {} # 接收的数据
        self.acked_seq = -1     # 已确认的最高序列号

    def on_packet(self, packet: RDTPacket):
        """处理接收的数据包"""
        # 校验和验证
        if not packet.validate():
            return  # 丢弃包

        if packet.seq == self.expected_seq:
            # 按序接收
            self.received_data[packet.seq] = packet.data
            self.expected_seq += 1

            # 发送累积 ACK
            self.send_ack(packet.seq)

            # 检查是否有缓存的高序号包
            while self.expected_seq in self.received_data:
                self.expected_seq += 1

        elif packet.seq > self.expected_seq:
            # 乱序接收，缓存数据包
            if packet.seq not in self.received_data:
                self.received_data[packet.seq] = packet.data

            # 发送重复 ACK
            self.send_ack(self.expected_seq - 1)

        else:
            # 重复包（seq < expected_seq）
            # 发送 ACK
            self.send_ack(packet.seq)

    def send_ack(self, seq: int):
        """发送 ACK"""
        if seq > self.acked_seq:
            self.acked_seq = seq
            ack_packet = ACKPacket(seq=seq)
            udp_send(ack_packet.encode())
```

## 超时重传

### 超时计算

**策略**: 仅对 SendBase 包计时

**理由**: 简化实现，避免为每个包维护计时器

**超时时间**: 100ms（可根据网络状况调整）

### 超时处理流程

1. 检测到 SendBase 包超时
2. 重传 SendBase 包
3. 重启计时器
4. 等待 ACK

### 超时场景示例

```
时间轴:
T0: 发送 Seq=0, 计时器开始
T1: 发送 Seq=1-4 (窗口内)
T2: 超时! (100ms 后仍未收到 ACK)
    -> 重传 Seq=0, 重启计时
T3: 收到 ACK=0
    -> 滑动窗口到 base=1
T4: 收到 ACK=4
    -> 滑动窗口到 base=5
```

## 丢包处理

### 场景 1: 发送方丢包

```
发送方发送: 0, 1, 2, 3, 4
网络丢失: 2
接收方收到: 0, 1, 3, 4
接收方 ACK: ACK=0, ACK=1, ACK=1, ACK=1 (重复 ACK)
发送方检测到重复 ACK=1，超时后重传 Seq=2
```

### 场景 2: ACK 丢失

```
发送方发送: 0, 1, 2
接收方收到: 0, 1, 2
接收方 ACK: ACK=0, ACK=1, ACK=2
网络丢失: ACK=1
发送方收到: ACK=0, ACK=2
发送方识别累积确认，窗口滑动到 base=3
```

### 场景 3: 连续丢包

```
发送方发送: 0, 1, 2, 3, 4
网络丢失: 1, 2, 3
接收方收到: 0, 4
接收方 ACK: ACK=0, ACK=0 (重复)
发送方超时重传: Seq=0
接收方收到重复 Seq=0，丢弃并发送 ACK=0
...（超时重传循环，直到重传次数 > 10）
传输失败
```

## 可视化传输

### 窗口状态显示

```
发送方窗口状态:
[████████] [████████] [████████] [        ] [        ]
  Seq=5     Seq=6     Seq=7     Seq=8     Seq=9
  已确认    已确认    待确认    可发送    可发送

传输进度: ████████░░░░░░░░ 50% (1024/2048 KB)
速度: 1.2 MB/s
重传: 2 次
```

### 滑动窗口动画

```
初始状态:
[base=0, next=0, window=5]
[ ] [ ] [ ] [ ] [ ]

发送 5 个包:
[base=0, next=5, window=5]
[0] [1] [2] [3] [4]

收到 ACK=2:
[base=3, next=5, window=5]
   [2] [3] [4] [ ] [ ]

发送 2 个新包:
[base=3, next=7, window=5]
   [2] [3] [4] [5] [6]
```

## 测试场景

### 正常流程测试

1. 发送方发送 10 个包（窗口 5）
2. 接收方依次接收并确认
3. 窗口正常滑动
4. 传输完成

### 丢包测试

1. 发送方发送 10 个包
2. 网络随机丢弃 20% 的包
3. 发送方超时重传
4. 最终传输完成

### 超时测试

1. 发送方发送包
2. 接收方不发送 ACK
3. 发送方超时重传
4. 验证重传次数限制

### 边界测试

1. **空文件**: 0 字节
2. **小文件**: < 1024 字节（1 个包）
3. **精确边界**: 1024 字节（1 个包）
4. **大文件**: 10240 字节（10 个包）
5. **序列号回绕**: Seq=65535 → Seq=0

## 性能指标

### 吞吐量

**理论吞吐量**:

```
吞吐量 = (窗口大小 * 包大小) / RTT
       = (5 * 1024) / 0.01  (假设 RTT=10ms)
       = 512 KB/s
```

**实际吞吐量**: 目标 > 1 MB/s (在 0% 丢包网络)

### 延迟

**首包延迟**: RTT + 处理时间
**末包延迟**: RTT + 处理时间 + (总包数 / 窗口大小) * 超时时间

### 丢包率 vs 成功率

| 丢包率 | 成功率 | 重传次数 | 传输时间 |
|--------|--------|----------|----------|
| 0% | 100% | 0 | 基准 |
| 5% | 100% | ~5 | +20% |
| 10% | 100% | ~12 | +50% |
| 20% | 100% | ~30 | +150% |

## 错误处理

### 校验和错误

1. 检测到校验和不匹配
2. 丢弃数据包
3. 不发送 ACK
4. 等待发送方超时重传

### 超时限制

**最大重传次数**: 10 次

**超时后处理**:
1. 停止重传
2. 标记传输失败
3. 向用户报告错误

### 序列号错误

**检测条件**:
- 接收到的序列号 < expected_seq - 100
- 可能原因: 序列号回绕或严重延迟

**处理方式**:
- 记录警告日志
- 继续正常处理

## 示例代码

### 完整发送方实现

```python
import time
import struct
import socket
from dataclasses import dataclass
from typing import Dict, Set

@dataclass
class RDTPacket:
    seq: int
    data: bytes
    checksum: int = 0

    def encode(self) -> bytes:
        data = struct.pack(">H", self.seq) + self.data
        checksum = crc16(data)
        return struct.pack(">HH", self.seq, checksum) + self.data

    @classmethod
    def decode(cls, data: bytes) -> 'RDTPacket':
        seq, checksum = struct.unpack(">HH", data[:4])
        payload = data[4:]
        return cls(seq=seq, data=payload, checksum=checksum)

    def validate(self) -> bool:
        data = struct.pack(">H", self.seq) + self.data
        return self.checksum == crc16(data)

class RDTSender:
    def __init__(self, dest_addr: tuple, window_size: int = 5):
        self.dest_addr = dest_addr
        self.window_size = window_size
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_base = 0
        self.next_seq = 0
        self.packets: Dict[int, RDTPacket] = {}
        self.acked: Set[int] = set()
        self.timeout_start = None
        self.max_retries = 10
        self.retry_count = 0

    def send_file(self, file_data: bytes):
        """发送文件"""
        total_packets = (len(file_data) + 1023) // 1024

        while self.send_base < total_packets:
            # 发送窗口内的包
            while self.next_seq < min(self.send_base + self.window_size, total_packets):
                start = self.next_seq * 1024
                end = start + 1024
                chunk = file_data[start:end]
                self._send_packet(RDTPacket(seq=self.next_seq, data=chunk))
                self.next_seq += 1

            # 等待 ACK 或超时
            try:
                ack_data, _ = self.sock.recvfrom(4)
                ack_seq = struct.unpack(">H", ack_data[:2])[0]
                self._on_ack(ack_seq)
                self.retry_count = 0  # 重置重试计数
            except socket.timeout:
                self._handle_timeout()

            if self.retry_count > self.max_retries:
                raise Exception("传输失败：超过最大重传次数")

    def _send_packet(self, packet: RDTPacket):
        self.sock.sendto(packet.encode(), self.dest_addr)
        self.packets[packet.seq] = packet
        if packet.seq == self.send_base and self.timeout_start is None:
            self.timeout_start = time.time()

    def _on_ack(self, ack_seq: int):
        if ack_seq >= self.send_base:
            old_base = self.send_base
            self.send_base = ack_seq + 1

            for seq in range(old_base, self.send_base):
                self.acked.add(seq)
                if seq in self.packets:
                    del self.packets[seq]

            if self.send_base < self.next_seq:
                self.timeout_start = time.time()
            else:
                self.timeout_start = None

    def _handle_timeout(self):
        if self.send_base < self.next_seq:
            packet = self.packets[self.send_base]
            self._send_packet(packet)
            self.retry_count += 1
            self.timeout_start = time.time()
```

### 完整接收方实现

```python
class RDTReceiver:
    def __init__(self, bind_addr: tuple):
        self.bind_addr = bind_addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(bind_addr)
        self.sock.settimeout(1.0)
        self.expected_seq = 0
        self.received_data: Dict[int, bytes] = {}
        self.acked_seq = -1

    def receive_file(self, total_size: int) -> bytes:
        """接收文件"""
        file_data = bytearray()
        total_packets = (total_size + 1023) // 1024

        while len(self.received_data) < total_packets:
            try:
                data, addr = self.sock.recvfrom(1028)
                packet = RDTPacket.decode(data)

                if packet.validate():
                    self._on_packet(packet)

            except socket.timeout:
                continue

        # 组装文件
        for seq in sorted(self.received_data.keys()):
            file_data.extend(self.received_data[seq])

        return bytes(file_data)

    def _on_packet(self, packet: RDTPacket):
        if packet.seq == self.expected_seq:
            # 按序接收
            self.received_data[packet.seq] = packet.data
            self.expected_seq += 1
            self._send_ack(packet.seq)

            # 检查缓存的高序号包
            while self.expected_seq in self.received_data:
                self.expected_seq += 1

        elif packet.seq > self.expected_seq:
            # 乱序接收，缓存
            if packet.seq not in self.received_data:
                self.received_data[packet.seq] = packet.data
            self._send_ack(self.expected_seq - 1)

        else:
            # 重复包
            self._send_ack(packet.seq)

    def _send_ack(self, seq: int):
        if seq > self.acked_seq:
            self.acked_seq = seq
            ack_data = struct.pack(">H", seq)
            self.sock.sendto(ack_data, self.dest_addr)
```

## 参考资料

- [RDT 协议经典实现](https://stanford.edu/class/cs144/)
- [滑动窗口协议](https://en.wikipedia.org/wiki/Sliding_window_protocol)
- [CRC 校验算法](https://en.wikipedia.org/wiki/Cyclic_redundancy_check)
- [UDP 可靠传输设计](https://en.wikipedia.org/wiki/Reliable_User_Datagram_Protocol)
