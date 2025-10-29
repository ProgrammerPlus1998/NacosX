# NacosX

[English](README.md) | [中文](README_CN.md)

**NacosX** is a decorator-based Python library designed to make service registration and discovery with Nacos effortless.  
It automates the entire lifecycle — registration, heartbeat maintenance, re-registration on failure, and graceful shutdown — with just one decorator.

Built on top of [nacos-sdk-python](https://github.com/nacos-group/nacos-sdk-python), NacosX provides a higher-level, decorator-based abstraction for seamless integration.

---

## 🌟 Key Features

- 🚀 **One-line decorator** to register your gRPC or HTTP service with Nacos
- 💓 **Automatic heartbeat** with failure detection and self-healing
- 🔄 **Retry mechanism** for registration and reconnection
- 🧘 **Graceful shutdown** with SIGINT / SIGTERM handling
- 🧩 **Thread-safe and async-compatible**, supporting both sync and async functions
- 🔧 **Custom metadata and namespace** support
- 📦 **Designed for Kubernetes/CCE environments** where stability and self-healing matter

---

## 📦 Installation

```bash
pip install nacosx
```

---

## 🔧 Quick Start

### Basic Example

```python
import time
from nacosx import nacos_registry

@nacos_registry(
    nacos_addr="127.0.0.1:8848",
    namespace="dev",
    service_name="example-service",
    service_addr="192.168.0.101:50051",
)
def main():
    print("Service running...")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
```

### ✅ What Happens Automatically:

- ✓ Registers `example-service` to Nacos
- ✓ Sends periodic heartbeats
- ✓ Re-registers if heartbeats fail multiple times
- ✓ Deregisters gracefully on `Ctrl+C` or container termination

---

## 🎯 Advanced Usage

### Custom Metadata

```python
@nacos_registry(
    nacos_addr="127.0.0.1:8848",
    service_name="my-service",
    service_addr="192.168.1.10:8080",
    metadata={"version": "1.0.0", "env": "production"},
)
def run_service():
    # Your service logic
    pass
```

### Async Function Support

```python
import asyncio
from nacosx import nacos_registry

@nacos_registry(
    nacos_addr="127.0.0.1:8848",
    service_name="async-service",
    service_addr="0.0.0.0:8080",
)
async def async_main():
    print("Async service running...")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(async_main())
```

### Context Manager (Manual Control)

For manual lifecycle control, use `NacosService` as a context manager:

```python
from nacosx import NacosService
import time

def run_my_service():
    print("Service is running...")
    time.sleep(10)

with NacosService(
    nacos_addr="127.0.0.1:8848",
    namespace="dev",
    service_name="my-service",
    service_ip="192.168.1.10",
    service_port=8080,
    metadata={"version": "1.0.0"},
) as svc:
    run_my_service()
    # Then register to Nacos when service is ready
    svc.start()
    # Service will be automatically deregistered when exiting the context
```

Or without context manager:

```python
from nacosx import NacosService

svc = NacosService(
    nacos_addr="127.0.0.1:8848",
    service_name="my-service",
    service_ip="192.168.1.10",
    service_port=8080,
)

try:
    svc.start()  # Register and start heartbeat
    # Your service logic here
    while True:
        time.sleep(1)
finally:
    svc.stop()  # Deregister and stop heartbeat
```

---

## 🛠️ Configuration Options

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `nacos_addr` | `str` | ✅ | - | Nacos server address (e.g., `127.0.0.1:8848`) |
| `service_name` | `str` | ✅ | - | Service name to register |
| `service_addr` | `str` | ✅ | - | Service address (IP:PORT) |
| `namespace` | `str` | ❌ | `public` | Nacos namespace |
| `group_name` | `str` | ❌ | `DEFAULT_GROUP` | Service group name |
| `cluster_name` | `str` | ❌ | `DEFAULT` | Cluster name |
| `metadata` | `dict` | ❌ | `{}` | Custom metadata |
| `heartbeat_interval` | `int` | ❌ | `5` | Heartbeat interval in seconds |
| `max_retry` | `int` | ❌ | `3` | Max retry attempts for registration |

---

## 🔄 How It Works

1. **Registration**: When your decorated function starts, NacosX registers the service with Nacos
2. **Heartbeat**: A background thread sends periodic heartbeats to keep the service alive
3. **Self-Healing**: If heartbeats fail consecutively, NacosX attempts re-registration
4. **Graceful Shutdown**: On `SIGINT`/`SIGTERM`, the service is deregistered before exit

---

## 📝 Requirements

- Python >= 3.7
- [nacos-sdk-python](https://github.com/nacos-group/nacos-sdk-python) >= 2.0.0, < 3.0.0

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by the need for simpler Nacos integration in Python microservices
- Built with ❤️ for the Python community

---

## 📮 Contact

If you have any questions or suggestions, please open an issue on GitHub.

**GitHub**: [https://github.com/ProgrammerPlus1998/NacosX](https://github.com/ProgrammerPlus1998/NacosX)
