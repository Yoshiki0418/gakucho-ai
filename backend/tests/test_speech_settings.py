"""Speech boundaries and speaker propagation without models, services or GPUs."""

import ast
import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

APP = Path(__file__).resolve().parents[1] / "app"
spec = importlib.util.spec_from_file_location(
    "speech_settings_test_target", APP / "services/speech_settings.py"
)
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


class SpeechSettingsTests(unittest.TestCase):
    def test_catalog_never_loads_models_and_reports_missing_checkpoints(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            speech.os.environ,
            {
                "WHISPER_CACHE_DIR": directory,
                "WHISPER_MODELS": "base,large-v3-turbo",
            },
        ), patch.object(
            speech.importlib.util, "find_spec", return_value=object()
        ), patch.object(
            speech.shutil, "which", return_value="ffmpeg"
        ):
            options = {item["id"]: item for item in speech.get_stt_options()}
            self.assertTrue(options["browser"]["available"])
            self.assertFalse(options["whisper-base"]["available"])
            Path(directory, "base.pt").touch()
            self.assertTrue(
                next(
                    item
                    for item in speech.get_stt_options()
                    if item["id"] == "whisper-base"
                )["available"]
            )
            self.assertEqual(
                speech.validate_whisper_model("whisper-base"),
                Path(directory, "base.pt"),
            )
            for invalid in ("browser", "../../secret", "whisper-../../secret", "base"):
                with self.assertRaises(speech.SpeechSettingsError):
                    speech.validate_whisper_model(invalid)
            with self.assertRaises(speech.SpeechSettingsError) as unavailable:
                speech.validate_whisper_model("whisper-large-v3")
            self.assertEqual(unavailable.exception.status_code, 503)

    def test_invalid_or_oversized_audio_is_rejected_before_decode(self):
        with patch.object(speech.subprocess, "run") as run:
            for payload in (b"", b"x" * (speech.MAX_UPLOAD_BYTES + 1)):
                with self.assertRaises(speech.SpeechSettingsError):
                    speech.decode_audio(payload)
            run.assert_not_called()

    def test_audio_duration_limit_is_enforced_after_bounded_decode(self):
        for seconds, accepted in ((1, True), (60, True), (61, False)):
            output = np.zeros(seconds * speech.SAMPLE_RATE, dtype=np.float32).tobytes()
            with patch.object(
                speech.subprocess,
                "run",
                return_value=types.SimpleNamespace(returncode=0, stdout=output),
            ) as run:
                if accepted:
                    self.assertEqual(
                        len(speech.decode_audio(b"recording")),
                        seconds * speech.SAMPLE_RATE,
                    )
                else:
                    with self.assertRaises(speech.SpeechSettingsError) as error:
                        speech.decode_audio(b"recording")
                    self.assertEqual(error.exception.status_code, 413)
                args = run.call_args.args[0]
                self.assertIn("61", args)
                self.assertEqual(args[args.index("-protocol_whitelist") + 1], "pipe")

    def test_corrupt_audio_and_decoder_timeout(self):
        failures = [
            types.SimpleNamespace(returncode=1, stdout=b""),
            types.SimpleNamespace(returncode=0, stdout=b"x"),
        ]
        for result in failures:
            with patch.object(
                speech.subprocess, "run", return_value=result
            ), self.assertRaises(speech.SpeechSettingsError):
                speech.decode_audio(b"recording")
        with patch.object(
            speech.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired("ffmpeg", 20),
        ), self.assertRaises(speech.SpeechSettingsError):
            speech.decode_audio(b"recording")

    def test_whisper_uses_checkpoint_path_and_serializes_inference(self):
        speech._loaded_key = None
        speech._loaded_model = None
        engine = types.SimpleNamespace(
            transcribe=Mock(return_value={"text": " example "})
        )
        whisper = types.SimpleNamespace(load_model=Mock(return_value=engine))
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory, "base.pt")
            checkpoint.touch()
            with patch.object(
                speech, "validate_whisper_model", return_value=checkpoint
            ), patch.object(
                speech, "decode_audio", return_value=np.zeros(16)
            ), patch.dict(
                sys.modules, {"whisper": whisper}
            ), patch.dict(
                speech.os.environ, {"WHISPER_DEVICE": "cpu"}
            ):
                self.assertEqual(
                    speech.transcribe_audio(b"recording", "whisper-base"), "example"
                )
                speech.transcribe_audio(b"recording", "whisper-base")
                whisper.load_model.assert_called_once_with(
                    str(checkpoint), device="cpu"
                )
                self.assertFalse(engine.transcribe.call_args.kwargs["fp16"])
                speech._inference_lock.acquire()
                try:
                    with self.assertRaises(speech.SpeechSettingsError) as busy:
                        speech.transcribe_audio(b"recording", "whisper-base")
                    self.assertEqual(busy.exception.status_code, 429)
                finally:
                    speech._inference_lock.release()


class FakeTensor:
    def __init__(self, data):
        self.data = np.asarray(data)

    def to(self, _device):
        return self

    def unsqueeze(self, axis):
        return FakeTensor(np.expand_dims(self.data, axis))

    def size(self, axis):
        return self.data.shape[axis]

    def __getitem__(self, key):
        return FakeTensor(self.data[key])

    def detach(self):
        return self

    def cpu(self):
        return self

    def float(self):
        return self

    def numpy(self):
        return self.data


