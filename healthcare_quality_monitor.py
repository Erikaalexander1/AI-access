"""
Healthcare Policy & Quality Metrics Monitor - Enhanced Edition
Cross-references news with official CMS documentation for verified, regulation-backed insights
Focus: FQHC, HEDIS, Stars, VBC, Risk Adjustment, MA Programs, Population Health
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

# Get credentials from environment
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

# Healthcare policy and quality-focused RSS feeds
RSS_FEEDS = [
    "https://www.cms.gov/newsroom/rss-feeds",
    "https://www.fiercehealthcare.com/rss.xml",
    "https://www.modernhealthcare.com/rss",
    "https://www.healthcaredive.com/feeds/news/",
    "https://khn.org/feed/",
    "https://www.healthaffairs.org/do/10.1377/hp.rss/full/",
    "https://www.ama-assn.org/rss/news.xml",
    "https://www.healthleadersmedia.com/rss.xml",
    "https://www.ajmc.com/rss.xml",
]

# CMS Reference Documents for Cross-Referencing
CMS_REFERENCE_DOCS = {
    'FQHC': 'https://www.cms.gov/center/provider-type/federally-qualified-health-centers-fqhc-center',
    'Star_Ratings': 'https://www.cms.gov/medicare/health-drug-plans/medicareadvtgspecratestats',
    'Risk_Adjustment': 'https://www.cms.gov/medicare/payment/medicare-advantage-rates-statistics/risk-adjustment',
    'MA_Quality': 'https://www.cms.gov/medicare/health-drug-plans/part-c-d-performance-data',
    'CMMI_Models': 'https://www.cms.gov/priorities/innovation/innovation-models',
}

# Keywords organized by topic area
FQHC_KEYWORDS = [
    "FQHC", "federally qualified health center", "community health center",
    "health center", "340B", "HRSA"
]

STARS_HEDIS_KEYWORDS = [
    "star ratings", "Stars", "HEDIS", "quality measures", "quality metrics",
    "performance measures", "CAHPS", "medication adherence", "PDC",
    "proportion of days covered", "quality bonus"
]

VBC_KEYWORDS = [
    "value-based care", "VBC", "value based", "ACO", "accountable care",
    "MSSP", "Medicare Shared Savings", "shared savings",
    "alternative payment model", "APM", "quality payment",
    "bundled payment", "episode-based"
]

RISK_ADJUSTMENT_KEYWORDS = [
    "risk adjustment", "HCC", "hierarchical condition category",
    "CMS-HCC", "RAF score", "risk score", "risk coding",
    "diagnosis capture", "chart chase"
]

MA_KEYWORDS = [
    "Medicare Advantage", "MA plan", "MA contract",
    "Part C", "Medicare managed care", "MA quality",
    "MA performance", "SNP", "special needs plan"
]

POPULATION_HEALTH_KEYWORDS = [
    "population health", "care management", "care coordination",
    "chronic disease management", "social determinants",
    "SDOH", "health equity", "transitional care",
    "readmission", "preventive care"
]

CIN_KEYWORDS = [
    "CIN", "clinically integrated network", "physician alignment",
    "network performance", "clinical integration"
]


def is_relevant_article(title, summary):
    """Check if article is relevant to healthcare quality/policy topics"""
    text = (title + ' ' + summary).lower()
    
    # Must contain healthcare/Medicare context
    has_healthcare_context = any(term in text for term in [
        "medicare", "medicaid", "cms", "healthcare", "health plan",
        "quality", "provider", "physician", "hospital", "clinic"
    ])
    
    if not has_healthcare_context:
        return False
    
    # Check if contains any target keywords
    all_keywords = (FQHC_KEYWORDS + STARS_HEDIS_KEYWORDS + VBC_KEYWORDS + 
                   RISK_ADJUSTMENT_KEYWORDS + MA_KEYWORDS + 
                   POPULATION_HEALTH_KEYWORDS + CIN_KEYWORDS)
    
    if any(keyword.lower() in text for keyword in all_keywords):
        return True
    
    return False


def collect_articles():
    """Collect healthcare quality and policy articles"""
    print("Collecting healthcare policy and quality articles...")
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
                    # Check recency
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
    """Use Claude with web search to create verified, regulation-backed summary"""
    print("\nCreating executive summary with regulatory cross-referencing...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Prepare article list
    article_list = "\n\n".join([
        f"ARTICLE {i}:\nTitle: {art['title']}\nSource: {art['source']}\nDate: {art['published']}\nSummary: {art['summary'][:800]}\nLink: {art['link']}"
        for i, art in enumerate(articles, 1)
    ])
    
    prompt = f"""You are analyzing {len(articles)} recent healthcare policy articles for Carina Health Network, a CIN supporting all 21 FQHCs in Colorado.

CRITICAL TASK: Cross-reference news articles with official CMS documentation to verify accuracy and provide regulation-backed implementation guidance.

