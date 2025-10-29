import pytest
from unittest.mock import patch, MagicMock
from src.linkedin_api_client import LinkedInApiClient

# No longer need to mock the token file, we will pass the token directly.

@patch("src.linkedin_api_client.SessionLocal")  # Mock the database session
@patch("httpx.AsyncClient")
def test_get_profile_success(mock_async_client, mock_db_session):
    """Tests successful profile retrieval with a direct token."""
    # Mock the database call to return a token
    mock_token = MagicMock()
    mock_token.access_token = "dummy_access_token_from_db"
    mock_db_session.return_value.query.return_value.order_by.return_value.first.return_value = mock_token

    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "test_user_urn"}
    mock_async_client.return_value.__aenter__.return_value.get.return_value = mock_response

    # Initialize the client with a direct access token
    client = LinkedInApiClient(access_token="dummy_access_token")

    import asyncio
    profile = asyncio.run(client.get_profile())

    assert profile["id"] == "test_user_urn"
    # Ensure the Authorization header is correctly set
    mock_async_client.return_value.__aenter__.return_value.get.assert_called_with(
        f"{client.API_BASE_URL}/me", headers={'Authorization': 'Bearer dummy_access_token', 'Content-Type': 'application/json', 'X-Restli-Protocol-Version': '2.0.0'}
    )


@patch("src.linkedin_api_client.SessionLocal") # Mock the database session
@patch("httpx.AsyncClient")
def test_share_post_success(mock_async_client, mock_db_session):
    """Tests successful post sharing with a direct token."""
    # Mock the database call
    mock_token = MagicMock()
    mock_token.access_token = "dummy_access_token_from_db"
    mock_db_session.return_value.query.return_value.order_by.return_value.first.return_value = mock_token

    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "new_post_urn"}
    mock_async_client.return_value.__aenter__.return_value.post.return_value = mock_response

    # Initialize the client with a direct access token
    client = LinkedInApiClient(access_token="dummy_access_token")

    import asyncio
    result = asyncio.run(client.share_post("test_user_urn", "Hello, world!"))

    assert result["id"] == "new_post_urn"
