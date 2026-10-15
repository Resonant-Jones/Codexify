"""Cancellable HTTP I/O for one accepted local stream's immutable envelope.

The synchronous parser waits on native async I/O, not an abandoned blocking
Requests thread. Each await inherits the same absolute monotonic deadline.
"""

import asyncio
import concurrent.futures
import threading
import time
from datetime import datetime, timezone

import httpx
from requests import exceptions as req_exc

from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadline,
    AcceptedChatTaskDeadlineExceeded,
)


class DeadlineResponse:
    def __init__(self, owner, response):
        self.owner = owner
        self.response = response
        self.status_code = response.status_code
        self.headers = response.headers
        self.lines = response.aiter_lines()

    def iter_lines(self, decode_unicode=False):
        while True:
            try:
                line = self.owner.call(self.lines.__anext__())
            except StopAsyncIteration:
                return
            yield line if decode_unicode else line.encode()

    @property
    def content(self):
        return self.owner.call(self.response.aread())

    @property
    def text(self):
        self.content
        return self.response.text

    def json(self):
        self.content
        return self.response.json()

    def close(self):
        self.owner.call(self.owner.close_response(self.response), terminal=True)


class AcceptedDeadlineTransport:
    def __init__(self, deadline: AcceptedChatTaskDeadline):
        anchor = time.monotonic()
        now = datetime.now(timezone.utc)
        self.work_limit = anchor + (deadline.work_deadline_at - now).total_seconds()
        self.terminal_limit = (
            anchor + (deadline.terminal_deadline_at - now).total_seconds()
        )
        if self.work_limit <= anchor:
            raise AcceptedChatTaskDeadlineExceeded()
        self.attempted = False
        self.client = None
        self.active_task = None
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(
            target=self.loop.run_forever, name="accepted-chat-http", daemon=True
        )
        self.thread.start()

    async def bounded(self, coroutine, terminal, child_limit):
        limit = self.terminal_limit if terminal else self.work_limit
        remaining = limit - time.monotonic()
        if remaining <= 0:
            coroutine.close()
            raise AcceptedChatTaskDeadlineExceeded(attempted=self.attempted)
        current = asyncio.current_task()
        if not terminal:
            self.active_task = current
        try:
            effective = (
                min(remaining, child_limit) if child_limit is not None else remaining
            )
            return await asyncio.wait_for(coroutine, timeout=effective)
        except asyncio.TimeoutError:
            if child_limit is not None and time.monotonic() < limit:
                raise req_exc.ReadTimeout(
                    "Provider control request timed out"
                ) from None
            raise AcceptedChatTaskDeadlineExceeded(attempted=self.attempted) from None
        finally:
            if self.active_task is current:
                self.active_task = None

    def call(self, coroutine, *, terminal=False, child_limit=None):
        future = asyncio.run_coroutine_threadsafe(
            self.bounded(coroutine, terminal, child_limit), self.loop
        )
        try:
            return future.result()
        except concurrent.futures.CancelledError:
            raise req_exc.ConnectionError("Local stream observation closed") from None
        except httpx.ConnectTimeout as exc:
            if not terminal and time.monotonic() >= self.work_limit:
                raise AcceptedChatTaskDeadlineExceeded(
                    attempted=self.attempted
                ) from None
            raise req_exc.ConnectTimeout(str(exc)) from exc
        except httpx.TimeoutException as exc:
            if not terminal and time.monotonic() >= self.work_limit:
                raise AcceptedChatTaskDeadlineExceeded(
                    attempted=self.attempted
                ) from None
            raise req_exc.ReadTimeout(str(exc)) from exc
        except httpx.RequestError as exc:
            raise req_exc.ConnectionError(str(exc)) from exc

    async def send(self, url, payload, headers, timeout):
        if self.client is None:
            self.client = httpx.AsyncClient()
        remaining = self.work_limit - time.monotonic()
        if remaining <= 0:
            raise AcceptedChatTaskDeadlineExceeded(attempted=self.attempted)
        connect, read = timeout
        policy = httpx.Timeout(min(read, remaining), connect=min(connect, remaining))
        request = self.client.build_request(
            "POST", url, json=payload, headers=headers, timeout=policy
        )
        self.attempted = True
        return await self.client.send(request, stream=True)

    def post(self, url, *, json, headers, stream, timeout):
        return DeadlineResponse(self, self.call(self.send(url, json, headers, timeout)))

    async def close_response(self, response):
        active = self.active_task
        if active is not None and active is not asyncio.current_task():
            active.cancel()
            await asyncio.gather(active, return_exceptions=True)
        await response.aclose()

    async def control_json(self, method, url, headers):
        if self.client is None:
            self.client = httpx.AsyncClient()
        response = await self.client.request(method, url, headers=headers, timeout=2)
        return response.json()

    def terminal_json(self, method, url, headers):
        return self.call(
            self.control_json(method, url, headers), terminal=True, child_limit=2
        )

    async def shutdown(self):
        active = self.active_task
        if active is not None:
            active.cancel()
            await asyncio.gather(active, return_exceptions=True)
        if self.client is not None:
            await self.client.aclose()
        await self.loop.shutdown_asyncgens()

    def close(self):
        try:
            self.call(self.shutdown(), terminal=True)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=max(0.01, self.terminal_limit - time.monotonic()))
            if self.thread.is_alive():
                raise RuntimeError("Accepted chat HTTP cleanup did not finish")
            self.loop.close()
