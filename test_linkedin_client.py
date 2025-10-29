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

    def test_login_with_credentials_saves_cookies(self):
        """
        Test that when logging in with email/password, cookies are manually saved.
        """
        # Arrange: Use patch.dict to temporarily set environment variables
        with patch.dict(os.environ, {'LINKEDIN_EMAIL': 'test@example.com', 'LINKEDIN_PASSWORD': 'password'}):
            # Reload the module to make it pick up the new environment variables
            importlib.reload(src.linkedin_client)
            # We must import the function AFTER the reload
            from src.linkedin_client import get_linkedin_api

            # Act: Use patch as a context manager AFTER the reload
            with patch('src.linkedin_client.Linkedin') as mock_linkedin, \
                 patch('builtins.open', new_callable=mock_open) as mock_file_open, \
                 patch('json.dump') as mock_json_dump:

                # Configure the mock Linkedin API object
                mock_api = MagicMock()
                mock_api.client.cookies.get_dict.return_value = {"JSESSIONID": "some_dummy_cookie"}
                mock_linkedin.return_value = mock_api

                # Call the function under test
                api = get_linkedin_api()

                # Assert
                self.assertIsNotNone(api)
                # 1. Verify Linkedin was called for authentication without the cookie path
                mock_linkedin.assert_called_once_with(
                    'test@example.com',
                    'password',
                    refresh_cookies=True
                )
                # 2. Verify the cookie file was opened for writing
                mock_file_open.assert_called_once_with(COOKIE_PATH, "w")
                # 3. Verify that the cookies were dumped to the file
                mock_json_dump.assert_called_once_with({"JSESSIONID": "some_dummy_cookie"}, mock_file_open())

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

            # No reload needed here, but we still import locally for consistency
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
