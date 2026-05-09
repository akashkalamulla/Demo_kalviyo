import requests
import anthropic
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

KLAVIYO_PRIVATE_KEY = os.getenv("KLAVIYO_PRIVATE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EMAIL_LIST_ID = "S8iE8h"

# Used for campaign creation, template creation (revision 2024-02-15)
headers = {"Authorization": f"Klaviyo-API-Key {KLAVIYO_PRIVATE_KEY}", "revision": "2024-02-15", "Content-Type": "application/vnd.api+json", "accept": "application/vnd.api+json"}

# Used for template assignment only (requires newer revision)
assign_headers = {"Authorization": f"Klaviyo-API-Key {KLAVIYO_PRIVATE_KEY}", "revision": "2025-01-15", "Content-Type": "application/vnd.api+json", "accept": "application/vnd.api+json"}

# ── STEP 1: Generate newsletter copy via Claude ──────────────────────────────

print("Generating newsletter copy...")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

weekly_brief = "Topic: Benefits of magnesium for sleep. Key message: our new magnesium supplement launches next week. Tone: warm, educational."

message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    system="You are a wellness brand copywriter. Write a short weekly newsletter (max 200 words). Return only the newsletter body text, no subject line.",
    messages=[{"role": "user", "content": weekly_brief}],
)

newsletter_copy = message.content[0].text
print(f"Copy generated: {newsletter_copy[:80]}...")

# ── STEP 2: Wrap copy in basic HTML email template ───────────────────────────

html_content = f"""
<html>
<body style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
  <h1 style="color: #2e7d5e; font-size: 24px;">Your Weekly Wellness Note</h1>
  <div style="font-size: 16px; line-height: 1.7;">
    {newsletter_copy.replace(chr(10), '<br>')}
  </div>
  <hr style="margin-top: 40px; border: none; border-top: 1px solid #eee;">
  <p style="font-size: 12px; color: #999;">You're receiving this because you subscribed to our wellness newsletter.</p>
</body>
</html>
"""

# ── STEP 3: Create Klaviyo campaign ──────────────────────────────────────────

print("Creating Klaviyo campaign...")

campaign_payload = {
    "data": {
        "type": "campaign",
        "attributes": {
            "name": f"Weekly Newsletter - {datetime.now().strftime('%Y-%m-%d')}",
            "audiences": {"included": [EMAIL_LIST_ID]},
            "send_strategy": {"method": "immediate"},
            "campaign-messages": {
                "data": [
                    {
                        "type": "campaign-message",
                        "attributes": {
                            "label": "Main message",
                            "channel": "email",
                            "content": {
                                "subject": "This week: the sleep mineral you're probably missing",
                                "preview_text": "Magnesium and your rest — here's what the research says.",
                                "from_email": "akashinnodata@gmail.com",
                                "from_label": "Wellness Brand",
                                "reply_to_email": "akashinnodata@gmail.com",
                            },
                        },
                    }
                ]
            },
        },
    }
}

campaign_response = requests.post("https://a.klaviyo.com/api/campaigns/", headers=headers, json=campaign_payload)

print(f"Campaign creation status: {campaign_response.status_code}")

if campaign_response.status_code != 201:
    print("ERROR:", campaign_response.json())
    exit()

campaign_data = campaign_response.json()
campaign_id = campaign_data["data"]["id"]
message_id = campaign_data["data"]["relationships"]["campaign-messages"]["data"][0]["id"]
print(f"Campaign ID: {campaign_id}")
print(f"Message ID: {message_id}")

# ── STEP 4: Create a template with the HTML content ──────────────────────────

print("Creating HTML template...")

template_payload = {
    "data": {"type": "template", "attributes": {"name": f"Newsletter Template - {datetime.now().strftime('%Y-%m-%d')}", "editor_type": "CODE", "html": html_content, "text": newsletter_copy}}
}

template_response = requests.post("https://a.klaviyo.com/api/templates/", headers=headers, json=template_payload)

print(f"Template creation status: {template_response.status_code}")

if template_response.status_code != 201:
    print("ERROR:", template_response.json())
    exit()

template_id = template_response.json()["data"]["id"]
print(f"Template ID: {template_id}")

# ── STEP 5: Assign template to campaign message ───────────────────────────────

print("Assigning template to campaign message...")

assign_payload = {"data": {"type": "campaign-message", "id": message_id, "relationships": {"template": {"data": {"type": "template", "id": template_id}}}}}

assign_response = requests.post("https://a.klaviyo.com/api/campaign-message-assign-template", headers=assign_headers, json=assign_payload)

print(f"Template assignment status: {assign_response.status_code}")

if assign_response.status_code not in [200, 201, 202]:
    print("ERROR:", assign_response.json())
    exit()

# ── DONE ─────────────────────────────────────────────────────────────────────

print("\n✅ Pipeline complete.")
print(f"Campaign '{campaign_id}' created in Klaviyo with Claude-generated copy.")
print(f"Template '{template_id}' assigned to message '{message_id}'.")
print("Check your Klaviyo dashboard → Campaigns to see it.")
