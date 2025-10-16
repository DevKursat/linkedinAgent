import sys
import os
import pytest

# Ensure project root is on sys.path for test discovery when running from CI or locally
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src import comment_handler as ch


def test_safe_generate_tags_basic():
    tags = ch._safe_generate_tags("This is a test about product management and startups.", title="Product launches")
    assert isinstance(tags, list)
    assert len(tags) <= 5


def test_safe_generate_summary_truncation():
    long_text = "word " * 1000
    s = ch._safe_generate_summary(long_text, max_chars=200)
    assert isinstance(s, str)
    assert len(s) <= 200
