import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import importlib
import json

# We need to import the module itself to reload it and reset its state
import src.linkedin_client

# We import the functions we want to test
from src.linkedin_client import get_linkedin_api, COOKIE_PATH

class TestLinkedInClient(unittest.TestCase):

    def setUp(self):
        """Set up for tests."""
        if os.path.exists(COOKIE_PATH):
            os.remove(COOKIE_PATH)
        src.linkedin_client._linkedin_api_client = None

    def tearDown(self):
        """Tear down after tests."""
        if os.path.exists(COOKIE_PATH):
            os.remove(COOKIE_PATH)
        src.linkedin_client._linkedin_api_client = None

    @patch('src.linkedin_client._load_credentials', return_value=('test@example.com', 'password'))
    @patch('src.linkedin_client.Linkedin')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_login_with_credentials_saves_cookies(self, mock_json_dump, mock_open, mock_linkedin, mock_load_credentials):
        """
        Test that when no cookie file exists, the app uses credentials
        provided by the mocked _load_credentials function.
        """
        # Arrange
        mock_api = MagicMock()
        mock_api.client.cookies.get_dict.return_value = {"JSESSIONID": "some_dummy_cookie"}
        mock_linkedin.return_value = mock_api

        # Act
        api = get_linkedin_api()

        # Assert
        self.assertIsNotNone(api)
        mock_load_credentials.assert_called_once()
        mock_linkedin.assert_called_once_with(
            'test@example.com',
            'password',
            refresh_cookies=True
        )
        mock_open.assert_called_once_with(COOKIE_PATH, "w")
        mock_json_dump.assert_called_once_with({"JSESSIONID": "some_dummy_cookie"}, mock_open())

    @patch('src.linkedin_client.os.path.exists', return_value=True)
    @patch('src.linkedin_client.Linkedin')
    def test_login_with_existing_cookies(self, mock_linkedin, mock_exists):
        """
        Test that when a cookie file exists, it's used for authentication.
        """
        # Arrange
        mock_api = MagicMock()
        mock_linkedin.return_value = mock_api

        # Act
        api = get_linkedin_api()

        # Assert
        self.assertIsNotNone(api)
        mock_linkedin.assert_called_once_with(
            "",
            "",
            cookies=COOKIE_PATH
        )

if __name__ == '__main__':
    unittest.main()
