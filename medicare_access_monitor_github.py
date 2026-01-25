"""
Medicare ACCESS Program Monitor for Milu Health
Tracks policy changes, program updates, and strategic opportunities
Emails weekly summary to erika@miluhealth.com
GitHub Actions version - uses environment variables
"""

import feedparser
import anthropic
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import time
import os
import re

# Get credentials from environment variables
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

# Medicare and healthcare policy RSS feeds
RSS_FEEDS = [
    "https://www.cms.gov/newsroom/rss-feeds",
    "https://www.fiercehealthcare.com/rss.xml",
    "https://www.modernhealthcare.com/rss",
    "https://www.healthcaredive.com/feeds/news/",
    "https://khn.org/feed/",
    "https://www.healthaffairs.org/do/10.1377/hp.rss/full/",
    "https://www.ama-assn.org/rss/news.xml",
]

# Keywords for Medicare ACCESS and related programs
KEYWORDS = [
    "ACCESS", "ACO REACH", "Medicare Advantage", 
    "CMS Innovation Center", "CMMI",
    "Medicare Part D", "medication therapy management", "MTM",
    "value-based care", "risk adjustment",
    "Medicare payment", "Medicare policy",
    "star ratings", "quality measures",
    "beneficiary", "Medicare enrollment",
    "prescription drug coverage", "formulary",
    "prior authorization", "step therapy"
]

# High-priority terms
HIGH_PRIORITY = [
    "ACCESS program", "ACO REACH", "CMMI",
    "medication therapy management", "MTM",
    "Part D", "prescription drug"
]


def is_relevant_article(title, summary):
    """Check if article is relevant to Medicare ACCESS and policy"""
    text = (title + ' ' + summary).lower()
    
    # Must contain Medicare or CMS
    has_medicare = any(term in text for term in ["medicare", "cms", "centers for medicare"])
    if not has_medicare:
        return False
    
    # High priority if contains ACCESS or other key programs
    if any(term.lower() in text for term in HIGH_PRIORITY):
        return True
    
    # Or contains other relevant Medicare keywords
    if any(keyword.lower() in text for keyword in KEYWORDS):
        return True
    
    return False


def collect_articles():
    """Collect Medicare ACCESS and policy articles"""
    print("Collecting Medicare ACCESS and policy articles...")
    articles = []
    
    for i, feed_url in enumerate(RSS_FEEDS, 1):
        try:
            print(f"Checking feed {i}/{len(RSS_FEEDS)}...")
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                print(f"  No entries found")
                continue
            
            for entry in feed.entries[:25]:
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))
                
                if is_relevant_article(title, summary):
                    # Check recency (last 3 weeks)
                    pub_date = entry.get('published_parsed', entry.get('updated_parsed'))
                    if pub_date:
                        pub_datetime = datetime(*pub_date[:6])
                        if (datetime.now() - pub_datetime).days > 21:
                            continue
                    
                    articles.append({
                        'title': title,
                        'link': entry.get('link', ''),
                        'summary': summary[:2000],
                        'published': entry.get('published', entry.get('updated', 'Date unknown')),
                        'source': feed.feed.get('title', 'Unknown source')
                    })
            
            found_count = len([a for a in articles if a['source'] == feed.feed.get('title', 'Unknown source')])
            if found_count > 0:
                print(f"  Found {found_count} relevant articles")
            
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    # Remove duplicates
    unique_articles = {}
    for article in articles:
        simple_title = re.sub(r'[^\w\s]', '', article['title'].lower())
        if simple_title not in unique_articles:
            unique_articles[simple_title] = article
    
    articles = list(unique_articles.values())
    articles.sort(key=lambda x: x.get('published', ''), reverse=True)
    
    print(f"\nCollected {len(articles)} unique relevant articles")
    return articles


