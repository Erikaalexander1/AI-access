"""
Pharmacy & Medication Management AI Monitor for Milu Health
Focus: Medication adherence, safety, Medicare ACCESS, MTM, clinical pharmacy AI
Emails weekly summary to alexander.erika@gmail.com
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

# Pharmacy and medication-focused RSS feeds
RSS_FEEDS = [
    "https://www.pharmacytimes.com/rss",
    "https://www.pharmacist.com/RSS",
    "https://www.healthcareitnews.com/rss/artificial-intelligence",
    "https://www.mobihealthnews.com/feed",
    "https://www.fiercehealthcare.com/rss.xml",
    "https://www.modernhealthcare.com/section/technology?rss=1",
    "https://healthitanalytics.com/feed",
    "https://medcitynews.com/feed/",
]

# Pharmacy and medication-specific keywords
PHARMACY_KEYWORDS = [
    "medication", "pharmacy", "pharmacist", "drug",
    "prescription", "adherence", "MTM", "medication therapy management",
    "polypharmacy", "deprescribing", "drug interaction",
    "medication safety", "medication error", "adverse drug",
    "clinical pharmacy", "pharmaceutical care",
    "medication reconciliation", "medication review"
]

MEDICARE_KEYWORDS = [
    "Medicare", "ACCESS", "CMS", "Part D",
    "medication therapy management", "MTM",
    "star ratings", "Medicare Advantage"
]

AI_MEDICATION_KEYWORDS = [
    "AI medication", "artificial intelligence pharmacy",
    "machine learning drug", "predictive medication",
    "automated dispensing", "clinical decision support medication",
    "EHR medication", "e-prescribing", "medication alert"
]

def is_relevant_article(title, summary):
    """Check if article is relevant to pharmacy/medication management"""
    text = (title + ' ' + summary).lower()
    
    # High priority: Medicare/ACCESS programs
    if any(keyword.lower() in text for keyword in MEDICARE_KEYWORDS):
        return True
    
    # High priority: AI + medication/pharmacy
    has_ai = any(term in text for term in ["ai", "artificial intelligence", "machine learning", "automation", "algorithm"])
    has_pharmacy = any(keyword.lower() in text for keyword in PHARMACY_KEYWORDS)
    if has_ai and has_pharmacy:
        return True
    
    # Medium priority: Pharmacy innovation/technology
    if has_pharmacy and any(term in text for term in ["technology", "digital", "innovation", "system", "platform"]):
        return True
    
    # Exclude non-pharmacy healthcare AI
    exclude_terms = ["imaging", "radiology", "ultrasound", "surgery", "robot surgery", 
                     "diagnostic imaging", "pathology", "NASA", "space"]
    if any(term in text for term in exclude_terms):
        return False
    
    return False


def collect_articles():
    """Collect pharmacy and medication-focused articles"""
    print("Collecting pharmacy and medication management articles...")
    articles = []
    
    for i, feed_url in enumerate(RSS_FEEDS, 1):
        try:
            print(f"Checking feed {i}/{len(RSS_FEEDS)}...")
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                print(f"  No entries found")
                continue
            
            for entry in feed.entries[:20]:
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))
                
                if is_relevant_article(title, summary):
                    # Check recency
                    pub_date = entry.get('published_parsed', entry.get('updated_parsed'))
                    if pub_date:
                        pub_datetime = datetime(*pub_date[:6])
                        if (datetime.now() - pub_datetime).days > 21:  # 3 weeks
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
    """Use Claude to create executive summary of all articles"""
    print("\nCreating executive summary with Claude API...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Prepare article list for Claude
    article_list = "\n\n".join([
        f"ARTICLE {i}:\nTitle: {art['title']}\nSource: {art['source']}\nDate: {art['published']}\nSummary: {art['summary'][:800]}\nLink: {art['link']}"
        for i, art in enumerate(articles, 1)
    ])
    
    prompt = f"""You are analyzing {len(articles)} recent articles about pharmacy, medication management, Medicare programs, and healthcare AI for a Lead Clinical Pharmacist at Milu Health.

Milu Health Context:
- Milu uses an AI system called Merlin that integrates with EHR systems
- Focus areas: medication adherence, clinical decision support, cost-saving opportunities
- Target: Medicare patients, especially ACCESS program participants
- Services: Pharmacist-led care coordination, MTM, medication optimization

Please analyze these articles and create:

1. EXECUTIVE SUMMARY:
   - Start with a brief 2-3 sentence overview paragraph
   - Then provide 5-7 bullet points highlighting major themes, trends, and developments
   - Be specific and substantive - include data/findings where available
   - Focus on what pharmacy and healthcare AI leaders should be paying attention to

2. KEY TAKEAWAYS (5-7 bullet points):
   - Most important insights that would be actionable or strategically relevant
   - Focus on pharmacy practice, medication safety, AI validation, Medicare programs
   - Be specific and data-driven where possible

3. MILU STRATEGIC IMPLICATIONS:
   - Start with a brief 2-3 sentence context paragraph
   - Then provide 4-6 bullet points covering:
     * How these trends connect to Milu's work with Merlin, EHR integration, and medication adherence
     * Opportunities for Milu in Medicare ACCESS or other programs
     * Considerations for AI safety, validation, or clinical pharmacy protocols
     * Strategic positioning opportunities
   - Be actionable and specific to Milu's business

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
    html_parts.append('<h1 style="color: #0066cc; text-align: center;">Pharmacy & Medication Management AI Weekly Brief</h1>')
    html_parts.append(f'<p style="text-align: center; color: #666; font-size: 11pt;">Week ending {datetime.now().strftime("%B %d, %Y")}</p>')
    html_parts.append(f'<p style="text-align: center; color: #666; font-size: 10pt; font-style: italic;">Articles analyzed: {len(articles)} | Focus: Medication Management, Medicare ACCESS, Clinical Pharmacy AI</p>')
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
    receiver_email = "alexander.erika@gmail.com"
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'Pharmacy AI Weekly Brief - {datetime.now().strftime("%b %d, %Y")} ({num_articles} articles)'
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
    print("Pharmacy & Medication Management AI Monitor - Milu Health")
    print(f"Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    try:
        # Collect articles
        articles = collect_articles()
        
        if not articles:
            print("\n" + "=" * 80)
            print("No relevant articles found this week.")
            print("Focus areas: medication management, pharmacy AI, Medicare ACCESS")
            print("Try again later or check RSS feed availability.")
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
            print(f"To: alexander.erika@gmail.com")
            print(f"Articles analyzed: {len(articles)}")
            print(f"Run completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
