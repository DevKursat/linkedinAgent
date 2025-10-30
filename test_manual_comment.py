"""Test for manual comment functionality."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_manual_comment_missing_url(client):
    """Test that manual comment fails without a URL."""
    response = client.post("/api/manual_comment", json={})
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is False
    assert "required" in result["message"].lower()


def test_manual_comment_invalid_url(client):
    """Test that manual comment fails with invalid URL."""
    response = client.post("/api/manual_comment", json={
        "post_url": "https://www.example.com/not-a-linkedin-post"
    })
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is False
    assert "URN" in result["message"] or "URL" in result["message"]


@patch('src.main.LinkedInApiClient')
@patch('src.main.generate_text')
@patch('src.main.log_action')
def test_manual_comment_success(mock_log, mock_generate, mock_client_class, client):
    """Test successful manual comment."""
    # Setup mocks
    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client
    mock_client.get_profile.return_value = {"id": "test_user_urn"}
    mock_client.submit_comment.return_value = {"id": "comment123"}
    mock_generate.return_value = "Great post! Very insightful."
    
    response = client.post("/api/manual_comment", json={
        "post_url": "https://www.linkedin.com/feed/update/urn:li:activity:1234567890/"
    })
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "success" in result["message"].lower()
    assert mock_client.submit_comment.called


@patch('src.main.LinkedInApiClient')
@patch('src.main.log_action')
def test_manual_comment_with_custom_text(mock_log, mock_client_class, client):
    """Test manual comment with custom comment text."""
    # Setup mocks
    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client
    mock_client.get_profile.return_value = {"id": "test_user_urn"}
    mock_client.submit_comment.return_value = {"id": "comment123"}
    
    custom_text = "This is my custom comment"
    response = client.post("/api/manual_comment", json={
        "post_url": "https://www.linkedin.com/posts/username_activity-1234567890-abcd",
        "comment": custom_text
    })
    
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    
    # Verify custom text was used
    call_args = mock_client.submit_comment.call_args
    assert call_args[0][2] == custom_text  # Third argument should be the comment text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
