# Automated Post and Profile Discovery

## Overview

The LinkedIn Agent now includes **fully automated discovery** systems that find relevant posts to comment on and profiles to invite - all without using LinkedIn's deprecated search API.

## 🤖 Automated Post Discovery

### How It Works

The system discovers LinkedIn posts through multiple indirect methods:

1. **RSS Feed Monitoring**
   - Monitors tech news RSS feeds (TechCrunch, Wired, Ars Technica)
   - Extracts LinkedIn post URLs mentioned in articles
   - Filters by your interests

2. **Hashtag-Based Discovery**
   - Generates LinkedIn hashtag URLs based on your interests
   - Constructs targeted URLs like `linkedin.com/feed/hashtag/ai/`
   - Discovers trending posts in your field

3. **Smart Filtering**
   - Matches posts against your interests (from `.env` file)
   - Selects most relevant posts
   - Randomizes selection for variety

### Your Interests

Configure in `.env`:
```bash
INTERESTS=ai,llm,product,saas,startup,founder,ux,devtools,infra
```

The system uses these keywords to:
- Filter discovered posts
- Generate relevant hashtag searches
- Target appropriate content

### Post Discovery Process

```
1. Check user interests from config
2. Search RSS feeds for LinkedIn mentions
3. Extract post URLs from articles
4. Generate hashtag-based suggestions
5. Filter and rank by relevance
6. Select random post from top matches
7. Generate AI comment
8. Post comment
```

### Safety Features

- **Rate Limiting**: Maximum posts per day
- **Quality Control**: Only comments on relevant posts
- **Error Handling**: Graceful failures without spam
- **Logging**: All actions tracked for review

## 🛡️ Safe Profile Discovery

### How It Works

Profile discovery is designed with **account safety as top priority**:

1. **Conservative Limits**
   - Maximum 2 invitations per day
   - Daily counter resets at midnight
   - Cannot exceed limit

2. **Interest-Based Targeting**
   - Uses your interests to suggest profiles
   - Targets professionals in your field
   - Avoids random/spam invitations

3. **Manual Override**
   - System can be configured to require approval
   - Suggestions generated but not auto-sent
   - User maintains full control

### Configuration

In `.env`:
```bash
# Maximum invitations per day (recommended: 2)
INVITES_MAX_PER_DAY=2

# Enable/disable auto-invitations
INVITES_ENABLED=false

# Batch size (keep at 1 for safety)
INVITES_BATCH_SIZE=1
```

### Safety Mechanisms

#### Daily Limits
```python
# Enforced at code level
max_daily_invites = 2
invited_today = 0

# Resets daily
if today != last_invite_date:
    invited_today = 0
```

#### Smart Targeting
- Only profiles matching interests
- 2nd degree connections preferred
- Industry-specific targeting
- No cold/spam invitations

#### LinkedIn Policy Compliance
- Respects rate limits
- Personalized messages
- No bulk invitations
- User consent required

## 🔧 Technical Implementation

### Post Discovery Class

```python
from src.post_discovery import PostDiscovery

# Initialize with interests
discovery = PostDiscovery(['ai', 'startup', 'product'])

# Discover posts
posts = await discovery.discover_posts_smart(max_posts=5)

# Returns list of:
# {
#   'url': 'https://linkedin.com/feed/update/...',
#   'title': 'Post title',
#   'source': 'RSS Feed',
#   'discovered_at': '2024-10-30T...'
# }
```

### Profile Discovery Class

```python
from src.post_discovery import ProfileDiscovery

# Initialize with safety limits
discovery = ProfileDiscovery(
    interests=['ai', 'startup'], 
    max_daily_invites=2
)

# Check if can send
if discovery.can_send_invite():
    profile = await discovery.discover_profiles_safe()
    if profile:
        # Send invitation
        discovery.record_invite_sent()
```

## 📊 Monitoring & Logs

### Success Logs

```
[2024-10-30 14:23:45] Auto Comment Added
Details: Commented on: AI in Product Development
URL: https://linkedin.com/feed/update/urn:li:activity:1234567890/

[2024-10-30 15:30:12] Invitation Sent
Details: Sent invitation to john-doe-ai-founder
URL: https://linkedin.com/in/john-doe-ai-founder/
```

### Safety Logs

```
[2024-10-30 16:45:00] Invitation Skipped
Details: Daily invite limit reached (safety)

[2024-10-30 17:00:00] Commenting Skipped
Details: No relevant posts discovered
```

## ⚠️ Safety Guidelines

### DO:
✅ Keep `INVITES_MAX_PER_DAY` at 2 or lower
✅ Monitor action logs regularly
✅ Review interests to stay relevant
✅ Use meaningful invitation messages
✅ Respect LinkedIn's terms of service

### DON'T:
❌ Exceed 2-3 invitations per day
❌ Send generic/spam messages
❌ Target random profiles
❌ Disable safety mechanisms
❌ Ignore LinkedIn warnings

## 🚨 Account Safety

### Risk Levels

**Low Risk (Current Settings)**
- 2 invitations/day
- Relevant comments only
- Interest-based targeting
- Rate limiting active

**Medium Risk**
- 5+ invitations/day
- Generic comments
- Broad targeting

**High Risk (Avoid)**
- 10+ invitations/day
- Automated bulk actions
- Random targeting
- No rate limiting

### Best Practices

1. **Start Slow**
   - Begin with 1-2 invitations/day
   - Monitor for warnings
   - Increase gradually if safe

2. **Stay Relevant**
   - Only comment on posts you understand
   - Send invitations to relevant people
   - Maintain authenticity

3. **Monitor Regularly**
   - Check action logs daily
   - Look for LinkedIn warnings
   - Adjust if needed

4. **Personalize**
   - Use AI to generate unique comments
   - Customize invitation messages
   - Avoid templates

## 📈 Expected Results

### Post Discovery
- **Discovery Rate**: 3-5 posts per run
- **Comment Success**: 80-90%
- **Relevance**: High (interest-filtered)

### Profile Discovery
- **Daily Invites**: 0-2 (safety limit)
- **Acceptance Rate**: Varies by targeting
- **Account Safety**: Maximum

## 🔍 Troubleshooting

### "No posts discovered"
- Check interests in `.env`
- Verify RSS feeds are accessible
- Try manual trigger first

### "Daily invite limit reached"
- This is intentional for safety
- Limit resets at midnight
- Do not override

### "Could not extract URN"
- Post URL format may have changed
- Check logs for URL pattern
- Report if persistent

## 🎯 Optimization Tips

### Better Post Discovery
1. **Refine Interests**: Use specific keywords
2. **Add RSS Feeds**: Include industry-specific sources
3. **Monitor Trends**: Update interests quarterly

### Better Profile Discovery
1. **Targeted Interests**: Specific > general
2. **Network Quality**: Quality > quantity
3. **Engagement**: Comment before inviting

## 📚 References

- [LinkedIn API Best Practices](https://www.linkedin.com/help/linkedin/answer/a1339724)
- [Profile Discovery Code](../src/post_discovery.py)
- [Worker Integration](../src/worker.py)
- [Safety Configuration](.env.example)
