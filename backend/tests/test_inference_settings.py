"""Request settings tests: no credentials, network, model weights or real database.

The runtime classes/functions are compiled from their source AST so that module-level
production model/DB initialization is not executed. Agent cloning uses the real SDK.
"""

import ast
import asyncio
import json
import re
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import AsyncIterator, List, Optional

import httpx
from agents import Agent
from app.services.inference_settings import parse_settings, settings_catalog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

APP = Path(__file__).resolve().parents[1] / "app"


def load_definitions(relative_path, names, namespace):
    tree = ast.parse((APP / relative_path).read_text())
    selected = [
        n
        for n in tree.body
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name in names
    ]
    for n in selected:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            n.decorator_list = []
    exec(
        compile(
            ast.Module(body=selected, type_ignores=[]), str(APP / relative_path), "exec"
        ),
        namespace,
    )
    return namespace


def agent_class():
    namespace = {
        "Agent": Agent,
        "replace": replace,
        "AsyncIterator": AsyncIterator,
        "ResearchAgent": object,
        "LifePlanningAgent": object,
        "LocationAgent": object,
        "get_president_persona": lambda: "学長として対話してください。",
        "get_current_time": lambda: "time",
        "get_weather": lambda: "weather",
        "ENDOGENOUS_FILLER_INSTRUCTION": "学長のフィラー",
        "CEREMONY_ENDOGENOUS_FILLER_INSTRUCTION": "式典のフィラー",
    }
    return load_definitions(
        "agent/general_conversation/agent.py", {"GeneralConversationAgent"}, namespace
    )["GeneralConversationAgent"]


class SettingsValidationTests(unittest.TestCase):
    def test_defaults_and_request_isolation(self):
        defaults = parse_settings({})
        selected = parse_settings(
            {
                "llm_model": "gpt-4o",
                "temperature": "0",
                "max_tokens": "256",
                "rag_top_k": "12",
                "rag_threshold": "0.7",
                "tts_voice": "2",
            }
        )
        self.assertIsNone(defaults.temperature)
        self.assertIsNone(defaults.max_tokens)
        self.assertEqual(
            (defaults.rag_top_k, defaults.rag_threshold, defaults.tts_voice),
            (5, 0.25, 0),
        )
        self.assertEqual(
            (selected.temperature, selected.max_tokens, selected.tts_voice), (0, 256, 2)
        )
        with self.assertRaises(ValidationError):
            selected.max_tokens = 99
        self.assertEqual(parse_settings({}), defaults)

    def test_rejects_invalid_or_unsupported_settings(self):
        cases = [
            {"temperature": "NaN"},
            {"temperature": "Infinity"},
            {"llm_model": "gpt-4o", "temperature": "-0.1"},
            {"llm_model": "gpt-4o", "temperature": "2.1"},
            {"temperature": "0.5"},
            {"llm_model": "not-allowed"},
            {"filler_model": "not-allowed"},
            {"max_tokens": "0"},
            {"max_tokens": "4097"},
            {"max_tokens": "1.5"},
            {"rag_top_k": "0"},
            {"rag_top_k": "21"},
            {"rag_threshold": "nan"},
            {"rag_threshold": "1.1"},
            {"tts_voice": "-1"},
            {"tts_voice": "name-not-id"},
            {"mode": "invalid"},
            {"filler_mode": "invalid"},
        ]
        for query in cases:
            with self.subTest(query=query), self.assertRaises(ValueError):
                parse_settings(query)

    def test_token_limit_respects_responses_api_minimum(self):
        with self.assertRaises(ValidationError):
            parse_settings({"max_tokens": "15"})
        self.assertEqual(parse_settings({"max_tokens": "16"}).max_tokens, 16)
        catalog = settings_catalog([], [])
        self.assertEqual(catalog["limits"]["max_tokens"], {"min": 16, "max": 4096})

    def test_filler_compatibility_and_catalog(self):
        self.assertEqual(parse_settings({"filler_enabled": "false"}).filler_mode, "off")
        self.assertEqual(
            parse_settings(
                {"filler_enabled": "false", "filler_mode": "static"}
            ).filler_mode,
            "static",
        )
        catalog = settings_catalog(
            [{"id": "2", "label": "話者"}],
            [{"id": "browser", "label": "ブラウザ", "available": True}],
        )
        self.assertEqual(catalog["defaults"]["tts_voice"], "2")
        self.assertEqual(
            {m["id"] for m in catalog["modes"]}, {"general", "assistant", "ceremony"}
        )
        self.assertFalse(
            next(m for m in catalog["llm_models"] if m["id"] == "gpt-5.2")[
                "supports_temperature"
            ]
        )


