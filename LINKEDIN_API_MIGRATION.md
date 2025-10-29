# LinkedIn API Migration Guide

## Overview

LinkedIn has recently made significant changes to their public API, deprecating several endpoints and requiring migration to OpenID Connect for authentication. This document explains the changes and how they affect linkedinAgent.

## What Changed?

### 1. Profile Endpoint Migration (✅ Fixed)

**Old Endpoint (Deprecated):**
```
GET https://api.linkedin.com/v2/me
```

**New Endpoint:**
```
GET https://api.linkedin.com/v2/userinfo
```

**What We Did:**
- Updated `LinkedInApiClient.get_profile()` to use `/v2/userinfo`
- Added backward compatibility by mapping the `sub` field to `id`
- No breaking changes for existing code

**Required Scopes:**
- Old: `r_liteprofile`, `r_emailaddress`
- New: `openid`, `profile`, `email`

### 2. Search Endpoint Deprecation (⚠️ Unavailable)

**Deprecated Endpoint:**
```
GET https://api.linkedin.com/v2/search?q=keywords&keywords=...
```

**Status:** This endpoint has been completely deprecated by LinkedIn for public apps. No replacement is available.

**Impact:**
- Auto-comment feature that searched for posts is currently unavailable
- The `search_for_posts()` method now returns an empty list with a warning
- Manual commenting via the web UI is still available

**Workaround:**
Use manual commenting through the dashboard at `http://localhost:5000/manual_comment` or `/queue` endpoints.

## What You Need to Do

### For New Users

1. **Enable OpenID Connect in LinkedIn Developer Portal:**
   - Go to your app in [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
   - Under "Products", request "Sign In with LinkedIn using OpenID Connect"
   - Wait for approval (usually instant for this product)

2. **Update Your Scopes:**
   Make sure your `.env` file or OAuth configuration includes:
   ```
   LINKEDIN_SCOPES=openid profile w_member_social
   ```

3. **Re-authenticate:**
   - Visit `http://localhost:5000/login` (or your deployment URL)
   - Complete the OAuth flow
   - The new token will work with the updated endpoints

### For Existing Users

If you're already using linkedinAgent:

1. **Check Your App Configuration:**
   - Verify that "Sign In with LinkedIn using OpenID Connect" is enabled in your LinkedIn app
   - If not, request it in the Developer Portal

2. **Update Scopes (if needed):**
   - Edit your `.env` file and update `LINKEDIN_SCOPES` to: `openid profile w_member_social`

3. **Re-authenticate:**
   - Log out: `http://localhost:5000/logout`
   - Log back in: `http://localhost:5000/login`

4. **Restart Services:**
   ```bash
   docker compose restart
   ```

## Expected Behavior After Migration

### ✅ Working Features:
- User profile retrieval (now using `/userinfo`)
- Post creation and sharing
- Adding reactions (likes)
- Submitting comments on specific posts
- Turkish summary follow-ups
- Connection invitations
- Manual commenting via web UI

### ⚠️ Currently Unavailable:
- Automatic post search and discovery
- Automated commenting on discovered posts

The scheduler will skip the auto-commenting job and log a message instead of throwing errors.

## Error Messages Explained

### 403 Forbidden on `/v2/me`
**Before Fix:** This error occurred because `/v2/me` is deprecated.  
**After Fix:** The client now uses `/v2/userinfo` - no more 403 errors.

### 404 Not Found on `/v2/search`
**Before Fix:** This error occurred when trying to search for posts.  
**After Fix:** Search functionality is disabled gracefully. No errors, just skips the operation.

## API Version Compatibility

The changes are backward compatible:
- `get_profile()` still returns a dict with an `id` field
- Existing code using the client doesn't need changes
- Tests have been updated and all pass

## Timeline

- **October 2024:** LinkedIn started deprecating `/v2/me` and search endpoints
- **October 29, 2024:** linkedinAgent updated to use OpenID Connect
- **Future:** LinkedIn may provide new discovery/search APIs (status unknown)

## Need Help?

If you encounter issues:

1. Check the [Troubleshooting](README.md#troubleshooting) section
2. Verify your LinkedIn app configuration
3. Check logs: `docker compose logs worker`
4. Open an issue on GitHub with error details

## References

- [LinkedIn OpenID Connect Documentation](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2)
- [LinkedIn API Error Handling](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/error-handling)
- [Sign In with LinkedIn using OpenID Connect](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2)
