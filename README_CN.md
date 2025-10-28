# NacosX

[English](README.md) | [中文](README_CN.md)

**NacosX** 是一个基于装饰器的 Python 库，旨在让 Nacos 服务注册与发现变得轻松简单。  
它仅需一个装饰器，就能自动化整个生命周期 — 注册、心跳维护、失败重注册以及优雅关闭。

---

## 🌟 核心特性

- 🚀 **单行装饰器**即可将 gRPC 或 HTTP 服务注册到 Nacos
- 💓 **自动心跳**，具备故障检测和自我修复能力
- 🔄 **重试机制**，支持注册和重连
- 🧘 **优雅关闭**，处理 SIGINT / SIGTERM 信号
- 🧩 **线程安全且兼容异步**，支持同步和异步函数
- 🔧 **自定义元数据和命名空间**支持
- 📦 **专为 Kubernetes/CCE 环境设计**，注重稳定性和自我修复

---

## 📦 安装

```bash
pip install nacosx
```

---

## 🔧 快速开始

### 基础示例

```python
import time
from nacosx import nacos_registry

@nacos_registry(
    server_addr="127.0.0.1:8848",
    namespace="dev",
    service_name="example-service",
    service_addr="192.168.0.101:50051",
)
def main():
    print("服务运行中...")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
```

### ✅ 自动完成的操作：

- ✓ 将 `example-service` 注册到 Nacos
- ✓ 发送周期性心跳
- ✓ 如果心跳多次失败，自动重新注册
- ✓ 在 `Ctrl+C` 或容器终止时优雅注销

---

## 🎯 高级用法

### 自定义元数据

```python
@nacos_registry(
    server_addr="127.0.0.1:8848",
    service_name="my-service",
    service_addr="192.168.1.10:8080",
    metadata={"version": "1.0.0", "env": "production"},
)
def run_service():
    # 你的服务逻辑
    pass
```

### 异步函数支持

```python
import asyncio
from nacosx import nacos_registry

@nacos_registry(
    server_addr="127.0.0.1:8848",
    service_name="async-service",
    service_addr="0.0.0.0:8080",
)
async def async_main():
    print("异步服务运行中...")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(async_main())
```

### 上下文管理器（手动控制）

如需手动控制生命周期，可以使用 `NacosService` 作为上下文管理器：

```python
from nacosx import NacosService
import time

def run_my_service():
    print("服务运行中...")
    time.sleep(10)

with NacosService(
    server_addr="127.0.0.1:8848",
    namespace="dev",
    service_name="my-service",
    service_ip="192.168.1.10",
    service_port=8080,
    metadata={"version": "1.0.0"},
) as svc:
    # 进入上下文时自动注册服务
    run_my_service()
    # 退出上下文时自动注销服务
```

或者不使用上下文管理器：

```python
from nacosx import NacosService

svc = NacosService(
    server_addr="127.0.0.1:8848",
    service_name="my-service",
    service_ip="192.168.1.10",
    service_port=8080,
)

try:
    svc.start()  # 注册服务并启动心跳
    # 你的服务逻辑
    while True:
        time.sleep(1)
finally:
    svc.stop()  # 注销服务并停止心跳
```

---

## 🛠️ 配置选项

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `server_addr` | `str` | ✅ | - | Nacos 服务器地址（如 `127.0.0.1:8848`） |
| `service_name` | `str` | ✅ | - | 要注册的服务名称 |
| `service_addr` | `str` | ✅ | - | 服务地址（IP:端口） |
| `namespace` | `str` | ❌ | `public` | Nacos 命名空间 |
| `group_name` | `str` | ❌ | `DEFAULT_GROUP` | 服务分组名称 |
| `cluster_name` | `str` | ❌ | `DEFAULT` | 集群名称 |
| `metadata` | `dict` | ❌ | `{}` | 自定义元数据 |
| `heartbeat_interval` | `int` | ❌ | `5` | 心跳间隔（秒） |
| `max_retry` | `int` | ❌ | `3` | 注册最大重试次数 |

---

## 🔄 工作原理

1. **注册**：当装饰的函数启动时，NacosX 将服务注册到 Nacos
2. **心跳**：后台线程发送周期性心跳以保持服务活跃
3. **自我修复**：如果心跳连续失败，NacosX 会尝试重新注册
4. **优雅关闭**：收到 `SIGINT`/`SIGTERM` 信号时，在退出前注销服务

---

## 📝 依赖要求

- Python >= 3.7
- requests >= 2.25.0

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- 灵感来源于在 Python 微服务中简化 Nacos 集成的需求
- 用 ❤️ 为 Python 社区构建

---

## 📮 联系方式

如有任何问题或建议，请在 GitHub 上提交 issue。

**GitHub**: [https://github.com/ProgrammerPlus1998/NacosX](https://github.com/ProgrammerPlus1998/NacosX)