class AgentSettingsTests(unittest.TestCase):
    def test_real_sdk_clone_keeps_other_requests_and_handoffs_unchanged(self):
        klass = agent_class()
        domain = Agent(name="Domain", model="gpt-5.2")
        agent = klass(domain, domain, domain)
        default = agent._resolve_agent("general", "none")
        first = agent._resolve_agent("general", "none", "gpt-4o", 0.1, 256)
        second = agent._resolve_agent("general", "none", "gpt-4o-mini", 1.5, 512)
        self.assertEqual(
            (
                first.model,
                first.model_settings.temperature,
                first.model_settings.max_tokens,
            ),
            ("gpt-4o", 0.1, 256),
        )
        self.assertEqual(
            (
                second.model,
                second.model_settings.temperature,
                second.model_settings.max_tokens,
            ),
            ("gpt-4o-mini", 1.5, 512),
        )
        self.assertIsNone(default.model_settings.temperature)
        self.assertIsNone(default.model_settings.max_tokens)
        self.assertIs(agent._resolve_agent("general", "none"), default)
        self.assertIs(first.handoffs[0], domain)
        self.assertEqual(domain.model, "gpt-5.2")

    def test_neutral_assistant_has_no_president_handoffs(self):
        klass = agent_class()
        domain = Agent(name="Domain")
        agent = klass(domain, domain, domain)
        neutral = agent._resolve_agent(
            "assistant", "endogenous", "gpt-4o-mini", 0.2, 128
        )
        self.assertEqual(neutral.name, "AssistantAgent")
        self.assertEqual(neutral.handoffs, [])
        self.assertIn("名乗らず", neutral.instructions)
        self.assertNotIn("学長のフィラー", neutral.instructions)
        self.assertIs(agent._resolve_agent("ceremony", "none"), agent.ceremony_agent)


class FakeDaily:
    def __init__(self, delay=0):
        self.delay = delay
        self.calls = []

    async def stream_generate(self, **kwargs):
        self.calls.append(kwargs)
        await asyncio.sleep(self.delay)
        yield "会話。"


class FakeRag:
    def __init__(self):
        self.calls = []

    async def run_stream(self, **kwargs):
        self.calls.append(kwargs)
        yield "検索結果。"


class FakeClassifier:
    def __init__(self, route):
        self.route = route
        self.calls = 0

    async def classify_rag_vs_dialogue(self, text):
        self.calls += 1
        return self.route


def orchestrator_class():
    namespace = {
        "asyncio": asyncio,
        "time": time,
        "AsyncIterator": AsyncIterator,
        "Optional": Optional,
        "GeneralConversationAgent": object,
        "LLMDecisionClassifier": object,
        "RAGModule": object,
        "BaseLLM": object,
        "OpenAILLM": object,
    }
    return load_definitions(
        "agent/response_orchestrator.py", {"ResponseOrchestrator"}, namespace
    )["ResponseOrchestrator"]


