"""Task-owned Redis transport bounds for the immutable ADR-087 envelope."""

from __future__ import annotations

import copy
import ipaddress
import json
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone

from redis.connection import Connection, ConnectionPool, SSLConnection
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.retry import Retry

from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadline,
    AcceptedChatTaskDeadlineExceeded,
)


@dataclass
class _Budget:
    work_end: float
    terminal_end: float
    terminal: bool = False
    invalid: bool = False
    client: object | None = None

    def remaining(self):
        if self.invalid:
            raise ValueError("accepted chat deadline snapshot is invalid")
        remaining = (self.terminal_end if self.terminal else self.work_end) - time.monotonic()
        if remaining <= 0:
            error = AcceptedChatTaskDeadlineExceeded()
            if self.terminal:
                error.detail["message"] = "Accepted chat task terminal deadline exceeded."
            raise error
        return remaining

    def sleep(self, seconds):
        limit = min(seconds, self.remaining())
        time.sleep(max(0, limit))
        self.remaining()

    def close_client(self):
        client, self.client = self.client, None
        pool = getattr(client, "connection_pool", None)
        if isinstance(pool, ConnectionPool):
            client.close()
            pool.disconnect()


_budget: ContextVar[_Budget | None] = ContextVar("chat_redis_budget", default=None)


@contextmanager
def accepted_redis_scope(
    deadline: AcceptedChatTaskDeadline | None, *, now=None,
    monotonic_at_wall=None, invalid=False,
):
    value = None
    if deadline is not None:
        clock = time.monotonic() if monotonic_at_wall is None else monotonic_at_wall
        wall = now or datetime.now(timezone.utc)
        work = (deadline.work_deadline_at - wall).total_seconds()
        terminal = (deadline.terminal_deadline_at - wall).total_seconds()
        value = _Budget(clock + work, clock + terminal, terminal=work <= 0)
    elif invalid:
        value = _Budget(0, 0, invalid=True)
    token = _budget.set(value)
    try:
        yield
    finally:
        try:
            if value is not None:
                value.close_client()
        finally:
            _budget.reset(token)


def use_redis_terminal_budget():
    value = _budget.get()
    if value is not None:
        value.terminal = True


def reset_scoped_redis_client():
    value = _budget.get()
    if value is None:
        return False
    value.close_client()
    return True


def redis_retry_sleep(seconds):
    value = _budget.get()
    if value is None:
        time.sleep(seconds)
    else:
        value.sleep(seconds)


class _BoundedBackoff:
    def __init__(self, backoff):
        self.backoff = backoff

    def reset(self):
        self.backoff.reset()

    def compute(self, failures):
        delay = self.backoff.compute(failures)
        if delay > 0:
            redis_retry_sleep(delay)
        # The original driver's retry loop must not sleep a second time.
        return 0


class _BoundedRetry(Retry):
    def call_with_retry(self, do, fail, is_retryable=None):
        def checked():
            value = _budget.get()
            if value is not None:
                value.remaining()
            result = do()
            if value is not None:
                value.remaining()
            return result

        return super().call_with_retry(checked, fail, is_retryable)


class _DeadlineSocket:
    """Keep native RESP parsers, clipping every underlying read/write."""

    def __init__(self, sock, budget):
        self.sock = sock
        self.budget = budget
        self.policy_timeout = sock.gettimeout()

    def __getattr__(self, name):
        return getattr(self.sock, name)

    def gettimeout(self):
        return self.policy_timeout

    def settimeout(self, timeout):
        self.policy_timeout = timeout
        self.sock.settimeout(timeout)

    def setblocking(self, flag):
        self.settimeout(None if flag else 0)

    def _io(self, method, *args, **kwargs):
        try:
            if _budget.get() is not self.budget:
                raise ValueError("accepted Redis socket is outside its owning task scope")
            remaining = self.budget.remaining()
            limit = remaining if self.policy_timeout is None else min(self.policy_timeout, remaining)
            self.sock.settimeout(limit)
            try:
                result = getattr(self.sock, method)(*args, **kwargs)
            except socket.timeout:
                self.budget.remaining()
                raise
            self.budget.remaining()
            return result
        except (AcceptedChatTaskDeadlineExceeded, ValueError):
            self.sock.close()
            raise

    def recv(self, *args, **kwargs):
        return self._io("recv", *args, **kwargs)

    def recv_into(self, *args, **kwargs):
        return self._io("recv_into", *args, **kwargs)

    def send(self, *args, **kwargs):
        return self._io("send", *args, **kwargs)

    def sendall(self, *args, **kwargs):
        return self._io("sendall", *args, **kwargs)


class _HandshakeSocket(_DeadlineSocket):
    def gettimeout(self):
        # SSL reads the socket timeout after certificate/context setup and
        # takes ownership by detach(). Do not give the handshake a stale limit.
        try:
            remaining = self.budget.remaining()
        except (AcceptedChatTaskDeadlineExceeded, ValueError):
            self.sock.close()
            raise
        return remaining if self.policy_timeout is None else min(self.policy_timeout, remaining)



