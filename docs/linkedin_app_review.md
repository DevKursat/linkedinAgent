LinkedIn App Review Package

Purpose
-------
This document contains the suggested text, scopes, API usage, and demo steps to request elevated LinkedIn API permissions required by the linkedinAgent project. The agent posts on behalf of the user, reads comments on user's shares, and sends connection invites to selected people.

Required scopes and why
-----------------------
- w_member_social
  - Purpose: Create posts and comments on behalf of the authenticated user (required for posting daily shares, follow-ups, proactive commenting).
- r_liteprofile or openid profile (OIDC)
  - Purpose: Resolve the authenticated user's id and basic profile for building author URNs and for personalization.
- r_organization_social (if posting to organization pages)
  - Purpose: If user wants to post as an organization.
- (Optional) growth/invitations or equivalent elite permission
  - Purpose: Send connection invitations on behalf of the user.
  - Note: This scope is typically gated in LinkedIn and requires detailed review and justification.
- (Optional) comments.read or posts.read if available under REST API
  - Purpose: To list comments on the user's posts when LinkedIn allows.

Usage justification (copy for the LinkedIn App Review form)
------------------------------------------------------------
What does the app do?
The linkedinAgent is a personal productivity agent that helps a user manage their LinkedIn presence. With explicit user consent (OAuth login), the agent will:
- Create short, high-quality LinkedIn posts on behalf of the user at scheduled times.
- Generate and post value-adding follow-up comments and summaries for the user's posts.
- Read comments on the user's posts to identify mentions and important interactions.
- Optionally send personalized connection invitations to non-connections identified via discovery and user-configured heuristics.

Why we need elevated permissions
We only act on behalf of an authenticated account after explicit OAuth consent. Elevated permissions are required to:
- Create content (w_member_social) so the user can automate posting and engagement.
- Read comments and interactions on the user's content to enable automated replies and invitations.
- Send invitations on behalf of the user when the user has requested the agent to do so.

Data retention and privacy
--------------------------
- We only store minimal metadata required to operate: LinkedIn access token (encrypted by the host environment), post IDs/URNs, queued invite targets, and transient generation results.
- We do not scrape or store full external user profiles beyond the URN and optional display name used for personalization.
- Invitations are only sent when the user has explicitly enabled invites in their settings and after review.
- Users may revoke OAuth access at any time; bot will stop operating for that account immediately when token becomes invalid.

Demo steps for reviewer
-----------------------
1. Sign in with the test account using OAuth flow and grant the requested scopes.
2. Using the test account, create a scheduled post via the demo UI or call the API to create a post.
3. Confirm post is visible and the app can read the post's comments (simulate a comment and verify the agent can list it).
4. (Invitation step) With explicit consent, enable invites and instruct the app to send a single test invite to a test URN provided by the reviewer.

Example API calls (for review team)
----------------------------------
- GET /v2/me or /v2/userinfo to confirm token and retrieve profile.
- POST /rest/growth/invitations or POST /v2/invitations to create an invitation given a person URN.
- GET /rest/posts/{post_id}/comments to list comments on a post (or equivalent socialActions endpoints).

Security & Contact
------------------
- The requesting application is a personal productivity agent; the developer will provide any additional screencasts or live demo access requested by the review team.
- Contact: <your-email@example.com>

Notes and caveats
-----------------
- LinkedIn's invitations and some comment-listing APIs are gated and may require partnership-level access. If the team requests changes to the usage patterns, we will adapt the flow (e.g., switch to manual send-with-confirm flow) to comply.

Appendix: reproducible demo commands
------------------------------------
- Run the discovery and invite pipeline locally (dry-run) to show queuing behavior without sending invites:

  python3 manage.py set-dry-run true
  python3 manage.py enqueue-invites-csv sample_invites.csv
  python3 manage.py list-invites

- To demonstrate the live send (review-only):
  1) Ensure a test account and a test person URN are provided.
  2) Run:

  python3 manage.py enable-invites


