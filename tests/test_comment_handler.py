import pytest

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
