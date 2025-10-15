LinkedIn App Review — Submission package (ready-to-paste)

Overview
--------
Use this file as the final copy to paste into the LinkedIn Developer Console when requesting elevated permissions. Replace bracketed values (e.g., [YOUR_EMAIL]) and attach the assets listed at the end.

Developer contact
-----------------
Support email: [your-email@example.com]
Company / Developer: [Your Name or Company]
App name: linkedinAgent
App ID: [paste your app id from the LinkedIn Developer Console]
Redirect URI: [your redirect URI, e.g. https://your-host.example.com/callback]
Privacy policy URL: [public URL to privacy policy]

Short description (one sentence)
--------------------------------
An OAuth-enabled personal productivity agent that helps an authenticated LinkedIn user schedule posts, auto-reply to comments, and (optionally) send personalized connection invitations on behalf of the user.

Detailed description / Use case (paste into "long description")
----------------------------------------------------------------
linkedinAgent is a personal productivity assistant that acts only after explicit OAuth consent from a LinkedIn account owner. Its core features:
- Create scheduled public posts and follow-up comments on behalf of the authenticated user (requires w_member_social).
- Read comments on the user's posts to identify mentions and generate context-aware replies to promote timely engagement.
- Optionally send personalized connection invitations to non-connections when the authenticated user has enabled that feature.

We only perform actions when a user explicitly connects their LinkedIn account via OAuth and grants the requested scopes. The application stores minimal metadata (post URNs, queued invite URNs, timestamps) and does not publish or retain sensitive third-party profile data beyond a profile URN and optional display name used for personalization.

Why the requested permissions are necessary
------------------------------------------
- w_member_social: Required to create posts, comments and follow-ups on behalf of the authenticated user to automate scheduled posting and engagement.
- r_liteprofile / openid profile: Required to resolve the authenticated user's ID and construct author URNs for API calls.
- (Optional) Invitations/Growth API: Required to create a connection invitation on behalf of the authenticated user when they explicitly enable invite automation.
- (Optional) Comments/Posts read: Listing comments on the user's own posts (and reading responses) enables the automated reply and mention-detection features.

Data handling and retention
--------------------------
- Access token: stored locally by the user-hosted instance (not shared). Instruct reviewers to use the provided test account and ephemeral token for the demo.
- Stored metadata: post IDs/URNs, queue items and minimal invite records (person URN, display name) are kept to coordinate retries and audit actions.
- No bulk scraping: We do not harvest or store full external user profiles. Only URNs and optional short display names are kept.
- Revocation: Users can revoke OAuth tokens at any time; the app will stop performing actions for that account.

Demo instructions for reviewer (copy into form or attach as separate document)
------------------------------------------------------------------------------
Please follow these steps to reproduce the behavior with a test account:
1) Create a test LinkedIn account or use the test account credentials we provide in the attachments.
2) In the app's OAuth consent, grant these scopes: w_member_social, openid profile email.
3) From the developer app dashboard, ensure redirect URI matches the supplied redirect URI.
4) Using the app's demo UI or CLI, run a scheduled post and confirm the app creates a post in the authenticated account's feed.
5) Simulate a comment on that post and confirm the app can list comments and generate a reply (the app has a simulate endpoint for reviewer at /simulate_incoming_comment).
6) (Invites only) If the reviewer provides a test recipient URN, enable invites for the test account and request the app to send a single invitation; we will demonstrate one controlled invite.

Assets to attach (recommended)
------------------------------
- Short screencast (1–2 minutes) showing:
  - OAuth consent flow granting the scopes
  - Creating a scheduled post via the app UI
  - A simulated incoming comment and the agent posting a reply
  - (Optional) Enabling invites and sending a single test invite
- Screenshots:
  - App dashboard showing granted scopes
  - Example post created by the app
  - Example alert log entry on failed invite (demonstrates error handling)
- Test account credentials (if you want the reviewers to exercise live flows)
- Privacy policy URL

Exact text copy for common LinkedIn Developer Console fields
-----------------------------------------------------------
- Business name / Developer: [Your Name or Company]
- App short description: Personal LinkedIn assistant for scheduled posting and engagement
- App long description: (Use the "Detailed description" section above)
- Intended use: "The app will be used by an authenticated LinkedIn user to automate posting, reply to comments, and optionally send connection invitations after explicit user enablement."
- Data usage: "We store minimal metadata (post IDs, queued invite URNs) to coordinate retries and auditing. We do not sell or share user data. Tokens are stored locally by the self-hosted instance and may be revoked at any time."

Where to submit
----------------
1) Developer Console (preferred):
   - URL: https://www.linkedin.com/developers/
   - Sign in -> "My Apps" -> Select your app -> "Products" tab -> Add the required products/scopes (w_member_social, Sign In with LinkedIn, etc.) -> Click "Request Access" for gated products (invitations/growth APIs).
2) If a manual support request is required (for partnership APIs): open a support ticket via LinkedIn Help or contact LinkedIn Developer Support through the console's support/Help links. Provide the submission package and screencast.

Expected review timeline
------------------------
- Typical: 2–6 business days for standard product access (w_member_social, Sign In with LinkedIn).
- Gated/partner APIs (invitations/growth): may take longer — typically 1–3 weeks, sometimes longer depending on LinkedIn's review needs.
- Note: reviewers commonly request additional information or a short screencast; responding promptly shortens the overall time.

After approval: next steps
-------------------------
1) Toggle INVITES_ENABLED=true and DRY_RUN=false using the `manage.py enable-invites` command (or edit .env), then run a small smoke test: `python3 manage.py send-invite <id> --force` for a single invite.
2) Monitor `data/alerts.log` for any errors; the app will also enqueue failed actions for retries.

Support & contact
-----------------
If reviewers ask technical questions, provide the following contact and technical lead info:
- Technical lead: [Your Name]
- Contact email: [your-email@example.com]
- Project repo: https://github.com/DevKursat/linkedinAgent