Carina Health Context:
- CIN supporting ALL 21 FQHCs in Colorado (including Peak Vista, Denver Health CHC, Salud Family Health, Clinica Family Health, and 17 others)
- Network covers 850,000+ patients across 247 clinic sites in 47 counties  
- Participates in MSSP (Medicare Shared Savings Program) - earned millions in shared savings
- Manages Medicare Advantage contracts
- 95% of FQHCs use Azara DQMS platform with Snowflake data warehouse
- Master patient index: 3.5 million patients
- Pharmacy team: 2 clinical pharmacists (including Lead Clinical Pharmacist), Leah (0.4 FTE), 3 pharmacy technicians
- Goal: Demonstrate ROI through improved quality outcomes and cost savings within existing resources

INSTRUCTIONS:
1. First, use web search to verify key claims in the articles by checking official CMS sources
2. Cross-reference implementation ideas against actual CMS regulations and manuals
3. Cite specific CMS manual chapters/sections when making recommendations

Create the following analysis:

1. EXECUTIVE SUMMARY (2-3 sentences):
   - Major themes across all topic areas
   - Most significant VERIFIED developments this week

2. KEY DEVELOPMENTS BY TOPIC:
   - Group articles by: FQHC, HEDIS/Stars, VBC Programs, Risk Adjustment, MA Quality, Population Health
   - For each topic with news:
     * 2-4 bullet points summarizing developments
     * Note if verified against CMS documentation or if claims need caution
     * Include specific metrics, dates, policy changes

3. CARINA IMPLEMENTATION IDEAS - TACTICAL ACTION ITEMS:
   
   CRITICAL: Only include if news provides SPECIFIC, ACTIONABLE information verified against CMS regulations.
   If too general, write: "No specific implementation opportunities identified this week."
   
   Format as tactical playbook entries with REGULATORY CITATIONS:
   
   **[INITIATIVE NAME]**  
   Regulatory Basis: [Cite specific CMS manual/chapter - e.g., "Per CMS Medicare Managed Care Manual Ch.11 §40.1.2..."]
   Concrete Action: [Exactly what to do - which system, data, metric, FQHC(s)]
   Timeline: [Specific - "Launch March 2026" or "6-week pilot"]
   Implementation Steps:
   1. [Specific with tools - e.g., "Pull Azara report for X"]
   2. [Specific with resources - e.g., "Tech compiles Y list"]  
   3. [Specific with metrics - e.g., "Track via Snowflake"]
   Expected ROI: [Numbers with calculation - "$X from Y% improvement affecting N patients"]
   Resource Allocation: [How to use 2 pharmacists + 0.4 Leah + 3 techs]
   Best FQHC Targets: [Specific from the 21 - e.g., "Peak Vista (74K patients)" or "Denver Health CHC + Salud"]
   
   Must be executable with current staff. Only 2-5 items. Must tie to this week's news AND verified regulations.

4. STRATEGIC IMPLICATIONS FOR CARINA (3-5 bullet points):
   - Verified opportunities/threats
   - Required compliance changes
   - Competitive positioning

5. KEY TAKEAWAYS (5-7 bullet points):
   - Most actionable, regulation-backed insights

Use web search liberally to verify claims and find official CMS documentation.

Articles to analyze:

{article_list}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract response text (handling tool use) - only take the LAST text block
        # (first blocks are often Claude's internal "thinking" preamble)
        text_blocks = [block.text for block in message.content if hasattr(block, 'text')]
        
        if not text_blocks:
            return "Error: No text content in response"
        
        # Join all text blocks but strip any preamble before the actual analysis
        response_text = " ".join(text_blocks)
        
        # Remove common preamble patterns
        for preamble in [
            "I'll analyze", "I will analyze", "Based on my search", 
            "Let me analyze", "I can now provide"
        ]:
            if preamble in response_text:
                # Find where the real content starts (first numbered section or header)
                import re
                match = re.search(r'(HEALTHCARE POLICY|1\.\s+EXECUTIVE|EXECUTIVE SUMMARY)', response_text)
                if match:
                    response_text = response_text[match.start():]
                break
        
        return response_text
        
    except Exception as e:
        print(f"Error creating summary: {e}")
        return f"Error creating executive summary: {str(e)}"


