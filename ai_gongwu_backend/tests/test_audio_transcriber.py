"""Tests for ASR provider dispatch and FunASR result extraction."""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.media.audio_transcriber import (
    FunASRTranscriber,
    WhisperLocalTranscriber,
    _FUNASR_MODEL_CACHE,
    _WHISPER_MODEL_CACHE,
    get_transcriber,
)


class AudioTranscriberTestCase(unittest.TestCase):
    def setUp(self):
        _WHISPER_MODEL_CACHE.clear()
        _FUNASR_MODEL_CACHE.clear()

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


if __name__ == "__main__":
    unittest.main()