class PropagationTests(unittest.IsolatedAsyncioTestCase):
    async def test_rag_and_dialogue_both_fast_and_slow_paths(self):
        klass = orchestrator_class()
        for route in ("rag", "dialogue"):
            for delay in (0, 0.01):
                with self.subTest(route=route, delay=delay):
                    rag, daily, classifier = (
                        FakeRag(),
                        FakeDaily(delay),
                        FakeClassifier(route),
                    )
                    orchestrator = klass(
                        rag, daily, object(), classifier, filler_timeout=0.001
                    )
                    history = [{"role": "user", "content": "以前の質問"}]
                    result = [
                        part
                        async for part in orchestrator.stream_response(
                            "test",
                            "質問",
                            history=history,
                            filler_mode="off",
                            llm_model="gpt-4o",
                            temperature=0.4,
                            max_tokens=321,
                            rag_top_k=7,
                            rag_threshold=0.6,
                        )
                    ]
                    self.assertEqual(daily.calls[0]["temperature"], 0.4)
                    self.assertEqual(daily.calls[0]["max_tokens"], 321)
                    self.assertEqual(daily.calls[0]["history"], history)
                    if route == "rag":
                        self.assertEqual(result, ["検索結果。"])
                        self.assertEqual(
                            rag.calls[0],
                            {
                                "query": "質問",
                                "top_k": 7,
                                "threshold": 0.6,
                                "temperature": 0.4,
                                "max_tokens": 321,
                            },
                        )
                    else:
                        self.assertEqual(result, ["会話。"])
                        self.assertEqual(rag.calls, [])
                    # A subsequent request gets defaults, not the previous request's values.
                    _ = [
                        part
                        async for part in orchestrator.stream_response(
                            "other", "別の質問", filler_mode="off"
                        )
                    ]
                    self.assertIsNone(daily.calls[-1]["temperature"])
                    self.assertIsNone(daily.calls[-1]["max_tokens"])
                    if route == "rag":
                        self.assertEqual(
                            (rag.calls[-1]["top_k"], rag.calls[-1]["threshold"]),
                            (5, 0.25),
                        )

    async def test_neutral_mode_does_not_call_president_classifier_or_rag(self):
        rag, daily, classifier = FakeRag(), FakeDaily(), FakeClassifier("rag")
        orchestrator = orchestrator_class()(rag, daily, object(), classifier)
        output = [
            part
            async for part in orchestrator.stream_response(
                "user",
                "学内について",
                mode="assistant",
                filler_mode="dynamic",
                max_tokens=200,
            )
        ]
        self.assertEqual(output, ["会話。"])
        self.assertEqual(classifier.calls, 0)
        self.assertEqual(rag.calls, [])
        self.assertEqual(daily.calls[0]["mode"], "assistant")
        self.assertEqual(daily.calls[0]["filler_mode"], "none")

    async def test_rag_generation_passes_values_without_mutating_defaults(self):
        namespace = {
            "AsyncIterator": AsyncIterator,
            "Optional": Optional,
            "List": List,
            "Dict": dict,
            "Any": object,
            "BaseLLM": object,
            "Retriever": object,
            "Path": Path,
        }
        klass = load_definitions(
            "agent/modules/rag_module.py", {"RAGModule"}, namespace
        )["RAGModule"]
        calls = []

        class LLM:
            async def stream_generate(self, **kwargs):
                calls.append(kwargs)
                yield "answer"

        search_calls = []
        retriever = SimpleNamespace(
            search=lambda *a, **kw: search_calls.append((a, kw)) or []
        )
        rag = klass(retriever, LLM())
        rag.build_prompt = lambda *a: "prompt"
        _ = [
            x
            async for x in rag.run_stream(
                "test", top_k=8, threshold=0.8, temperature=0, max_tokens=999
            )
        ]
        self.assertEqual((calls[-1]["temperature"], calls[-1]["max_tokens"]), (0, 999))
        self.assertEqual(search_calls[-1][1], {"top_k": 8, "threshold": 0.8})
        _ = [x async for x in rag.run_stream("next")]
        self.assertEqual(
            (calls[-1]["temperature"], calls[-1]["max_tokens"]), (0.7, 200)
        )
        self.assertEqual((rag.temperature, rag.max_tokens), (0.7, 200))


