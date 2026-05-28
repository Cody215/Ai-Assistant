"""
Tests for llm/ollama_client.py — Ollama API integration with fallback.

Validates that the Ollama client can call tools, handle text responses,
and gracefully fall back to Gemini on connection failure.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, Mock
import pytest

from llm.ollama_client import _build_ollama_tools, call_with_tool


class MockFunctionDeclaration:
    """Mock a Gemini FunctionDeclaration for testing."""

    def __init__(self, name: str, description: str = "", params=None):
        self.name = name
        self.description = description
        self.parameters = params


class MockParameterSchema:
    """Mock parameter schema."""

    def __init__(self, properties=None, required=None):
        self.properties = properties or {}
        self.required = required or []


class TestBuildOllamaTools:
    """Test conversion of Gemini tools to Ollama format."""

    def test_build_empty_declarations(self):
        """Should handle empty declarations list."""
        result = _build_ollama_tools([])
        assert result == []

    def test_build_simple_tool(self):
        """Should convert simple tool declaration."""
        decl = MockFunctionDeclaration("get_time", "Get current time")
        decl.parameters = None
        
        result = _build_ollama_tools([decl])
        
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "get_time"
        assert result[0]["function"]["description"] == "Get current time"

    def test_build_tool_with_parameters(self):
        """Should convert tool with parameters."""
        props = {
            "query": MockFunctionDeclaration("query"),
            "max_results": MockFunctionDeclaration("max_results"),
        }
        props["query"].description = "Search query"
        props["max_results"].description = "Max results"
        
        params = MockParameterSchema(properties=props, required=["query"])
        decl = MockFunctionDeclaration("web_search", "Search the web", params)
        
        result = _build_ollama_tools([decl])
        
        assert len(result) == 1
        assert "parameters" in result[0]["function"]
        assert "query" in result[0]["function"]["parameters"]["properties"]
        assert "query" in result[0]["function"]["parameters"]["required"]

    def test_build_multiple_tools(self):
        """Should convert multiple tool declarations."""
        decls = [
            MockFunctionDeclaration("get_time", "Get time"),
            MockFunctionDeclaration("get_date", "Get date"),
            MockFunctionDeclaration("get_battery", "Get battery"),
        ]
        for decl in decls:
            decl.parameters = None
        
        result = _build_ollama_tools(decls)
        
        assert len(result) == 3
        assert result[0]["function"]["name"] == "get_time"
        assert result[1]["function"]["name"] == "get_date"
        assert result[2]["function"]["name"] == "get_battery"


class TestCallWithToolSuccess:
    """Test successful Ollama API calls."""

    @patch("ollama.chat")
    def test_call_returns_text_response(self, mock_chat):
        """Should handle plain text response from Ollama."""
        mock_chat.return_value = {
            "message": {
                "content": "The current time is 3:45 PM.",
                "tool_calls": None,
            }
        }
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert tool_name is None
        assert text == "The current time is 3:45 PM."
        assert args is None

    @patch("ollama.chat")
    def test_call_returns_tool_call(self, mock_chat):
        """Should parse tool call from Ollama response."""
        mock_chat.return_value = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_time",
                            "arguments": {"timezone": "UTC"},
                        }
                    }
                ],
            }
        }
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert tool_name == "get_time"
        assert text is None
        assert args == {"timezone": "UTC"}

    @patch("ollama.chat")
    def test_call_parses_json_arguments(self, mock_chat):
        """Should parse JSON string arguments."""
        mock_chat.return_value = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "web_search",
                            "arguments": '{"query": "AI news", "limit": 5}',
                        }
                    }
                ],
            }
        }
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="Search for AI news",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert tool_name == "web_search"
        assert args == {"query": "AI news", "limit": 5}

    @patch("ollama.chat")
    def test_call_handles_malformed_json_arguments(self, mock_chat):
        """Should handle malformed JSON gracefully."""
        mock_chat.return_value = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "web_search",
                            "arguments": "{invalid json}",
                        }
                    }
                ],
            }
        }
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="Search for AI news",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert tool_name == "web_search"
        assert args == {}  # Falls back to empty dict


class TestCallWithToolFallback:
    """Test fallback behavior on errors."""

    @patch("ollama.chat")
    def test_fallback_on_connection_refused(self, mock_chat):
        """Should fall back on connection refused."""
        mock_chat.side_effect = ConnectionRefusedError("Ollama not running")
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert tool_name is None
        assert text is None
        assert args is None

    @patch("ollama.chat")
    def test_fallback_on_connection_error(self, mock_chat):
        """Should fall back on general connection error."""
        mock_chat.side_effect = OSError("Connection refused")
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert tool_name is None
        assert text is None
        assert args is None

    @patch("ollama.chat")
    def test_fallback_on_timeout(self, mock_chat):
        """Should fall back on timeout."""
        mock_chat.side_effect = TimeoutError("Request timed out")
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert tool_name is None
        assert text is None
        assert args is None

    @patch("ollama.chat")
    def test_fallback_on_generic_exception(self, mock_chat):
        """Should fall back on any exception."""
        mock_chat.side_effect = Exception("Something went wrong")
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert tool_name is None
        assert text is None
        assert args is None


class TestCallWithToolEdgeCases:
    """Test edge cases."""

    @patch("ollama.chat")
    def test_empty_response_content(self, mock_chat):
        """Should handle empty response content."""
        mock_chat.return_value = {
            "message": {
                "content": "",
                "tool_calls": None,
            }
        }
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert tool_name is None
        assert text == ""
        assert args is None

    @patch("ollama.chat")
    def test_whitespace_response_stripped(self, mock_chat):
        """Should strip whitespace from response."""
        mock_chat.return_value = {
            "message": {
                "content": "   The time is 3:45 PM.   \n",
                "tool_calls": None,
            }
        }
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert text == "The time is 3:45 PM."

    @patch("ollama.chat")
    def test_message_dict_missing_content(self, mock_chat):
        """Should handle missing content key."""
        mock_chat.return_value = {
            "message": {
                "tool_calls": None,
            }
        }
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert text == ""

    @patch("ollama.chat")
    def test_response_missing_message(self, mock_chat):
        """Should handle missing message key in response."""
        mock_chat.return_value = {}
        
        tool_name, text, args = call_with_tool(
            model="phi3:mini",
            user_text="What time is it?",
            system_prompt="You are helpful.",
            declarations=[],
        )
        
        assert text == ""