class SpeakerTests(unittest.TestCase):
    def setUp(self):
        source = ast.parse((APP / "models/tts/style_bert_vits2_tts.py").read_text())
        cls = next(
            node
            for node in source.body
            if isinstance(node, ast.ClassDef) and node.name == "StyleBertVITS2_TTS"
        )
        namespace = {
            "BaseTTS": object,
            "Path": Path,
            "Optional": object(),
            "np": np,
            "sf": types.SimpleNamespace(
                write=lambda target, *_args, **_kwargs: target.write(b"RIFF")
            ),
            "io": io,
            "base64": __import__("base64"),
            "Languages": types.SimpleNamespace(JP="JP"),
            "DEFAULT_SDP_RATIO": 0.2,
            "DEFAULT_NOISE": 0.6,
            "DEFAULT_NOISEW": 0.8,
        }
        # Preserve the real class bodies; avoid heavyweight module imports.
        exec(
            compile("from __future__ import annotations\n", "future", "exec"), namespace
        )
        module = ast.Module(
            body=[
                ast.ImportFrom(
                    module="__future__", names=[ast.alias(name="annotations")], level=0
                ),
                cls,
            ],
            type_ignores=[],
        )
        ast.fix_missing_locations(module)
        exec(compile(module, "style_bert_vits2_tts.py", "exec"), namespace)
        self.namespace = namespace
        self.tts = namespace["StyleBertVITS2_TTS"].__new__(
            namespace["StyleBertVITS2_TTS"]
        )
        self.model = types.SimpleNamespace(
            hyper_parameters=types.SimpleNamespace(
                version="2.0-JP-Extra",
                data=types.SimpleNamespace(
                    spk2id={"first": 0, "second": 2},
                    add_blank=False,
                    sampling_rate=16000,
                ),
            ),
            infer=Mock(return_value=(16000, np.zeros(320))),
            device="cpu",
            style2id={"Neutral": 0},
        )
        self.tts.tts_model = self.model

    def test_speaker_catalog_and_plain_synthesis_do_not_mutate_default(self):
        self.assertEqual(
            self.tts.get_available_speakers(),
            [{"id": "0", "label": "first"}, {"id": "2", "label": "second"}],
        )
        self.tts.synthesize_to_base64("test", speaker_id=2)
        self.tts.synthesize_to_base64("test")
        self.assertEqual(
            [call.kwargs["speaker_id"] for call in self.model.infer.call_args_list],
            [2, 0],
        )
        for invalid in (1, -1, True, "2"):
            with self.assertRaises(ValueError):
                self.tts._synthesize("test", speaker_id=invalid)

    def test_aligned_synthesis_passes_selected_id_into_neural_network(self):
        neural = types.SimpleNamespace(
            infer=Mock(
                return_value=(
                    FakeTensor(np.zeros((1, 1, 320))),
                    FakeTensor(np.ones((1, 1, 2, 2))),
                )
            )
        )
        self.model._TTSModel__net_g = neural
        self.model._TTSModel__get_style_vector = lambda *_: np.zeros(2)
        self.model._TTSModel__convert_to_16_bit_wav = lambda audio: audio.astype(
            np.int16
        )
        self.namespace.update(
            {
                "torch": types.SimpleNamespace(
                    no_grad=contextlib.nullcontext,
                    LongTensor=FakeTensor,
                    from_numpy=FakeTensor,
                    cuda=types.SimpleNamespace(is_available=lambda: False),
                ),
                "clean_text": lambda *_, **__: ("test", ["a", "i"], [], []),
                "infer_module": types.SimpleNamespace(
                    get_text=lambda *_: tuple(FakeTensor([1, 2]) for _ in range(6))
                ),
            }
        )
        result = self.tts.synthesize_with_visemes_to_base64("test", speaker_id=2)
        self.assertEqual(neural.infer.call_args.args[2].data.tolist(), [2])
        self.assertGreater(len(result["visemes"]), 0)
        self.assertAlmostEqual(result["duration"], 0.02)


class UploadRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_limits_and_close_on_all_paths(self):
        source = ast.parse((APP / "routers/speech_settings_router.py").read_text())
        fn = next(
            node for node in source.body if isinstance(node, ast.AsyncFunctionDef)
        )
        fn.decorator_list = []

        class HTTPException(Exception):
            def __init__(self, status_code, detail):
                self.status_code, self.detail = status_code, detail

        async def run(payload, invalid=False):
            closed = []

            async def read(size):
                return payload[:size]

            async def close():
                closed.append(True)

            async def direct_thread_call(fn, *args):
                return fn(*args)

            namespace = {
                "asyncio": types.SimpleNamespace(to_thread=direct_thread_call),
                "UploadFile": object,
                "File": lambda *_: None,
                "Form": lambda *_: None,
                "HTTPException": HTTPException,
                "MAX_UPLOAD_BYTES": speech.MAX_UPLOAD_BYTES,
                "SpeechSettingsError": speech.SpeechSettingsError,
                "validate_whisper_model": Mock(
                    side_effect=(
                        speech.SpeechSettingsError("unavailable", 503)
                        if invalid
                        else None
                    )
                ),
                "transcribe_audio": Mock(return_value="text"),
                "logger": Mock(),
            }
            exec(
                compile(
                    ast.Module(body=[fn], type_ignores=[]),
                    "speech_settings_router.py",
                    "exec",
                ),
                namespace,
            )
            try:
                result = await namespace["transcribe"](
                    types.SimpleNamespace(read=read, close=close), "whisper-base"
                )
                self.assertEqual(result, {"text": "text", "model": "whisper-base"})
            except HTTPException as error:
                namespace["transcribe_audio"].assert_not_called()
                self.assertIn(error.status_code, (400, 413, 503))
            self.assertEqual(closed, [True])

        await run(b"audio")
        await run(b"")
        await run(b"x" * (speech.MAX_UPLOAD_BYTES + 1))
        await run(b"audio", invalid=True)


if __name__ == "__main__":
    unittest.main()
