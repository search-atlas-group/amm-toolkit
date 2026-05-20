# /send-discord

Post a message to Discord via a Webhook.

## Instructions

### Prerequisites

The user must have `DISCORD_WEBHOOK_URL` set in their `.env` file. If not configured, direct them to:
1. Open Discord → Server Settings → Integrations → Webhooks
2. Create a new webhook for their target channel
3. Copy the webhook URL and add it to `.env`

### Step 1: Compose Message

Ask the user what they want to post. Common patterns:
- Results from a workflow (e.g., "post the SEO report we just ran")
- Custom update or announcement
- Client status summary

### Step 2: Format Message

Format the message using Discord markdown syntax:
- `**bold**` for emphasis
- Bullet lists with `-`
- Links: `[text](url)`
- Emoji: standard Unicode emoji or Discord `:emoji_name:`

Note: Discord messages have a 2000 character limit. If the message is longer, split it into multiple sends.

### Step 3: Send

Use the `integrations/discord/send-message.sh` script:

```bash
source .env
bash integrations/discord/send-message.sh "$DISCORD_WEBHOOK_URL" "Your formatted message here"
```

Or send directly via curl:

```bash
curl -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Your message here"}'
```

### Step 4: Confirm

Show the user what was sent and confirm delivery.

## Output Format

```
✅ Message sent to Discord

📨 Channel: {channel_name} (from webhook config)
📝 Preview:
   {message preview}
```

## Golden Rules

- Never expose the webhook URL in output
- Always show a preview before sending
- Format for Discord markdown, not Slack mrkdwn
- Split messages over 2000 characters
