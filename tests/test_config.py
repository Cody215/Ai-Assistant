# tests/test_config.py
"""
Tests for config loading and validation.

Uses monkeypatch to control environment variables without
touching the real .env file.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigValidation:

    def test_missing_gemini_key_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY",    raising=False)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        # Mock load_dotenv so it doesn't load from .env file
        monkeypatch.setattr("config.load_dotenv", lambda: None)
        from config import load_config
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            load_config()

    def test_missing_elevenlabs_key_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY",    "fake-gemini-key")
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        # Mock load_dotenv so it doesn't load from .env file
        monkeypatch.setattr("config.load_dotenv", lambda: None)
        from config import load_config
        with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
            load_config()

    def test_both_keys_present_loads_successfully(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY",    "fake-gemini-key")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-eleven-key")
        from config import load_config
        cfg = load_config()
        assert cfg.gemini_api_key    == "fake-gemini-key"
        assert cfg.elevenlabs_api_key == "fake-eleven-key"

    def test_keys_are_stripped_of_whitespace(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY",    "  fake-key-with-spaces  ")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "  another-key  ")
        from config import load_config
        cfg = load_config()
        assert cfg.gemini_api_key    == "fake-key-with-spaces"
        assert cfg.elevenlabs_api_key == "another-key"


class TestConfigDefaults:

    @pytest.fixture
    def cfg(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY",    "fake-key")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-key")
        from config import load_config
        return load_config()

    def test_default_gemini_model(self, cfg):
        assert "gemini" in cfg.gemini_model.lower()

    def test_default_stt_model(self, cfg):
        assert cfg.stt_model == "base.en"

    def test_default_ptt_key(self, cfg):
        assert cfg.ptt_key == "F9"

    def test_default_ptt_enabled(self, cfg):
        assert cfg.ptt_enabled is True

    def test_default_wake_word_enabled(self, cfg):
        # Wake word is now enabled by default in config.py
        assert cfg.wake_word_enabled is True

    def test_default_idle_checkin_minutes(self, cfg):
        assert isinstance(cfg.idle_checkin_minutes, int)
        assert cfg.idle_checkin_minutes >= 0

    def test_default_ollama_model(self, cfg):
        assert cfg.ollama_vision_model == "llava"

    def test_default_ollama_host(self, cfg):
        assert "localhost" in cfg.ollama_host
        assert "11434" in cfg.ollama_host

    def test_system_instruction_not_empty(self, cfg):
        assert len(cfg.system_instruction) > 100

    def test_system_instruction_contains_jarvis(self, cfg):
        assert "Jarvis" in cfg.system_instruction

    def test_memory_dir_is_path(self, cfg):
        from pathlib import Path
        assert isinstance(cfg.memory_dir, Path)
