"""Opt-in regression safety: -p tests.support.budget_network_guard.

No external DNS or sockets, including proxies. Only literal loopback addresses,
localhost, and Unix domain sockets are available to local test services.
"""

import ipaddress
import socket


def _local(host):
    if isinstance(host, bytes):
        host = host.decode("ascii")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


def pytest_configure(config):
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_getaddrinfo = socket.getaddrinfo
    original_sendto = socket.socket.sendto

    def validate(sock, address):
        if sock.family != socket.AF_UNIX and (
            not isinstance(address, tuple) or not _local(address[0])
        ):
            raise RuntimeError("External network forbidden by budget regression guard")

    def connect(sock, address):
        validate(sock, address)
        return original_connect(sock, address)

    def connect_ex(sock, address):
        validate(sock, address)
        return original_connect_ex(sock, address)

    def getaddrinfo(host, *args, **kwargs):
        if host is not None and not _local(host):
            raise RuntimeError("External DNS forbidden by budget regression guard")
        return original_getaddrinfo(host, *args, **kwargs)

    def sendto(sock, data, *args):
        validate(sock, args[-1])
        return original_sendto(sock, data, *args)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.socket.sendto = sendto
    socket.getaddrinfo = getaddrinfo
    # Do not allow environment-configured proxies to forward loopback traffic.
    import os

    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        os.environ.pop(key, None)