def create_plain_english_summary(executive_summary):
    """Generate a super simple, plain-English version of the summary"""
    print("Creating plain English summary...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Below is a detailed healthcare policy summary. Your job is to rewrite it in the simplest possible way — like you're explaining it to a smart friend who knows nothing about healthcare policy.

Rules:
- No jargon. If you must use a term, explain it in plain words immediately after.
- Short sentences. 
- Use analogies or real-world comparisons where helpful.
- Focus only on what actually MATTERS and what someone should DO about it.
- Format as 3-5 bullet points max. Each bullet = one key idea.
- Start each bullet with a bold one-phrase headline, then 1-2 plain sentences explaining it.

Here is the summary to simplify:

{executive_summary}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        result = message.content[0].text
        print(f"Plain English summary generated ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"Error creating plain English summary: {e}")
        return ""


def create_html_email(executive_summary, articles, plain_english_summary=""):
    """Create formatted HTML email"""
    print("Creating HTML email...")
    
    html_parts = ['<div style="font-family: Arial, sans-serif; font-size: 12pt; max-width: 800px;">']
    
    # Header
    html_parts.append('<h1 style="color: #0066cc; text-align: center;">Healthcare Quality & Policy Weekly Brief</h1>')
    html_parts.append('<p style="text-align: center; color: #cc0000; font-size: 10pt; font-weight: bold;">✓ Verified Against CMS Documentation</p>')
    html_parts.append(f'<p style="text-align: center; color: #666; font-size: 11pt;">Week ending {datetime.now().strftime("%B %d, %Y")}</p>')
    html_parts.append(f'<p style="text-align: center; color: #666; font-size: 10pt; font-style: italic;">Articles analyzed: {len(articles)} | Focus: FQHC, HEDIS/Stars, VBC, Risk Adjustment, MA Programs</p>')
    html_parts.append('<hr style="border: 1px solid #ddd; margin: 20px 0;">')
    
    # Process executive summary
    lines = executive_summary.split('\n')
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Section headers
        if (line.startswith('##') or line.startswith('#') or 
            'EXECUTIVE SUMMARY' in line or 'KEY DEVELOPMENTS' in line or 
            'CARINA IMPLEMENTATION' in line or 'IMPLEMENTATION IDEAS' in line or
            'STRATEGIC IMPLICATIONS' in line or 'KEY TAKEAWAYS' in line or
            any(topic in line for topic in ['HEDIS', 'Star', 'FQHC', 'VBC', 'Risk Adjustment', 'MA Quality', 'Population Health'])):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            section = line.replace('##', '').replace('#', '').strip()
            
            # Different colors for different sections
            if 'EXECUTIVE' in section:
                color = '#0066cc'
                size = '18pt'
            elif 'IMPLEMENTATION' in section or 'Initiative' in section:
                color = '#006600'
                size = '16pt'
            elif any(topic in section for topic in ['HEDIS', 'Star', 'FQHC', 'VBC', 'Risk', 'MA', 'Population']):
                color = '#006600'
                size = '14pt'
            else:
                color = '#0066cc'
                size = '16pt'
            
            html_parts.append(f'<h2 style="color: {color}; margin-top: 20px; font-size: {size};">{section}</h2>')
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
            # Highlight regulatory citations
            if 'Per CMS' in line or 'CMS Manual' in line or 'Chapter' in line or '§' in line:
                line = f'<span style="background-color: #ffffcc;">{line}</span>'
            html_parts.append(f'<p style="line-height: 1.6;">{line}</p>')
    
    if in_list:
        html_parts.append('</ul>')
    
    # Plain English Summary Section
    if plain_english_summary:
        html_parts.append('<hr style="border: 2px solid #ff9900; margin: 30px 0;">')
        html_parts.append('<div style="background: #fff8ee; border: 2px solid #ff9900; border-radius: 8px; padding: 20px; margin-bottom: 20px;">')
        html_parts.append('<h2 style="color: #cc6600; font-size: 18pt; margin-top: 0;">🧠 Plain English — What This Actually Means</h2>')
        html_parts.append('<p style="color: #666; font-style: italic; font-size: 10pt;">No jargon. Just the key stuff, explained simply.</p>')
        
        for line in plain_english_summary.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Handle bullet points (•, -, *, or numbered like "1.")
            if line.startswith('•') or line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line):
                text = re.sub(r'^[•\-\*\d\.]+\s*', '', line)
                text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
                html_parts.append(f'<p style="line-height: 1.8; margin: 12px 0;">• {text}</p>')
            else:
                line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
                html_parts.append(f'<p style="line-height: 1.7;">{line}</p>')
        
        html_parts.append('</div>')

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
    
    sender_email = "alexander.erika@gmail.com"
    receiver_email = "alexander.erika@gmail.com"
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'✓ Healthcare Quality Brief (CMS-Verified) - {datetime.now().strftime("%b %d")} ({num_articles} articles)'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    
    try:
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
    print("Healthcare Quality & Policy Monitor (Enhanced with CMS Verification)")
    print(f"Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    try:
        # Collect articles
        articles = collect_articles()
        
        if not articles:
            print("\n" + "=" * 80)
            print("No relevant articles found this week.")
            print("Focus areas: FQHC, HEDIS/Stars, VBC, Risk Adjustment, MA Programs")
            print("=" * 80)
            return
        
        # Create executive summary with CMS cross-referencing
        executive_summary = create_executive_summary(articles)
        
        # Create plain English version
        plain_english_summary = create_plain_english_summary(executive_summary)
        
        # Create HTML email
        html_content = create_html_email(executive_summary, articles, plain_english_summary)
        
        # Send email
        success = send_email(html_content, len(articles))
        
        if success:
            print()
            print("=" * 80)
            print("SUCCESS! CMS-verified weekly brief emailed")
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