def create_executive_summary(articles):
    """Use Claude to create executive summary focused on Milu opportunities"""
    print("\nCreating executive summary with Claude API...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Prepare article list
    article_list = "\n\n".join([
        f"ARTICLE {i}:\nTitle: {art['title']}\nSource: {art['source']}\nDate: {art['published']}\nSummary: {art['summary'][:800]}\nLink: {art['link']}"
        for i, art in enumerate(articles, 1)
    ])
    
    prompt = f"""You are analyzing {len(articles)} recent articles about Medicare programs, healthcare policy, and the ACCESS program for a Lead Clinical Pharmacist at Milu Health.

Milu Health Context:
- Milu provides AI-powered medication management services (Merlin system)
- Target market: Medicare beneficiaries, especially ACCESS program participants
- Services: Pharmacist-led MTM, medication adherence, clinical decision support
- The ACCESS program represents a $500M+ market opportunity for Milu

Please analyze these articles and create:

1. EXECUTIVE SUMMARY:
   - Brief 2-3 sentence overview of major policy/program developments
   - 5-7 bullet points covering:
     * Key Medicare policy changes or announcements
     * ACCESS/ACO REACH program updates
     * Part D or MTM program changes
     * Payment model or star ratings updates
     * Regulatory changes affecting medication management
   - Be specific about effective dates, dollar amounts, enrollment numbers when available

2. KEY TAKEAWAYS (5-7 bullet points):
   - Most critical policy changes that could impact medication management businesses
   - New opportunities or requirements for Medicare providers
   - Threats or challenges to current business models
   - Actionable intelligence for strategic planning

3. MILU STRATEGIC IMPLICATIONS:
   - Brief 2-3 sentence context about how these changes affect Milu's business
   - 4-6 bullet points covering:
     * Direct opportunities in ACCESS or other Medicare programs
     * Required changes to service offerings or compliance
     * Competitive positioning implications
     * Partnership or growth opportunities
     * Risk mitigation strategies
   - Be specific and actionable - what should Milu DO in response?

Articles to analyze:

{article_list}

Format your response with clear section headers and bullet points."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
        
    except Exception as e:
        print(f"Error creating summary: {e}")
        return f"Error creating executive summary: {str(e)}"


def create_html_email(executive_summary, articles):
    """Create formatted HTML email"""
    print("Creating HTML email...")
    
    # Process summary into HTML
    html_parts = ['<div style="font-family: Arial, sans-serif; font-size: 12pt; max-width: 800px;">']
    
    # Header
    html_parts.append('<h1 style="color: #0066cc; text-align: center;">Medicare ACCESS Program Weekly Brief</h1>')
    html_parts.append(f'<p style="text-align: center; color: #666; font-size: 11pt;">Week ending {datetime.now().strftime("%B %d, %Y")}</p>')
    html_parts.append(f'<p style="text-align: center; color: #666; font-size: 10pt; font-style: italic;">Articles analyzed: {len(articles)} | Focus: Medicare ACCESS, Policy Changes, MTM Programs</p>')
    html_parts.append('<hr style="border: 1px solid #ddd; margin: 20px 0;">')
    
    # Process executive summary
    lines = executive_summary.split('\n')
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Section headers
        if line.startswith('##') or 'EXECUTIVE SUMMARY' in line or 'KEY TAKEAWAYS' in line or 'MILU STRATEGIC' in line:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            section = line.replace('##', '').replace('#', '').strip()
            html_parts.append(f'<h2 style="color: #0066cc; margin-top: 20px;">{section}</h2>')
            continue
        
        # Bullet points
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            if not in_list:
                html_parts.append('<ul style="line-height: 1.6;">')
                in_list = True
            text = line[1:].strip().replace('**', '<strong>').replace('**', '</strong>')
            html_parts.append(f'<li>{text}</li>')
        else:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(f'<p style="line-height: 1.6;">{line}</p>')
    
    if in_list:
        html_parts.append('</ul>')
    
    # Article reference list
    html_parts.append('<hr style="border: 1px solid #ddd; margin: 30px 0;">')
    html_parts.append('<h2 style="color: #0066cc;">Article Reference List</h2>')
    html_parts.append('<p style="font-style: italic; color: #666;">All articles analyzed this week:</p>')
    
    for i, article in enumerate(articles, 1):
        html_parts.append(f'<div style="margin: 15px 0; padding: 10px; background: #f9f9f9; border-left: 3px solid #0066cc;">')
        html_parts.append(f'<p style="margin: 5px 0;"><strong>{i}. {article["title"]}</strong></p>')
        html_parts.append(f'<p style="margin: 5px 0; font-size: 10pt; color: #666;">{article["source"]} | {article["published"]}</p>')
        html_parts.append(f'<p style="margin: 5px 0; font-size: 10pt;"><a href="{article["link"]}" style="color: #0066cc;">{article["link"]}</a></p>')
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    
    return '\n'.join(html_parts)


def send_email(html_content, num_articles):
    """Send email via Gmail"""
    print("Sending email...")
    
    # Email configuration
    sender_email = "alexander.erika@gmail.com"
    receiver_email = "erika@miluhealth.com"
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'Medicare ACCESS Weekly Brief - {datetime.now().strftime("%b %d, %Y")} ({num_articles} articles)'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    # Attach HTML
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    
    try:
        # Connect to Gmail
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, GMAIL_APP_PASSWORD.replace(' ', ''))
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Email sent successfully to {receiver_email}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def main():
    """Main execution"""
    print("=" * 80)
    print("Medicare ACCESS Program Monitor - Milu Health")
    print(f"Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    try:
        # Collect articles
        articles = collect_articles()
        
        if not articles:
            print("\n" + "=" * 80)
            print("No relevant articles found this week.")
            print("Focus areas: Medicare ACCESS, policy changes, MTM programs")
            print("=" * 80)
            return
        
        # Create executive summary
        executive_summary = create_executive_summary(articles)
        
        # Create HTML email
        html_content = create_html_email(executive_summary, articles)
        
        # Send email
        success = send_email(html_content, len(articles))
        
        if success:
            print()
            print("=" * 80)
            print("SUCCESS! Weekly brief emailed")
            print(f"To: erika@miluhealth.com")
            print(f"Articles analyzed: {len(articles)}")
            print(f"Run completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
