"""LinkedIn API client using the official API."""
import os
from linkedin_api import Linkedin as OfficialLinkedin
from .config import config

_api_client = None


def get_linkedin_api():
    """Get the authenticated LinkedIn API client."""
    global _api_client
    if _api_client:
        return _api_client

    if not config.LINKEDIN_USERNAME or not config.LINKEDIN_PASSWORD:
        raise ValueError("LinkedIn username or password not set in config.")

    # The official API library uses cookies for session management.
    # It's recommended to handle cookie persistence for stability.
    cookie_path = os.path.join(os.path.dirname(__file__), '..', 'linkedin_cookies.json')

    try:
        api = OfficialLinkedin(
            username=config.LINKEDIN_USERNAME,
            password=config.LINKEDIN_PASSWORD,
            cookie_filepath=cookie_path,
            refresh_cookies=True  # Refresh cookies on each instantiation
        )
        _api_client = api
        return api
    except Exception as e:
        # This could be due to invalid credentials, network issues, or a captcha.
        print(f"Error initializing LinkedIn API: {e}")
        # Consider adding a notification mechanism here for login failures.
        raise


class LinkedinAPI:
    """A wrapper class for the Linkedin library to provide a consistent interface."""
    def __init__(self, username, password):
        self.client = OfficialLinkedin(username, password, refresh_cookies=True)

    def me(self):
        """Get the authenticated user's profile."""
        return self.client.get_profile()

    def post_ugc(self, text, tags=None):
        """Create a new User Generated Content post (a.k.a. a share)."""
        if not text:
            raise ValueError("Post text cannot be empty.")

        # The library expects visibility and content details.
        # Let's default to public visibility.
        post_data = {
            "author": f"urn:li:person:{self.me()['profile_id']}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text,
                        "attributes": [] # Can be used for mentions
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

        if tags:
            # The official API doesn't have a direct field for hashtags in the same way
            # some unofficial APIs do. Hashtags are typically included in the text.
            hashtags = ' '.join([f"#{tag.strip()}" for tag in tags])
            text_with_tags = f"{text}\n\n{hashtags}"
            post_data['specificContent']['com.linkedin.ugc.ShareContent']['shareCommentary']['text'] = text_with_tags

        # This is a conceptual representation. The actual method call might differ.
        # The underlying library might handle the URN creation internally.
        # Let's use a method that reflects creating a share.
        # Note: The `linkedin_api` library's method is `create_share`.
        response = self.client.create_share(commentary=text, visibility='PUBLIC')
        
        # The response structure needs to be adapted to what the scheduler expects.
        # The library returns a dictionary with 'id', which can be used to construct the URN.
        if response and 'id' in response:
            return {'urn': f"urn:li:share:{response['id']}", 'id': response['id']}
        return response

    def like_post(self, post_urn):
        """Like a post."""
        # The URN needs to be passed to the underlying library method.
        # The method might be named `react_to_post` or similar.
        self.client.react_to_activity(post_urn, "LIKE")

    def comment_on_post(self, post_urn, comment_text, parent_comment_id=None):
        """Comment on a post. Can also be a reply to another comment."""
        if parent_comment_id:
            # This is a reply to a comment.
            # The library might have a `reply_to_comment` method.
            # If not, the `create_comment` method might take a parent_urn argument.
            # Assuming the library handles this distinction.
            response = self.client.create_comment(post_urn, comment_text, parent_urn=f"urn:li:comment:{parent_comment_id}")
        else:
            # This is a top-level comment.
            response = self.client.create_comment(post_urn, comment_text)
        
        return response

    def list_comments(self, post_urn):
        """List comments on a post."""
        comments = self.client.get_activity_comments(post_urn)
        # Adapt the structure to what the scheduler expects
        formatted_comments = []
        for c in comments:
            # The structure from the library needs to be mapped to the app's internal format.
            # This is a conceptual mapping.
            formatted_comments.append({
                'id': c.get('entityUrn', '').split(':')[-1],
                'actor': c.get('author', {}).get('urn', ''),
                'message': {'text': c.get('commentary', {}).get('text', '')}
            })
        return formatted_comments

    def send_invite(self, person_urn, message):
        """Send a connection invitation."""
        # The person_urn might need to be converted to a profile_id for the library method.
        profile_id = person_urn.split(':')[-1]
        self.client.add_connection(profile_id, message=message)

    def get_profile_connections(self, profile_urn, limit=100):
        """Get connections of a given profile."""
        profile_id = profile_urn.split(':')[-1]
        return self.client.get_profile_connections(profile_id, limit=limit)

    def search_people(self, keywords, limit=10):
        """Search for people."""
        return self.client.search_people(keywords=keywords, limit=limit)


# You can then instantiate and use this class where needed,
# or adapt the `get_linkedin_api` function to return an instance of this wrapper.
# For simplicity, we continue with the direct `get_linkedin_api` function approach.
