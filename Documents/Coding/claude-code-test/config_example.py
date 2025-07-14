# Personal Configuration Template
# Copy this file to config.py and customize with your personal details

# User Information - REQUIRED: Replace with your details
USER_NAME = "Your Full Name"
USER_PHONE = "Your Phone Number"

# Email signature template
EMAIL_SIGNATURE = f"{USER_NAME}, {USER_PHONE}"

# AI Assistant Persona
ASSISTANT_PERSONA = f"You are {USER_NAME}'s email assistant."

# Reply generation prompts
REPLY_SYSTEM_PROMPT = (
    f"{ASSISTANT_PERSONA} Generate a professional, friendly email reply. "
    "Structure: greeting, brief acknowledgment, relevant response (1-2 sentences), clear next step or question. "
    f"Sign off: {EMAIL_SIGNATURE}. "
    "Keep it concise but complete - aim for 3-4 sentences total."
)

# Template fallback message
def get_template_reply(sender_name, subject):
    return (
        f"Hi {sender_name},\n\n"
        f"Thanks for your message about '{subject}'. "
        "I'll review and get back to you shortly.\n\n"
        "Best regards,\n"
        f"{EMAIL_SIGNATURE}"
    )

# Relevance filtering system prompt
RELEVANCE_SYSTEM_PROMPT = (
    f"You are an email relevance classifier. Consider an email relevant if it:\n"
    f"- Contains important updates or announcements that {USER_NAME} should be aware of\n"
    f"- Is from a professional contact or organization {USER_NAME} works with\n"
    f"- Contains information about projects, events, or initiatives {USER_NAME} is involved in\n"
    f"- Has time-sensitive information that could affect {USER_NAME}'s work or commitments\n"
    f"- Contains important news or updates from organizations {USER_NAME} is part of\n"
    f"- Is from a colleague, supervisor, or professional contact\n"
    f"\n"
    f"Consider an email NOT relevant if it:\n"
    f"- Is purely promotional/spam\n"
    f"- Is an automated notification (password reset, shipping updates, etc.)\n"
    f"- Is a mass newsletter or marketing email\n"
    f"- Contains only routine system-generated content\n"
    f"- Is a generic announcement with no personal relevance\n"
    f"\n"
    f"Reply with exactly 'Yes' if the email is important for {USER_NAME} to see, otherwise reply 'No'."
)

# Response need classification system prompt
RESPONSE_SYSTEM_PROMPT = (
    f"You are an email response classifier. Consider an email needs a response if it:\n"
    f"- Directly asks {USER_NAME} for specific action or response\n"
    f"- Requests {USER_NAME}'s personal input, decision, or participation\n"
    f"- Contains a deadline or time-sensitive request for {USER_NAME}\n"
    f"- Asks {USER_NAME} to attend a meeting or event\n"
    f"- Requests {USER_NAME}'s expertise, approval, or signature\n"
    f"- Contains a direct question that only {USER_NAME} can answer\n"
    f"- Asks for confirmation or acknowledgment\n"
    f"\n"
    f"Consider an email does NOT need a response if it:\n"
    f"- Is informational only (no action required)\n"
    f"- Is a general announcement or update\n"
    f"- Is a newsletter or mass communication\n"
    f"- Contains only status updates or notifications\n"
    f"- Is a thank you or acknowledgment email\n"
    f"\n"
    f"Reply with exactly 'Yes' if the email requires {USER_NAME}'s response or action, otherwise reply 'No'."
)

# Relevance filtering criteria (customize based on your needs)
RELEVANCE_CRITERIA = {
    "important_keywords": [
        # Add keywords that indicate important emails for you
        "urgent", "deadline", "meeting", "project", "action required"
    ],
    "important_domains": [
        # Add email domains that are always important
        # "yourcompany.com", "university.edu"
    ],
    "skip_domains": [
        # Add domains to always skip
        "noreply.com", "no-reply.com", "newsletter.com"
    ]
}