_DNS_PROGRAM = """
import json,socket,sys
host,port,family=json.load(sys.stdin)
try:
    result={'addresses':socket.getaddrinfo(host,port,family,socket.SOCK_STREAM)}
except OSError as error:
    result={'error':str(error)}
print(json.dumps(result))
"""


def _addresses(connection, budget):
    budget.remaining()
    try:
        numeric = ipaddress.ip_address(connection.host)
    except ValueError:
        numeric = None
    # Zone-qualified IPv6 needs the resolver's numeric scope-id tuple.
    if numeric is not None and getattr(numeric, "scope_id", None) is not None:
        numeric = None
    if numeric is not None:
        family = socket.AF_INET6 if numeric.version == 6 else socket.AF_INET
        if connection.socket_type not in (0, family):
            raise RedisConnectionError("Redis address family does not match numeric host")
        address = (str(numeric), connection.port)
        if family == socket.AF_INET6:
            address += (0, 0)
        return [(family, socket.SOCK_STREAM, 0, "", address)]

    policy = connection.socket_connect_timeout
    started = time.monotonic()
    child = subprocess.Popen(
        [sys.executable, "-I", "-c", _DNS_PROGRAM],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        remaining = budget.remaining()
        limit = remaining if policy is None else min(remaining, max(0, policy - (time.monotonic()-started)))
        try:
            output, _ = child.communicate(
                json.dumps([connection.host, connection.port, connection.socket_type]),
                timeout=limit,
            )
        except subprocess.TimeoutExpired:
            budget.remaining()
            raise RedisTimeoutError("Timeout resolving Redis host") from None
        budget.remaining()
        if child.returncode:
            raise RedisConnectionError("Redis hostname resolver failed")
        result = json.loads(output)
        if "error" in result:
            raise RedisConnectionError(result["error"])
        return result["addresses"]
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()
        child.stdin.close()
        child.stdout.close()


def _connect_socket(connection, budget):
    error = None
    for family, socktype, proto, _canonical, address in _addresses(connection, budget):
        budget.remaining()
        sock = socket.socket(family, socktype, proto)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if connection.socket_keepalive:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                for key, value in connection.socket_keepalive_options.items():
                    sock.setsockopt(socket.IPPROTO_TCP, key, value)
            remaining = budget.remaining()
            policy = connection.socket_connect_timeout
            sock.settimeout(remaining if policy is None else min(policy, remaining))
            sock.connect(tuple(address))
            budget.remaining()
            policy = connection.socket_timeout
            sock.settimeout(policy)
            return sock
        except OSError as exc:
            error = exc
            sock.close()
            budget.remaining()
        except BaseException:
            sock.close()
            raise
    if error is not None:
        raise error
    raise RedisConnectionError("Redis hostname resolver returned no addresses")


class _AcceptedOwner:
    def __init__(self, *args, _accepted_budget, **kwargs):
        self.accepted_budget = _accepted_budget
        super().__init__(*args, **kwargs)

    def _owner_budget(self):
        budget = _budget.get()
        if budget is not self.accepted_budget:
            raise ValueError("accepted Redis client is outside its owning task scope")
        budget.remaining()
        return budget


class AcceptedDeadlineConnection(_AcceptedOwner, Connection):
    def _connect(self):
        budget = self._owner_budget()
        return _DeadlineSocket(_connect_socket(self, budget), budget)


class AcceptedDeadlineSSLConnection(_AcceptedOwner, SSLConnection):
    def _connect(self):
        budget = self._owner_budget()
        if self.ssl_validate_ocsp or self.ssl_validate_ocsp_stapled:
            raise RedisConnectionError("Accepted Redis deadline cannot bound external OCSP validation")
        sock = _connect_socket(self, budget)
        try:
            remaining = budget.remaining()
            policy = self.socket_timeout
            sock.settimeout(remaining if policy is None else min(policy, remaining))
            sock = self._wrap_socket_with_ssl(_HandshakeSocket(sock, budget))
            budget.remaining()
            sock.settimeout(policy)
            return _DeadlineSocket(sock, budget)
        except BaseException:
            sock.close()
            budget.remaining()
            raise


def scoped_redis_client(factory, *, synthetic=False):
    """Keep accepted pools local; legacy/global clients remain untouched."""
    value = _budget.get()
    if value is None:
        return None
    value.remaining()
    if value.client is None:
        client = factory()
        pool = getattr(client, "connection_pool", None)
        if not isinstance(pool, ConnectionPool):
            if not synthetic:
                raise RedisConnectionError("Accepted Redis deadline requires a native connection pool")
        else:
            classes = {Connection: AcceptedDeadlineConnection, SSLConnection: AcceptedDeadlineSSLConnection}
            if pool.connection_class not in classes:
                client.close()
                pool.disconnect()
                raise RedisConnectionError("Accepted Redis connection policy is unsupported")
            pool.connection_class = classes[pool.connection_class]
            pool.connection_kwargs["_accepted_budget"] = value
            retry = pool.connection_kwargs["retry"]
            pool.connection_kwargs["retry"] = _BoundedRetry(
                _BoundedBackoff(copy.deepcopy(retry._backoff)),
                retry._retries, retry._supported_errors,
            )
        value.client = client
    return value.client
