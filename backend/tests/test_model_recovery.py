import unittest
import json
from unittest.mock import patch, AsyncMock
import httpx
from backend.app.chat import generate
from backend.config import settings

class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_cuda_failure_unloads_runner_before_retry(self):
        calls = []
        def respond(request):
            body = json.loads(request.content)
            calls.append(body)
            if len(calls) == 1:
                return httpx.Response(500, json={"error": "CUDA error: an illegal memory access was encountered"})
            if len(calls) == 2:
                return httpx.Response(200, json={"done": True})
            return httpx.Response(200, json={"response": "{}"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with patch('backend.app.chat.asyncio.sleep', new=AsyncMock()):
                self.assertEqual(await generate(client, 'test', {}, 'test'), '{}')
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1], {"model": calls[0]["model"], "keep_alive": 0})
        self.assertEqual(calls[0], calls[2])
        self.assertEqual(calls[0]["options"]["num_batch"], settings.llm_num_batch)

    async def test_persistent_cuda_failure_is_bounded(self):
        calls = []
        def respond(request):
            body = json.loads(request.content)
            calls.append(body)
            if "keep_alive" in body:
                return httpx.Response(200, json={"done": True})
            return httpx.Response(500, json={"error": "CUDA error"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with patch('backend.app.chat.asyncio.sleep', new=AsyncMock()):
                with self.assertRaises(httpx.HTTPStatusError):
                    await generate(client, 'test', {}, 'test')
        self.assertEqual(len(calls), 3)

    async def test_non_retryable_error_does_not_reset(self):
        calls = []
        def respond(request):
            calls.append(request)
            return httpx.Response(404, json={"error": "model not found"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with self.assertRaises(httpx.HTTPStatusError):
                await generate(client, 'test', {}, 'test')
        self.assertEqual(len(calls), 1)

    async def test_transient_server_error_retries_once(self):
        calls=[]
        def respond(request):
            calls.append(request)
            return httpx.Response(500,json={'error':'temporary'}) if len(calls)==1 else httpx.Response(200,json={'response':'{}'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with patch('backend.app.chat.asyncio.sleep',new=AsyncMock()):
                self.assertEqual(await generate(client,'test',{},'test'),'{}')
        self.assertEqual(len(calls),2)

    async def test_persistent_failure_is_bounded(self):
        calls=[]
        def respond(request):
            calls.append(request)
            return httpx.Response(500,json={'error':'unavailable'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with patch('backend.app.chat.asyncio.sleep',new=AsyncMock()):
                with self.assertRaises(httpx.HTTPStatusError):await generate(client,'test',{},'test')
        self.assertEqual(len(calls),2)
