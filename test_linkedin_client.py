import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import importlib
import json

# We need to import the module itself to reload it and reset its state
import src.linkedin_client
# Import the credentials to verify against them
from src import credentials

# We import the functions we want to test
from src.linkedin_client import get_linkedin_api, COOKIE_PATH

class TestLinkedInClient(unittest.TestCase):

    def setUp(self):
        """Set up for tests."""
        # Ensure no cookie file exists from previous runs
        if os.path.exists(COOKIE_PATH):
            os.remove(COOKIE_PATH)
        # Reset the cached client instance before each test
        src.linkedin_client._linkedin_api_client = None
        # Reload the module to reset its global state
        importlib.reload(src.linkedin_client)


    def tearDown(self):
        """Tear down after tests."""
        if os.path.exists(COOKIE_PATH):
            os.remove(COOKIE_PATH)
        # Clean up the cached client
        src.linkedin_client._linkedin_api_client = None

    @patch('src.linkedin_client.Linkedin')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_login_with_credentials_saves_cookies(self, mock_json_dump, mock_open, mock_linkedin):
        """
        Test that when no cookie file exists, the app uses the credentials
        from credentials.py and saves the new cookies.
        """
        # Arrange
        mock_api = MagicMock()
        mock_api.client.cookies.get_dict.return_value = {"JSESSIONID": "some_dummy_cookie"}
        mock_linkedin.return_value = mock_api
        from src.linkedin_client import get_linkedin_api

        # Act
        api = get_linkedin_api()

        # Assert
        self.assertIsNotNone(api)
        # 1. Verify Linkedin was called with the correct credentials from the file
        mock_linkedin.assert_called_once_with(
            credentials.LINKEDIN_EMAIL,
            credentials.LINKEDIN_PASSWORD,
            refresh_cookies=True
        )
        # 2. Verify the cookie file was opened for writing
        mock_open.assert_called_once_with(COOKIE_PATH, "w")
        # 3. Verify that the cookies were dumped to the file
        mock_json_dump.assert_called_once_with({"JSESSIONID": "some_dummy_cookie"}, mock_open())

    def test_login_with_existing_cookies(self):
        """
        Test that when a cookie file exists, it's used for authentication.
        """
        # Arrange: Create a dummy cookie file
        with open(COOKIE_PATH, 'w') as f:
            f.write('{"cookie": "dummy"}')

        # Act: Use patch as a context manager
        with patch('src.linkedin_client.Linkedin') as mock_linkedin:
            mock_api = MagicMock()
            mock_linkedin.return_value = mock_api

            from src.linkedin_client import get_linkedin_api
            api = get_linkedin_api()

            # Assert
            self.assertIsNotNone(api)
            # Verify that the Linkedin constructor was called with the cookie file path
            mock_linkedin.assert_called_once_with(
                "",
                "",
                cookies=COOKIE_PATH
            )

if __name__ == '__main__':
    unittest.main()
