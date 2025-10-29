import pytest
from unittest.mock import patch, MagicMock
from src.linkedin_api_client import LinkedInApiClient

@pytest.fixture
def mock_token_file(tmp_path):
    """Creates a dummy token file for testing."""
    token_file = tmp_path / "linkedin_token.json"
    token_file.write_text("dummy_access_token")
    return str(token_file)

@patch("httpx.AsyncClient")
def test_get_profile_success(mock_async_client, mock_token_file):
    """Tests successful profile retrieval."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "test_user_urn"}

    mock_async_client.return_value.__aenter__.return_value.get.return_value = mock_response

    client = LinkedInApiClient(token_file=mock_token_file)

    import asyncio
    profile = asyncio.run(client.get_profile())

    assert profile["id"] == "test_user_urn"

@patch("httpx.AsyncClient")
def test_share_post_success(mock_async_client, mock_token_file):
    """Tests successful post sharing."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "new_post_urn"}

    mock_async_client.return_value.__aenter__.return_value.post.return_value = mock_response

    client = LinkedInApiClient(token_file=mock_token_file)

    import asyncio
    result = asyncio.run(client.share_post("test_user_urn", "Hello, world!"))

    assert result["id"] == "new_post_urn"
