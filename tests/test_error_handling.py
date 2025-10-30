"""Tests for improved error handling in worker and AI core."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


@patch("src.ai_core.model", None)  # Simulate model not initialized
def test_generate_text_no_model():
    """Test that generate_text returns None when model is not initialized."""
    from src.ai_core import generate_text
    
    result = generate_text("Test prompt")
    assert result is None


@patch("src.ai_core.model")
def test_generate_text_empty_response(mock_model):
    """Test that generate_text returns None when response is empty."""
    from src.ai_core import generate_text
    
    # Mock empty response
    mock_response = MagicMock()
    mock_response.text = "   "  # Empty or whitespace
    mock_model.generate_content.return_value = mock_response
    
    result = generate_text("Test prompt")
    assert result is None


@patch("src.ai_core.model")
def test_generate_text_exception(mock_model):
    """Test that generate_text returns None when exception occurs."""
    from src.ai_core import generate_text
    
    # Mock exception
    mock_model.generate_content.side_effect = Exception("API Error")
    
    result = generate_text("Test prompt")
    assert result is None


@pytest.mark.asyncio
@patch("src.worker.log_action")
@patch("src.worker.get_api_client")
@patch("src.worker.find_shareable_article")
@patch("src.worker.generate_text")
async def test_post_creation_ai_failure(mock_generate, mock_article, mock_client, mock_log):
    """Test that post creation handles AI failure gracefully."""
    from src.worker import trigger_post_creation_async
    
    # Setup mocks
    mock_article.return_value = MagicMock(title="Test Article", link="https://example.com")
    mock_generate.return_value = None  # AI failure
    mock_client.return_value = MagicMock()
    
    result = await trigger_post_creation_async()
    
    assert result["success"] is False
    assert "AI content generation is not available" in result["message"]
    assert "GEMINI_API_KEY" in result["message"]


@pytest.mark.asyncio
@patch("src.worker.log_action")
@patch("src.worker.find_profile_to_invite")
@patch("src.worker.get_api_client")
async def test_invitation_403_error(mock_get_client, mock_find_profile, mock_log):
    """Test that invitation handles 403 error with silent failure pattern.
    
    Verifies that 403 Forbidden errors (missing permissions) return skip_log=True
    and do not create action log entries, preventing repetitive error messages.
    """
    from src.worker import trigger_invitation_async
    import httpx
    
    # Mock finding a profile
    mock_find_profile.return_value = {
        "urn_id": "test_invitee_urn",
        "public_id": "test-person"
    }
    
    # Setup mock client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Mock profile
    mock_client.get_profile = AsyncMock(return_value={"id": "test_urn"})
    
    # Mock 403 error
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_error = httpx.HTTPStatusError(
        "403 Forbidden",
        request=MagicMock(),
        response=mock_response
    )
    mock_client.send_invitation = AsyncMock(side_effect=mock_error)
    
    result = await trigger_invitation_async()
    
    assert result["success"] is False
    assert "special permissions" in result["message"]
    assert "invitations" in result["message"]
    assert result.get("skip_log") is True  # Should have skip_log flag
    
    # Verify log_action was NOT called for 403 errors (silent failure)
    mock_log.assert_not_called()


@pytest.mark.asyncio
@patch("src.worker.log_action")
@patch("src.worker.get_api_client")
@patch("src.worker.PostDiscovery")
async def test_commenting_returns_success(mock_post_discovery, mock_get_client, mock_log):
    """Test that commenting handles no discovered posts gracefully."""
    from src.worker import trigger_commenting_async
    
    # Mock API client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Mock post discovery to return no posts
    mock_discovery_instance = MagicMock()
    mock_discovery_instance.discover_posts_smart = AsyncMock(return_value=[])
    mock_post_discovery.return_value = mock_discovery_instance
    
    result = await trigger_commenting_async()
    
    # Should return failure with proper message when no posts found
    assert result["success"] is False
    assert "discover" in result["message"].lower() or "relevant" in result["message"].lower()
    assert "actions" in result
    
    # Verify log_action was called for skipping
    assert mock_log.called
