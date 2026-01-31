"""
Daily Leadership Insight Email
Sends Monday-Thursday mornings to alexander.erika@gmail.com
Focus: Team interaction, adding value, inclusive leadership, positivity
"""

import anthropic
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import os

def generate_leadership_insight():
    """Generate daily leadership insight using Claude"""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    today = datetime.now().strftime("%A, %B %d, %Y")
    
    prompt = f"""Generate a brief, actionable leadership insight email for {today}.

Context: The recipient is Erika, a Lead Clinical Pharmacist at Milu Health (healthcare AI startup). She has 19 years of pharmacy experience, triple board certifications, and is building clinical workflows while working with a team of nurses and pharmacists.

Create an email with:
1. A brief inspirational opening (2-3 sentences max)
2. ONE specific, research-backed insight about leadership, team interaction, or workplace positivity
3. A concrete micro-action she can take TODAY to practice this (be specific and practical)
4. Keep it under 150 words total

Focus areas (rotate through these):
- Building psychological safety in teams
- Inclusive communication practices
- Adding strategic value through clinical expertise
- Positive framing and solution-focused thinking
- Cross-functional collaboration
- Recognition and appreciation
- Active listening techniques
- Managing conflict constructively

Tone: Warm, practical, evidence-based (cite research when relevant), empowering

Do NOT use: Generic platitudes, overly formal language, or vague advice

Format as HTML for email."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text

def send_email(content):
    """Send the leadership insight email"""
    from_email = "erika@miluhealth.com"
    to_email = "alexander.erika@gmail.com"
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Daily Leadership Insight - {datetime.now().strftime('%A, %b %d')}"
    msg['From'] = from_email
    msg['To'] = to_email
    
    # Add HTML content
    html_part = MIMEText(content, 'html')
    msg.attach(html_part)
    
    # Send via Gmail
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(from_email, gmail_password)
        smtp.send_message(msg)
    
    print(f"✅ Daily leadership insight sent to {to_email}")

def main():
    print(f"Generating daily leadership insight for {datetime.now().strftime('%A, %B %d, %Y')}...")
    
    try:
        # Generate insight
        content = generate_leadership_insight()
        
        # Send email
        send_email(content)
        
        print("Success! Daily insight delivered.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
