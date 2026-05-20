# /send-slack

Post a message to Slack via an Incoming Webhook. Supports multiple named channels.

## Instructions

### Prerequisites

The user must have at least one Slack webhook in their `.env` file:

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/...         # default channel
SLACK_WEBHOOK_SEO=https://hooks.slack.com/...         # named: seo
SLACK_WEBHOOK_PPC=https://hooks.slack.com/...         # named: ppc
SLACK_WEBHOOK_CLIENTS=https://hooks.slack.com/...     # named: clients
```

If no `SLACK_WEBHOOK_*` vars are configured, direct them to:
1. Go to https://api.slack.com/messaging/webhooks
2. Create an Incoming Webhook for their workspace/channel
3. Add the webhook URL to `.env`

### Step 0: Channel Selection (multi-channel)

Check for multiple `SLACK_WEBHOOK_*` environment variables:

```bash
source .env
env | grep '^SLACK_WEBHOOK_' | sed 's/=.*//' | sort
```

- **If only `SLACK_WEBHOOK_URL` exists** → use it directly, skip to Step 1.
- **If multiple `SLACK_WEBHOOK_*` vars exist** → list them and ask the user which channel to post to:

```
Found 3 Slack channels:
  1. default  (SLACK_WEBHOOK_URL)
  2. seo      (SLACK_WEBHOOK_SEO)
  3. ppc      (SLACK_WEBHOOK_PPC)

Which channel? (1-3):
```

Resolve the chosen variable name to get the webhook URL.

### Step 1: Compose Message

Ask the user what they want to post. Common patterns:
- Results from a workflow (e.g., "post the SEO report we just ran")
- Custom update or announcement
- Client status summary

### Step 2: Format Message

Format the message using Slack's mrkdwn syntax:
- `*bold*` for emphasis
- Bullet lists with `-` or `•`
- Links: `<url|text>`
- Emoji: `:white_check_mark:`, `:chart_with_upwards_trend:`, etc.

### Step 3: Send

Use the `integrations/slack/send-message.sh` script:

```bash
source .env
# Use the webhook URL from the selected channel (default: SLACK_WEBHOOK_URL)
bash integrations/slack/send-message.sh "$SELECTED_WEBHOOK_URL" "Your formatted message here"
```

Or send directly via curl:

```bash
curl -X POST "$SELECTED_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"text": "Your message here"}'
```

### Step 4: Confirm

Show the user what was sent and confirm delivery.

## Output Format

```
✅ Message sent to Slack

📨 Channel: {channel_name} (from webhook config)
📝 Preview:
   {message preview}
```

## Golden Rules

- Never expose the webhook URL in output
- Always show a preview before sending
- Format for Slack's mrkdwn, not regular markdown
