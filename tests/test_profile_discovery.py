import pytest

from src.post_discovery import ProfileDiscovery


@pytest.mark.asyncio
async def test_discovery_uses_auto_invite_targets(monkeypatch):
    monkeypatch.setenv(
        "AUTO_INVITE_TARGETS",
        "urn:li:person:123|ahmet-yilmaz,urn:li:person:456|ayse-kaya"
    )

    discovery = ProfileDiscovery(["ai", "product"])
    profile = await discovery._discover_from_tech_communities()

    assert profile is not None
    assert profile["urn_id"].startswith("urn:li:person:")
    assert profile["public_id"] in {"ahmet-yilmaz", "ayse-kaya"}


@pytest.mark.asyncio
async def test_discovery_ignores_invalid_auto_invite_targets(monkeypatch):
    monkeypatch.setenv("AUTO_INVITE_TARGETS", "invalid-token,urn:li:person:999|")

    discovery = ProfileDiscovery(["ai", "product"])
    profile = await discovery._discover_from_tech_communities()

    assert profile is None
