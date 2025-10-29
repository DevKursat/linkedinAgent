import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


def test_post_creation_timing():
    """Test that post creation uses correct timing: 45s for like, 90s total for comment."""
    from src.worker import trigger_post_creation_async
    
    # Create mocks
    mock_article = MagicMock()
    mock_article.title = "Test Article"
    mock_article.link = "https://test.com/article"
    
    with patch('src.worker.get_api_client') as mock_get_client, \
         patch('src.worker.find_shareable_article', return_value=mock_article), \
         patch('src.worker.generate_text') as mock_generate, \
         patch('src.worker.log_action'), \
         patch('asyncio.sleep') as mock_sleep:
        
        # Setup mock API client
        mock_client = MagicMock()
        mock_client.get_profile = AsyncMock(return_value={"id": "test_user_urn"})
        mock_client.share_post = AsyncMock(return_value={"id": "test_post_urn"})
        mock_client.add_reaction = AsyncMock()
        mock_client.submit_comment = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Setup mock text generation
        mock_generate.side_effect = ["Test post content", "Test Turkish summary"]
        
        # Run the async function
        asyncio.run(trigger_post_creation_async())
        
        # Verify the sleep calls with correct timing
        sleep_calls = mock_sleep.call_args_list
        assert len(sleep_calls) == 2, "Should have two sleep calls"
        
        # First sleep should be 45 seconds (before liking)
        assert sleep_calls[0][0][0] == 45, "First sleep should be 45 seconds"
        
        # Second sleep should be 45 seconds (before commenting, totaling 90s)
        assert sleep_calls[1][0][0] == 45, "Second sleep should be 45 seconds (totaling 90s)"
        
        # Verify that like and comment were called
        mock_client.add_reaction.assert_called_once()
        mock_client.submit_comment.assert_called_once()


def test_worker_imports():
    """Test that worker module imports correctly."""
    from src import worker
    assert hasattr(worker, 'trigger_post_creation')
    assert hasattr(worker, 'trigger_commenting')
    assert hasattr(worker, 'trigger_invitation')
