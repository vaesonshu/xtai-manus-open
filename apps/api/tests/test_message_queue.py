"""消息队列与 Redis Stream Task 测试。"""

from __future__ import annotations

import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from infrastructure.message_queue.in_memory_message_queue import InMemoryMessageQueue
from infrastructure.message_queue.redis_stream_message_queue import RedisStreamMessageQueue
from infrastructure.redis.async_client import AsyncRedisClient
from infrastructure.task.redis_stream_task import RedisStreamTask


@pytest.fixture
def fake_async_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def redis_queue(fake_async_redis: FakeAsyncRedis) -> RedisStreamMessageQueue:
    client = AsyncRedisClient()
    client.bind_client(fake_async_redis)
    queue = RedisStreamMessageQueue("test:stream", client)
    return queue


@pytest.mark.asyncio
async def test_in_memory_message_queue_put_get_pop() -> None:
    queue = InMemoryMessageQueue()
    message_id = await queue.put({"event": "hello"})
    assert message_id

    read_id, payload = await queue.get()
    assert read_id == message_id
    assert payload == {"event": "hello"}

    pop_id, pop_payload = await queue.pop()
    assert pop_id == message_id
    assert pop_payload == {"event": "hello"}
    assert await queue.is_empty() is True


@pytest.mark.asyncio
async def test_redis_stream_message_queue_roundtrip(redis_queue: RedisStreamMessageQueue) -> None:
    message_id = await redis_queue.put("ping")
    assert message_id

    read_id, payload = await redis_queue.get()
    assert read_id == message_id
    assert payload == "ping"
    assert await redis_queue.size() == 1

    pop_id, pop_payload = await redis_queue.pop()
    assert pop_id == message_id
    assert pop_payload == "ping"
    assert await redis_queue.is_empty() is True


@pytest.mark.asyncio
async def test_redis_stream_message_queue_clear_and_delete(redis_queue: RedisStreamMessageQueue) -> None:
    first_id = await redis_queue.put("a")
    second_id = await redis_queue.put("b")
    assert await redis_queue.size() == 2

    assert await redis_queue.delete_message(first_id) is True
    assert await redis_queue.size() == 1

    await redis_queue.clear()
    assert await redis_queue.is_empty() is True
    assert await redis_queue.get_latest_id() == "0"
    assert second_id  # 避免未使用告警


@pytest.mark.asyncio
async def test_redis_stream_task_registry_and_streams(fake_async_redis: FakeAsyncRedis) -> None:
    class EchoRunner:
        def __init__(self) -> None:
            self.done_called = False

        async def invoke(self, task: RedisStreamTask) -> None:
            message_id, payload = await task.input_stream.get()
            assert message_id is not None
            await task.output_stream.put({"echo": payload})

        async def destroy(self) -> None:
            return None

        async def on_done(self, task: RedisStreamTask) -> None:
            self.done_called = True

    runner = EchoRunner()
    task = RedisStreamTask.create(runner)
    assert isinstance(task, RedisStreamTask)

    # 注入 fakeredis，避免依赖真实 Redis
    task.input_stream.bind_redis(fake_async_redis)  # type: ignore[attr-defined]
    task.output_stream.bind_redis(fake_async_redis)  # type: ignore[attr-defined]

    assert RedisStreamTask.get(task.task_id) is task
    await task.input_stream.put("hello")
    await task.invoke()

    # 等待后台任务完成
    for _ in range(50):
        if runner.done_called:
            break
        await asyncio.sleep(0.01)

    assert runner.done_called is True
    _, output = await task.output_stream.get()
    assert output == {"echo": "hello"}
    assert RedisStreamTask.get(task.task_id) is None

    await RedisStreamTask.destroy()
