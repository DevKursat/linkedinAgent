"""Content moderation and filtering."""
from typing import Tuple
from .config import config


# Political keywords to block
POLITICS_KEYWORDS = [
    "election", "vote", "voting", "democrat", "republican", "liberal", "conservative",
    "trump", "biden", "congress", "senate", "parliament", "政治", "选举", "投票",
    "政党", "seçim", "oy", "parti", "siyaset", "政策", "法案", "议会",
]

# Speculative crypto keywords to block
CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency", "blockchain",
    "nft", "defi", "web3", "metaverse", "token", "coin", "mining", "wallet",
    "altcoin", "dogecoin", "shiba", "pump", "moon", "hodl", "加密货币", 
    "比特币", "以太坊", "kripto", "blokzincir",
]

# Sensitive topics that require approval
SENSITIVE_KEYWORDS = [
    "war", "conflict", "military", "weapon", "terrorism", "racist", "sexist",
    "religion", "religious", "islam", "christian", "jewish", "hindu", "buddhist",
    "savaş", "silah", "terör", "din", "dini", "战争", "武器", "宗教",
]


def is_blocked(text: str) -> Tuple[bool, str]:
    """Check if content should be blocked."""
    text_lower = text.lower()
    
    # Check politics
    if config.BLOCK_POLITICS:
        for keyword in POLITICS_KEYWORDS:
            if keyword in text_lower:
                return True, f"blocked: political content ({keyword})"
    
    # Check speculative crypto
    if config.BLOCK_SPECULATIVE_CRYPTO:
        for keyword in CRYPTO_KEYWORDS:
            if keyword in text_lower:
                return True, f"blocked: speculative crypto ({keyword})"
    
    return False, ""


def is_sensitive(text: str) -> Tuple[bool, str]:
    """Check if content is sensitive and requires approval."""
    if not config.REQUIRE_APPROVAL_SENSITIVE:
        return False, ""
    
    text_lower = text.lower()
    
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in text_lower:
            return True, f"sensitive: {keyword}"
    
    return False, ""


def should_post_content(text: str) -> Tuple[bool, str]:
    """Check if content should be posted automatically."""
    blocked, reason = is_blocked(text)
    if blocked:
        return False, reason
    
    sensitive, reason = is_sensitive(text)
    if sensitive:
        return False, reason
    
    return True, ""
