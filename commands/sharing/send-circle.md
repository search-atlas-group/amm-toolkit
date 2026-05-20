# /send-circle

Post a message to a Circle community space.

## Instructions

### Prerequisites

The user must have these set in their `.env` file:
- `CIRCLE_API_KEY` — from Circle → Settings → API
- `CIRCLE_COMMUNITY_ID` — their community ID

If not configured, direct them to set up their Circle API credentials.

### Step 1: Choose Space

Use the Circle API to list available spaces:

```bash
source .env
curl -s -H "Authorization: Bearer $CIRCLE_API_KEY" \
  "https://app.circle.so/api/v1/spaces?community_id=$CIRCLE_COMMUNITY_ID"
```

Present the spaces and ask the user which one to post to.

### Step 2: Compose Post

Ask the user what they want to post. Common patterns:
- Client success story / case study
- Weekly/monthly results summary
- Tool tutorial or tip

Collect:
- **Title** (required for Circle posts)
- **Body** (markdown content)

### Step 3: Send

Use the `integrations/circle/post-to-space.sh` script or send directly:

```bash
source .env
curl -X POST "https://app.circle.so/api/v1/posts" \
  -H "Authorization: Bearer $CIRCLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": "'"$CIRCLE_COMMUNITY_ID"'",
    "space_id": "'"$SPACE_ID"'",
    "name": "Post Title",
    "body": "Post body in markdown"
  }'
```

### Step 4: Confirm

Show the post URL and confirm delivery.

## Output Format

```
✅ Posted to Circle

📍 Space: {space_name}
📝 Title: {post_title}
🔗 Link: {post_url}
```

## Golden Rules

- Circle API uses Bearer token auth (unlike Slack webhooks)
- Always preview the post before sending
- Circle supports markdown in post bodies
