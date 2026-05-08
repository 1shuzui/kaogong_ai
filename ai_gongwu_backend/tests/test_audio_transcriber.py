"""Tests for ASR provider dispatch and FunASR result extraction."""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch
import wave
from pathlib import Path
import uuid

from app.core.config import settings
from app.services.media.audio_transcriber import (
    FunASRTranscriber,
    WhisperLocalTranscriber,
    _FUNASR_MODEL_CACHE,
    _WHISPER_MODEL_CACHE,
    get_transcriber,
)
from app.services.media.video_processor import get_audio_duration_seconds, process_audio


class AudioTranscriberTestCase(unittest.TestCase):
    def setUp(self):
        _WHISPER_MODEL_CACHE.clear()
        _FUNASR_MODEL_CACHE.clear()
        self.temp_root = Path.cwd() / "storage" / "test_audio_transcriber"
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.created_paths: list[Path] = []

    def tearDown(self):
        for path in self.created_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def test_get_transcriber_returns_whisper(self):
        with patch.object(WhisperLocalTranscriber, "_load_model") as mock_load:
            _WHISPER_MODEL_CACHE[settings.WHISPER_MODEL_SIZE] = object()
            transcriber = get_transcriber("whisper")
            self.assertIsInstance(transcriber, WhisperLocalTranscriber)
            mock_load.assert_not_called()

    def test_get_transcriber_returns_funasr(self):
        cache_key = (
            settings.FUNASR_MODEL_NAME,
            settings.FUNASR_VAD_MODEL_NAME,
            settings.FUNASR_PUNC_MODEL_NAME,
            settings.ASR_DEVICE,
        )
        _FUNASR_MODEL_CACHE[cache_key] = object()
        transcriber = get_transcriber("funasr")
        self.assertIsInstance(transcriber, FunASRTranscriber)

    def test_unknown_provider_raises(self):
        with self.assertRaises(RuntimeError) as exc_info:
            get_transcriber("unknown")
        self.assertIn("unknown", str(exc_info.exception))

    def test_funasr_transcribe_extracts_text_from_list_payload(self):
        class StubAutoModel:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def generate(self, input):
                return [{"text": "你好，世界"}]

        funasr_module = types.ModuleType("funasr")
        funasr_module.AutoModel = StubAutoModel

        with patch.dict(sys.modules, {"funasr": funasr_module}):
            transcriber = FunASRTranscriber()
            text = transcriber.transcribe("dummy.wav")

        self.assertEqual(text, "你好，世界")

    def test_get_audio_duration_seconds_for_wav(self):
        wav_path = self.temp_root / f"duration_{uuid.uuid4().hex}.wav"
        self.created_paths.append(wav_path)
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 16000)

        duration = get_audio_duration_seconds(str(wav_path))

        self.assertIsNotNone(duration)
        assert duration is not None
        self.assertAlmostEqual(duration, 1.0, places=2)

    def test_process_audio_includes_duration_seconds(self):
        class StubTranscriber:
            def transcribe(self, audio_path: str, language=None) -> str:
                del audio_path, language
                return "这是一段音频作答"

        wav_path = self.temp_root / f"process_audio_{uuid.uuid4().hex}.wav"
        self.created_paths.append(wav_path)
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 8000)

        with patch("app.services.media.video_processor.get_transcriber", return_value=StubTranscriber()):
            result = process_audio(str(wav_path))

        self.assertEqual(result.source, "audio")
        self.assertEqual(result.transcript, "这是一段音频作答")
        self.assertIsNotNone(result.duration_seconds)
        assert result.duration_seconds is not None
        self.assertAlmostEqual(result.duration_seconds, 0.5, places=2)


if __name__ == "__main__":
    unittest.main()
