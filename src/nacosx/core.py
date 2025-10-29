"""
Core functionality for Nacos service registration and management.
"""

import nacos
import threading
import time
import signal
import sys
import traceback
import asyncio
from functools import wraps
from typing import Callable, Optional, Dict



# Default configuration constants
DEFAULT_REGISTER_RETRIES = 3
DEFAULT_REGISTER_RETRY_DELAY = 2
DEFAULT_HEARTBEAT_INTERVAL = 5
DEFAULT_HEARTBEAT_MAX_FAILURES = 5
DEFAULT_HEARTBEAT_RETRY_DELAY = 2
DEFAULT_UNREGISTER_TIMEOUT = 2


class NacosService:
    """
    Context manager for manual control of Nacos service registration/deregistration lifecycle.
    
    Supports automatic heartbeat, retry mechanism, and graceful shutdown.
    """
    
    def __init__(
        self,
        nacos_addr: str,
        namespace: Optional[str],
        service_name: str,
        service_ip: str,
        service_port: int,
        ephemeral: bool = True,
        metadata: Optional[Dict[str, str]] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        logger=None,
        register_retries=DEFAULT_REGISTER_RETRIES,
        register_retry_delay=DEFAULT_REGISTER_RETRY_DELAY,
        heartbeat_interval=DEFAULT_HEARTBEAT_INTERVAL,
        heartbeat_max_failures=DEFAULT_HEARTBEAT_MAX_FAILURES,
        heartbeat_retry_delay=DEFAULT_HEARTBEAT_RETRY_DELAY,
    ):
        """
        Initialize NacosService.
        
        Args:
            nacos_addr: Nacos server address
            namespace: Nacos namespace
            service_name: Service name to register
            service_ip: Service IP address
            service_port: Service port
            ephemeral: Whether the instance is ephemeral (temporary)
            metadata: Custom metadata dictionary
            username: Nacos username for authentication
            password: Nacos password for authentication
            logger: Custom logger instance
            register_retries: Maximum registration retry attempts
            register_retry_delay: Delay between registration retries (seconds)
            heartbeat_interval: Heartbeat interval (seconds)
            heartbeat_max_failures: Max consecutive heartbeat failures before re-registration
            heartbeat_retry_delay: Delay between heartbeat retries (seconds)
        """
        self.nacos_addr = nacos_addr
        self.namespace = namespace
        self.service_name = service_name
        self.service_ip = service_ip
        self.service_port = service_port
        self.ephemeral = ephemeral
        self.metadata = metadata or {}
        self.username = username
        self.password = password
        self.logger = logger
        self.register_retries = register_retries
        self.register_retry_delay = register_retry_delay
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_max_failures = heartbeat_max_failures
        self.heartbeat_retry_delay = heartbeat_retry_delay

        self._client = None
        self._heartbeat_thread = None
        self._heartbeat_stop = threading.Event()
        self._lock = threading.RLock()
        self._registered = False
        self._orig_sigint = None
        self._orig_sigterm = None

    def _log(self, level: str, *args):
        """Internal logging helper."""
        if self.logger:
            if level == "info":
                self.logger.info(" ".join(map(str, args)))
            elif level == "warning":
                self.logger.warning(" ".join(map(str, args)))
            elif level == "error":
                self.logger.error(" ".join(map(str, args)))
            else:
                self.logger.debug(" ".join(map(str, args)))
        else:
            # Fallback to print to avoid losing logs
            print(*args)

    def _init_client(self):
        """Initialize Nacos client (thread-safe)."""
        with self._lock:
            if self._client is None:
                if nacos is None:
                    raise ImportError("nacos-sdk-python is not installed. Install it with: pip install nacos-sdk-python")
                self._client = nacos.NacosClient(
                    self.nacos_addr,
                    namespace=self.namespace,
                    username=self.username,
                    password=self.password
                )
                self._log("info", "✓ Nacos client initialized successfully")

    def _register_once(self) -> bool:
        """Attempt to register service once."""
        try:
            with self._lock:
                self._client.add_naming_instance(
                    self.service_name,
                    self.service_ip,
                    self.service_port,
                    ephemeral=self.ephemeral,
                    metadata=self.metadata
                )
            self._registered = True
            self._log("info", f"✓ Service registered to Nacos: {self.service_name} {self.service_ip}:{self.service_port}")
            return True
        except Exception as e:
            self._log("warning", f"⚠ Failed to register to Nacos: {e}")
            self._log("debug", traceback.format_exc())
            return False

    def register_with_retry(self, retries: Optional[int] = None, delay: Optional[float] = None) -> bool:
        """Register service with retry mechanism."""
        retries = self.register_retries if retries is None else retries
        delay = self.register_retry_delay if delay is None else delay

        self._init_client()
        for attempt in range(1, retries + 1):
            ok = self._register_once()
            if ok:
                return True
            if attempt < retries:
                self._log("info", f"⚙ Registration attempt {attempt}/{retries} failed, retrying in {delay}s")
                time.sleep(delay)
        return False

    def _remove_once(self) -> bool:
        """Attempt to deregister service once."""
        try:
            with self._lock:
                self._client.remove_naming_instance(self.service_name, self.service_ip, self.service_port)
            self._registered = False
            self._log("info", "✓ Service deregistered from Nacos")
            return True
        except Exception as e:
            self._log("warning", f"⚠ Failed to deregister from Nacos: {e}")
            self._log("debug", traceback.format_exc())
            return False

    def _heartbeat_loop(self):
        """Heartbeat thread main loop with retry and self-healing."""
        fail_count = 0
        while not self._heartbeat_stop.is_set():
            # Wait with interrupt support
            is_stopped = self._heartbeat_stop.wait(self.heartbeat_interval)
            if is_stopped:
                break
            if not self.ephemeral:
                continue  # Permanent instances don't need heartbeat
            
            try:
                with self._lock:
                    self._client.send_heartbeat(self.service_name, self.service_ip, self.service_port)
                fail_count = 0
                # Optional debug logging
                # self._log("debug", "✓ Heartbeat sent successfully")
            except Exception as e:
                fail_count += 1
                self._log("warning", f"⚠ Heartbeat failed ({fail_count}/{self.heartbeat_max_failures}): {e}")
                self._log("debug", traceback.format_exc())
                
                # Wait before retry
                if self._heartbeat_stop.wait(self.heartbeat_retry_delay):
                    break
                
                # Self-healing: re-register after max failures
                if fail_count >= self.heartbeat_max_failures:
                    self._log("warning", "⚠ Detected consecutive heartbeat failures, attempting service re-registration (self-healing)")
                    try:
                        # Try to remove first (may fail)
                        try:
                            with self._lock:
                                self._client.remove_naming_instance(self.service_name, self.service_ip, self.service_port)
                        except Exception:
                            pass  # Ignore remove errors
                        
                        # Re-register with retry
                        ok = self.register_with_retry()
                        if ok:
                            self._log("info", "✓ Self-healing: Re-registration successful, heartbeat failure count reset")
                            fail_count = 0
                        else:
                            self._log("error", "✗ Self-healing: Re-registration failed, will continue trying in background")
                    except Exception as e2:
                        self._log("error", f"✗ Exception during self-healing process: {e2}")
                        self._log("debug", traceback.format_exc())

    def start(self) -> None:
        """
        Initialize client and register service.
        
        Raises:
            RuntimeError: If registration fails after all retries (optional, based on external handling)
        """
        self._init_client()
        ok = self.register_with_retry()
        if not ok:
            self._log("error", "✗ Service registration failed after multiple attempts")
            return
        
        # Start heartbeat thread (only for ephemeral instances)
        if self.ephemeral:
            self._heartbeat_stop.clear()
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()
            self._log("info", f"✓ Heartbeat thread started (interval: {self.heartbeat_interval}s)")

    def stop(self, unregister_timeout: float = DEFAULT_UNREGISTER_TIMEOUT) -> None:
        """Stop heartbeat thread and deregister service."""
        try:
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                self._heartbeat_stop.set()
                self._heartbeat_thread.join(timeout=unregister_timeout)
        except Exception as e:
            self._log("warning", f"⚠ Exception while stopping heartbeat thread: {e}")
        
        try:
            self._remove_once()
        except Exception:
            pass

    def install_signal_handlers(self):
        """Install signal handlers for graceful shutdown."""
        def _handle(signum, frame):
            self._log("info", f"⚙ Received exit signal ({signum}), preparing graceful shutdown...")
            try:
                self.stop()
            except Exception as e:
                self._log("error", f"✗ Graceful shutdown failed: {e}")
            
            # Call original handler if exists
            orig = {signal.SIGINT: self._orig_sigint, signal.SIGTERM: self._orig_sigterm}.get(signum)
            if orig:
                if callable(orig):
                    try:
                        orig(signum, frame)
                    except Exception:
                        pass
            
            # Exit if no original handler
            try:
                sys.exit(0)
            except SystemExit:
                raise

        # Save and replace original handlers
        self._orig_sigint = signal.getsignal(signal.SIGINT)
        self._orig_sigterm = signal.getsignal(signal.SIGTERM)
        try:
            signal.signal(signal.SIGINT, _handle)
            signal.signal(signal.SIGTERM, _handle)
            self._log("info", "✓ Graceful shutdown signal handlers installed")
        except Exception as e:
            self._log("warning", f"⚠ Failed to install signal handlers: {e}")

    def restore_signal_handlers(self):
        """Restore original signal handlers."""
        try:
            if self._orig_sigint is not None:
                signal.signal(signal.SIGINT, self._orig_sigint)
            if self._orig_sigterm is not None:
                signal.signal(signal.SIGTERM, self._orig_sigterm)
            self._log("info", "✓ Original signal handlers restored")
        except Exception as e:
            self._log("warning", f"⚠ Failed to restore signal handlers: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.install_signal_handlers()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        try:
            self.stop()
        finally:
            self.restore_signal_handlers()


def _call_func(func: Callable, is_coroutine: bool, *args, **kwargs):
    """Helper to call function (sync or async)."""
    if is_coroutine:
        return func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def nacos_registry(
    enabled: bool = True,
    nacos_addr: str = "",
    namespace: Optional[str] = None,
    service_name: str = "",
    service_addr: str = "",
    ephemeral: bool = True,
    heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
    heartbeat_max_failures: int = DEFAULT_HEARTBEAT_MAX_FAILURES,
    heartbeat_retry_delay: int = DEFAULT_HEARTBEAT_RETRY_DELAY,
    metadata: Optional[Dict[str, str]] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    logger=None,
    raise_on_register_fail: bool = True,
    register_retries: int = DEFAULT_REGISTER_RETRIES,
    register_retry_delay: int = DEFAULT_REGISTER_RETRY_DELAY,
):
    """
    Enhanced Nacos registration decorator.
    
    Supports context management, heartbeat self-healing, and graceful shutdown.
    
    Args:
        enabled: Enable/disable registration
        nacos_addr: Nacos server address
        namespace: Nacos namespace
        service_name: Service name to register
        service_addr: Service address in "ip:port" format
        ephemeral: Whether instance is ephemeral
        heartbeat_interval: Heartbeat interval (seconds)
        heartbeat_max_failures: Max heartbeat failures before re-registration
        heartbeat_retry_delay: Delay between heartbeat retries
        metadata: Custom metadata dictionary
        username: Nacos username
        password: Nacos password
        logger: Custom logger instance
        raise_on_register_fail: Raise exception on registration failure
        register_retries: Maximum registration retry attempts
        register_retry_delay: Delay between registration retries
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        is_coroutine = asyncio.iscoroutinefunction(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not enabled:
                return _call_func(func, is_coroutine, *args, **kwargs)

            # Parse service_addr
            if not nacos_addr:
                msg = "Nacos nacos_addr is required"
                if raise_on_register_fail:
                    raise ValueError(msg)
                else:
                    print("⚠", msg)
                    return _call_func(func, is_coroutine, *args, **kwargs)
            
            if not service_name:
                msg = "Nacos service_name is required"
                if raise_on_register_fail:
                    raise ValueError(msg)
                else:
                    print("⚠", msg)
                    return _call_func(func, is_coroutine, *args, **kwargs)
            
            if not service_addr or ':' not in service_addr:
                msg = f"Nacos configuration incomplete or service_addr format error: {service_addr}"
                if raise_on_register_fail:
                    raise ValueError(msg)
                else:
                    print("⚠", msg)
                    return _call_func(func, is_coroutine, *args, **kwargs)

            service_ip, port_str = service_addr.rsplit(':', 1)
            try:
                service_port = int(port_str)
            except ValueError:
                msg = f"Failed to parse port from service_addr: {service_addr}"
                if raise_on_register_fail:
                    raise ValueError(msg)
                else:
                    print("⚠", msg)
                    return _call_func(func, is_coroutine, *args, **kwargs)

            # Create NacosService instance
            nacos_svc = NacosService(
                nacos_addr=nacos_addr,
                namespace=namespace,
                service_name=service_name,
                service_ip=service_ip,
                service_port=service_port,
                ephemeral=ephemeral,
                metadata=metadata,
                username=username,
                password=password,
                logger=logger,
                register_retries=register_retries,
                register_retry_delay=register_retry_delay,
                heartbeat_interval=heartbeat_interval,
                heartbeat_max_failures=heartbeat_max_failures,
                heartbeat_retry_delay=heartbeat_retry_delay,
            )

            # Use context manager for lifecycle management
            try:
                with nacos_svc:
                    return _call_func(func, is_coroutine, *args, **kwargs)
            except Exception as e:
                if logger:
                    logger.error(f"✗ Exception in decorated function: {e}")
                    logger.debug(traceback.format_exc())
                else:
                    print(f"✗ Exception in decorated function: {e}")
                    print(traceback.format_exc())
                
                if raise_on_register_fail:
                    raise
                else:
                    return None

        return wrapper
    return decorator
