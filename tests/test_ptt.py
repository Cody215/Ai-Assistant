# tests/test_ptt.py
"""
Tests for push-to-talk key mapping and validation.
No actual keyboard hardware is used — just tests the config logic.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ptt import PushToTalk, KEY_MAP


class TestKeyMap:

    def test_key_map_not_empty(self):
        assert len(KEY_MAP) > 0

    def test_expected_keys_present(self):
        expected = {"F8", "F9", "F10", "ALT_R", "ALT_L",
                    "CTRL_R", "CTRL_L", "SHIFT_R", "SHIFT_L"}
        for key in expected:
            assert key in KEY_MAP, f"Expected key '{key}' not in KEY_MAP"


class TestPushToTalk:

    def test_valid_key_initialises(self):
        ptt = PushToTalk(key_name="F9")
        assert ptt.key_name == "F9"

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Unknown ptt_key"):
            PushToTalk(key_name="INVALID_KEY")

    def test_all_mapped_keys_are_valid(self):
        """Every key in KEY_MAP should initialise without error."""
        for key_name in KEY_MAP:
            ptt = PushToTalk(key_name=key_name)
            assert ptt.key_name == key_name

    def test_default_key(self):
        ptt = PushToTalk()
        assert ptt.key_name == "F9"

    def test_is_pressed_default_false(self):
        ptt = PushToTalk(key_name="F9")
        assert ptt.is_pressed() is False
