# tests/conftest.py
"""
Shared pytest configuration.

Adds the project root to sys.path so all imports work correctly
regardless of where pytest is run from.
"""

import sys
import os

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
