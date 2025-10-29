import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pytz

def test_is_within_operating_hours():
    """Test that is_within_operating_hours correctly identifies operating hours."""
    from src.scheduler import is_within_operating_hours
    
    # Test time at 8 AM (should be within operating hours)
    with patch('src.scheduler.datetime') as mock_datetime:
        tz = pytz.timezone("Europe/Istanbul")
        mock_now = tz.localize(datetime(2025, 1, 15, 8, 0, 0))
        mock_datetime.now.return_value = mock_now
        assert is_within_operating_hours() == True, "8 AM should be within operating hours"
    
    # Test time at 6 AM (should be outside operating hours)
    with patch('src.scheduler.datetime') as mock_datetime:
        tz = pytz.timezone("Europe/Istanbul")
        mock_now = tz.localize(datetime(2025, 1, 15, 6, 0, 0))
        mock_datetime.now.return_value = mock_now
        assert is_within_operating_hours() == False, "6 AM should be outside operating hours"
    
    # Test time at 10 PM (22:00, should be outside operating hours)
    with patch('src.scheduler.datetime') as mock_datetime:
        tz = pytz.timezone("Europe/Istanbul")
        mock_now = tz.localize(datetime(2025, 1, 15, 22, 0, 0))
        mock_datetime.now.return_value = mock_now
        assert is_within_operating_hours() == False, "10 PM should be outside operating hours"
    
    # Test time at 9 PM (21:00, should be within operating hours)
    with patch('src.scheduler.datetime') as mock_datetime:
        tz = pytz.timezone("Europe/Istanbul")
        mock_now = tz.localize(datetime(2025, 1, 15, 21, 0, 0))
        mock_datetime.now.return_value = mock_now
        assert is_within_operating_hours() == True, "9 PM should be within operating hours"


def test_safe_triggers_skip_outside_hours():
    """Test that safe trigger functions skip execution outside operating hours."""
    from src.scheduler import safe_trigger_post_creation, safe_trigger_commenting, safe_trigger_invitation
    
    # Mock time outside operating hours (2 AM)
    with patch('src.scheduler.is_within_operating_hours', return_value=False):
        with patch('src.scheduler.trigger_post_creation') as mock_post:
            safe_trigger_post_creation()
            mock_post.assert_not_called()
        
        with patch('src.scheduler.trigger_commenting') as mock_comment:
            safe_trigger_commenting()
            mock_comment.assert_not_called()
        
        with patch('src.scheduler.trigger_invitation') as mock_invite:
            safe_trigger_invitation()
            mock_invite.assert_not_called()


def test_safe_triggers_execute_during_hours():
    """Test that safe trigger functions execute during operating hours."""
    from src.scheduler import safe_trigger_post_creation, safe_trigger_commenting, safe_trigger_invitation
    
    # Mock time during operating hours (10 AM)
    with patch('src.scheduler.is_within_operating_hours', return_value=True):
        with patch('src.scheduler.trigger_post_creation') as mock_post:
            safe_trigger_post_creation()
            mock_post.assert_called_once()
        
        with patch('src.scheduler.trigger_commenting') as mock_comment:
            safe_trigger_commenting()
            mock_comment.assert_called_once()
        
        with patch('src.scheduler.trigger_invitation') as mock_invite:
            safe_trigger_invitation()
            mock_invite.assert_called_once()
