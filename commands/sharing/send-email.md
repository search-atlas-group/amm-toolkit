# /send-email

Send an email via the Resend API.

## Instructions

### Prerequisites

The user must have `RESEND_API_KEY` and `EMAIL_FROM` set in their `.env` file. If not configured, direct them to:
1. Sign up at https://resend.com
2. Create an API key under API Keys
3. (Optional) Verify a sender domain under Domains
4. Add `RESEND_API_KEY` and `EMAIL_FROM` to `.env`

For testing without a verified domain, they can use `onboarding@resend.dev` as the from address.

### Step 1: Collect Details

Ask the user for:
- **Recipient email** — who should receive this?
- **Subject** — what's the email about?
- **Content** — what should the body say?

Common patterns:
- Send a client their monthly SEO report
- Share workflow results (e.g., "email the PPC report to the client")
- Custom update or notification

### Step 2: Format Body

Compose the email body as HTML:
- Use `<h1>`, `<h2>` for headings
- Use `<p>` for paragraphs
- Use `<ul><li>` for bullet lists
- Use `<strong>` for bold, `<a href="">` for links
- Use `<table>` for tabular data (metrics, comparisons)

Keep formatting clean and professional.

### Step 3: Send

Use the `integrations/email/send-email.sh` script:

```bash
source .env
bash integrations/email/send-email.sh "$RESEND_API_KEY" "$EMAIL_FROM" "client@example.com" "Subject" "<html body>"
```

### Step 4: Confirm

Show the user what was sent and confirm delivery.

## Output Format

```
✅ Email sent

📧 To: {recipient}
📋 Subject: {subject}
📝 Preview:
   {body preview — first ~200 chars of plain text}
```

## Golden Rules

- Never expose the API key in output
- Always show a preview before sending
- Always confirm the recipient address before sending
- Format body as clean HTML, not markdown