class RouteTests(unittest.IsolatedAsyncioTestCase):
    def setup_namespace(self):
        history_calls, audio_calls = [], []

        class TTS:
            def get_available_speakers(self):
                return [{"id": "0", "label": "既定"}, {"id": "2", "label": "追加"}]

            def synthesize_with_visemes_to_base64(self, text, speaker_id=0):
                audio_calls.append(speaker_id)
                return {"audio": "test-audio", "visemes": []}

        class History:
            def get_recent_history(self, **kwargs):
                history_calls.append(("get", kwargs))
                return []

            def save_message(self, **kwargs):
                history_calls.append(("save", kwargs))

        class Orchestrator:
            def __init__(self):
                self.calls = []

            async def stream_response(self, **kwargs):
                self.calls.append(kwargs)
                yield "確認。"
                yield "末尾"

        orchestrator = Orchestrator()
        ns = {
            "asyncio": asyncio,
            "time": time,
            "json": json,
            "re": re,
            "Request": Request,
            "HTTPException": HTTPException,
            "ValidationError": ValidationError,
            "StreamingResponse": StreamingResponse,
            "parse_settings": parse_settings,
            "tts": TTS(),
            "history_service": History(),
            "conversation_orchestrator": orchestrator,
            "_sanitize_for_speech": lambda text: text,
        }
        ns = load_definitions(
            "routers/text_chat_router.py",
            {
                "char_stream_orchestrator",
                "_available_tts_voices",
                "_synthesize_audio_packet",
            },
            ns,
        )
        return ns, history_calls, audio_calls, orchestrator

    async def test_validation_happens_before_history_or_inference(self):
        from urllib.parse import urlencode

        for query in (
            {"max_tokens": "0"},
            {"max_tokens": "15"},
            {"tts_voice": "9"},
            {"temperature": "nan"},
            {"tts_provider": "other"},
        ):
            ns, history, audio, orchestrator = self.setup_namespace()
            request = Request(
                {"type": "http", "query_string": urlencode(query).encode()}
            )
            with self.subTest(query=query), self.assertRaises(HTTPException) as raised:
                await ns["char_stream_orchestrator"](request)
            self.assertEqual(raised.exception.status_code, 422)
            self.assertEqual((history, audio, orchestrator.calls), ([], [], []))

    async def test_nonfinite_validation_errors_are_json_serializable(self):
        ns, history, audio, orchestrator = self.setup_namespace()
        app = FastAPI()
        app.get("/stream")(ns["char_stream_orchestrator"])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            for key in ("temperature", "rag_threshold"):
                for value in ("nan", "NaN", "Infinity", "-Infinity"):
                    response = await client.get("/stream", params={key: value})
                    self.assertEqual(response.status_code, 422)
                    self.assertIn("detail", response.json())
        self.assertEqual((history, audio, orchestrator.calls), ([], [], []))

    async def test_omitted_voice_uses_catalog_default(self):
        ns, history, audio, orchestrator = self.setup_namespace()
        ns["tts"].get_available_speakers = lambda: [{"id": "2", "label": "追加"}]
        request = Request({"type": "http", "query_string": b"text=test"})
        response = await ns["char_stream_orchestrator"](request)
        _ = [part async for part in response.body_iterator]
        self.assertEqual(audio, [2, 2])

    async def test_route_passes_settings_and_voice_to_every_chunk(self):
        from urllib.parse import urlencode

        ns, history, audio, orchestrator = self.setup_namespace()
        query = {
            "text": "質問",
            "llm_model": "gpt-4o",
            "temperature": "0.2",
            "max_tokens": "333",
            "rag_top_k": "9",
            "rag_threshold": "0.9",
            "tts_voice": "2",
        }
        request = Request({"type": "http", "query_string": urlencode(query).encode()})
        response = await ns["char_stream_orchestrator"](request)
        packets = [
            json.loads(part.removeprefix("data: "))
            async for part in response.body_iterator
        ]
        self.assertEqual(audio, [2, 2])
        call = orchestrator.calls[0]
        self.assertEqual(
            (
                call["temperature"],
                call["max_tokens"],
                call["rag_top_k"],
                call["rag_threshold"],
            ),
            (0.2, 333, 9, 0.9),
        )
        self.assertEqual(packets[-1]["type"], "done")
        self.assertEqual(len([p for p in packets if p["type"] == "audio_chunk"]), 2)
        self.assertEqual(len(history), 3)


if __name__ == "__main__":
    unittest.main()
