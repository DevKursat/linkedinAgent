Screencast & Screenshot instructions for LinkedIn App Review

Length: 60–120 seconds recommended. Keep it focused and captioned.

Screencast outline:
1. Show the LinkedIn Developer Console app page (App ID visible) and the requested scopes added to the product list.
2. Demonstrate OAuth flow: click "Sign in with LinkedIn", select the test account and show the consent screen (scopes requested visible), click Accept.
3. Show the app dashboard where you can trigger a scheduled post; create or trigger a short post and show it appearing on the LinkedIn profile feed.
4. Show posting of a follow-up comment (the app schedules after posting and posts follow-up) — or run the simulate endpoint to show reply generation.
5. (Optional) Show enabling invites in app settings and demonstrate sending one test invite to a reviewer-supplied URN.

Screenshots to include:
- Developer Console: App ID and Product/Scope list
- OAuth consent screen showing scopes
- Example post created by the app (in feed)
- Example alert entry in `data/alerts.log` (showing robust error handling)

File formats & naming:
- Screencast: MP4 (H.264), under 50MB if possible — name: linkedinAgent_demo.mp4
- Screenshots: PNG, name as screenshot-1.png, screenshot-2.png, etc.

How to attach in the LinkedIn Developer Console:
- Use the "Add assets" or attachment UI inside the product access request form. Upload the screencast and 2–3 screenshots and include the short description provided in `docs/linkedin_app_submission.md`.

Tips:
- For privacy, use a test account or blur any personal identifiable info in the screencast.
- Keep audio minimal; add captions or short text overlays describing each step.

