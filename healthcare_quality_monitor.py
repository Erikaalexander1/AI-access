"""
Healthcare Quality & Policy Weekly Monitor
For: Erika Alexander - Lead Clinical Pharmacist, Carina Health Network
Role: VBC Clinical Pharmacist focused on FQHC quality, Stars/HEDIS, risk adjustment, adherence
Sends weekly email to alexander.erika@gmail.com every Sunday
"""

import feedparser
import anthropic
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import os
import re

# ── Credentials (from GitHub Secrets) ─────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
RECIPIENT_EMAIL = "alexander.erika@gmail.com"
SENDER_EMAIL = "alexander.erika@gmail.com"

# ── RSS Feeds ──────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    "https://www.cms.gov/newsroom/rss-feeds",
    "https://www.fiercehealthcare.com/rss.xml",
    "https://www.modernhealthcare.com/rss",
    "https://www.healthcaredive.com/feeds/news/",
    "https://kffhealthnews.org/feed/",
    "https://www.healthaffairs.org/do/10.1377/hp.rss/full/",
    "https://www.ama-assn.org/rss/news.xml",
    "https://www.healthleadersmedia.com/rss.xml",
    "https://www.ajmc.com/rss.xml",
]

# ── Keywords covering all 9 focus areas ───────────────────────────────────────
KEYWORDS = [
    # 1. FQHC
    "FQHC", "federally qualified health center", "community health center",
    "340B", "HRSA", "look-alike", "sliding fee", "UDS", "prospective payment",
    # 2. Stars / HEDIS
    "star ratings", "star rating", "HEDIS", "quality measures", "CAHPS",
    "PDC", "proportion of days covered", "quality bonus", "cut points",
    "NCQA", "SUPD", "statin", "medication adherence",
    # 3. Population Health
    "population health", "care management", "care coordination", "SDOH",
    "social determinants", "health equity", "care gaps", "gap closure",
    "chronic disease", "transitional care", "readmission", "preventive care",
    # 4. VBC
    "value-based care", "VBC", "value based", "ACO", "accountable care",
    "MSSP", "Medicare Shared Savings", "shared savings", "APM",
    "alternative payment model", "bundled payment", "total cost of care",
    # 5 & 9. Risk Adjustment / CMS-HCC / APMs
    "risk adjustment", "HCC", "hierarchical condition category",
    "CMS-HCC", "RAF score", "risk score", "V28", "RADV",
    "diagnosis capture", "ACO REACH", "CMMI", "capitation", "two-sided risk",
    # 6 & 8. MA Quality
    "Medicare Advantage", "MA plan", "MA contract", "MA quality",
    "Part C", "SNP", "special needs plan", "dual eligible", "D-SNP",
    "quality bonus payment", "MA stars",
    # 7. Adherence / MTM
    "MTM", "medication therapy management", "CMR", "comprehensive medication review",
    "Part D", "adherence program", "pharmacy quality", "PQA",
    # CIN
    "CIN", "clinically integrated network", "clinical integration",
]

CARINA_FQHCS = [
    "Clinica Family Health", "Denver Health", "High Plains Community Health",
    "Mountain Family Health", "Peak Vista", "Pueblo Community Health",
    "Salud Family Health", "Sunrise Community Health", "Valley-Wide Health",
    "STRIDE Community Health", "River Valley Health", "Northwest Colorado Health",
    "Uncompahgre Medical", "MarillacHealth", "Summit Community Care",
    "Tepeyac Community Health", "Axis Health System", "Sheridan Health",
    "Denver Indian Health", "Inner City Health"
]


def is_relevant(title, summary):
    text = (title + " " + summary).lower()
    has_health_context = any(t in text for t in [
        "medicare", "medicaid", "cms", "healthcare", "health plan",
        "quality", "provider", "physician", "hospital", "clinic", "pharmacy"
    ])
    if not has_health_context:
        return False
    return any(k.lower() in text for k in KEYWORDS)


def collect_articles():
    print("Collecting articles...")
    articles = []
    seen = set()

    for i, url in enumerate(RSS_FEEDS, 1):
        try:
            print(f"  Feed {i}/{len(RSS_FEEDS)}...")
            feed = feedparser.parse(url)
            for entry in feed.entries[:30]:
                title = entry.get('title', '').strip()
                summary = entry.get('summary', entry.get('description', ''))
                link = entry.get('link', '')

                if not title or title in seen:
                    continue
                if not is_relevant(title, summary):
                    continue

                pub = entry.get('published_parsed', entry.get('updated_parsed'))
                if pub:
                    age_days = (datetime.now() - datetime(*pub[:6])).days
                    if age_days > 21:
                        continue

                seen.add(title)
                articles.append({
                    'title': title,
                    'link': link,
                    'summary': summary[:1500],
                    'published': entry.get('published', entry.get('updated', 'Unknown date')),
                    'source': feed.feed.get('title', 'Unknown source')
                })
        except Exception as e:
            print(f"  Error on feed {i}: {e}")

    articles.sort(key=lambda x: x.get('published', ''), reverse=True)
    print(f"Collected {len(articles)} relevant articles")
    return articles


def generate_main_brief(articles):
    print("Generating main brief...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    article_text = "\n\n".join([
        f"[{i}] {a['title']}\nSource: {a['source']} | Date: {a['published']}\nSummary: {a['summary'][:600]}\nLink: {a['link']}"
        for i, a in enumerate(articles, 1)
    ])

    prompt = f"""You are writing a weekly briefing email for Erika Alexander, a Lead Clinical Pharmacist with 20 years of experience who is NEW to value-based care (VBC) at Carina Health Network — a CIN (Clinically Integrated Network) supporting 20 FQHCs (Federally Qualified Health Centers) across Colorado through MSSP (Medicare Shared Savings Program) and Medicare Advantage contracts.

Erika's goal: Make a measurable ROI impact in her new role by staying ahead of policy changes and translating them into pharmacy-driven revenue and quality improvements.

Carina's 20 FQHC partners:
1. Clinica Family Health | 2. Denver Health (CHCs) | 3. High Plains Community Health Center
4. Mountain Family Health Centers | 5. Peak Vista Community Health Centers
6. Pueblo Community Health Center | 7. Salud Family Health | 8. Sunrise Community Health
9. Valley-Wide Health Systems | 10. STRIDE Community Health Center
11. River Valley Health Centers | 12. Northwest Colorado Health
13. Uncompahgre Medical Center | 14. MarillacHealth | 15. Summit Community Care Clinic
16. Tepeyac Community Health Center | 17. Axis Health System | 18. Sheridan Health Services
19. Denver Indian Health and Family Services | 20. Inner City Health Center

TODAY'S DATE: {datetime.now().strftime('%B %d, %Y')}

ARTICLES TO ANALYZE:
{article_text}

INSTRUCTIONS:
1. Use web search to verify key claims against official CMS documentation
2. Spell out ALL acronyms on first use, e.g. "HEDIS (Healthcare Effectiveness Data and Information Set)"
3. For each section give a SPECIFIC, TACTICAL action Erika can take — not vague advice
4. Name specific FQHC partners when relevant
5. Include measure specs (denominator, numerator, exclusions) for clinical measures
6. Link to official CMS/NCQA sources

Write the brief using EXACTLY these section headers (include all 9 even if no news — give a standing best practice instead):

## WEEKLY HEALTHCARE BRIEF — {datetime.now().strftime('%B %d, %Y')}

## 1. FQHC (Federally Qualified Health Centers) Updates

## 2. CMS Star Ratings & HEDIS Measures

## 3. Population Health Initiatives

## 4. Value-Based Care (VBC) Program Optimization

## 5. Risk Adjustment — CIN/MSSP/MA/VBC Contracts

## 6. Supporting MA Contracts Through Stars/HEDIS Performance

## 7. Medication Adherence Programs Aligned with Stars/HEDIS

## 8. MA Quality Program Requirements

## 9. CMS-HCC Risk Adjustment & Alternative Payment Models (APMs)

## KEY TAKEAWAYS THIS WEEK

For sections 1-9, use this sub-structure:
**What's New:** [news/update]
**Official Source:** [Name — URL]
**Your Action at Carina:** [specific steps Erika can take]
**FQHC Spotlight:** [which of the 20 FQHCs are most impacted and why]
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}]
        )

        text_blocks = [b.text for b in message.content if hasattr(b, 'text') and b.text.strip()]
        full_text = " ".join(text_blocks)

        # Strip preamble before the first real header
        match = re.search(r'## WEEKLY HEALTHCARE BRIEF', full_text)
        if match:
            full_text = full_text[match.start():]

        print(f"Main brief generated ({len(full_text)} chars)")
        return full_text

    except Exception as e:
        print(f"Error generating main brief: {e}")
        return f"Error: {str(e)}"


def generate_plain_english(main_brief):
    print("Generating plain English summary...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Below is a detailed healthcare policy brief.

Rewrite it as a SHORT "Plain English Summary" — like texting a smart friend who knows NOTHING about healthcare, Medicare, or pharmacy jargon.

STRICT RULES:
- Exactly 5-6 bullet points. No more.
- Each bullet: **Bold headline (3-5 words)** then 2-3 plain sentences.
- Zero acronyms unless you explain them in plain words immediately
- Use real-world comparisons (money, sports, everyday life)
- End each bullet with "This means you should: [one specific action]"

Brief to simplify:
{main_brief[:4000]}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        result = message.content[0].text.strip()
        print(f"Plain English generated ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"Error generating plain English: {e}")
        return ""


def md_to_html(text):
    """Convert markdown text to HTML with styled formatting"""
    html = []
    lines = text.split('\n')
    in_ul = False

    for line in lines:
        line = line.rstrip()

        # Bold markdown inline
        def bold(s):
            return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', s)

        # H1 (# )
        if line.startswith('# ') and not line.startswith('## '):
            if in_ul: html.append('</ul>'); in_ul = False
            html.append(f'<h1 style="color:#0055a5;font-size:20pt;margin-top:10px;">{bold(line[2:])}</h1>')
            continue

        # H2 (## )
        if line.startswith('## '):
            if in_ul: html.append('</ul>'); in_ul = False
            heading = line[3:].strip()
            heading_plain = re.sub(r'\*\*(.*?)\*\*', r'\1', heading)
            if 'WEEKLY HEALTHCARE' in heading_plain.upper():
                html.append(f'<h1 style="color:#0055a5;font-size:20pt;text-align:center;margin:10px 0;">{heading_plain}</h1>')
            elif any(x in heading_plain.upper() for x in ['KEY TAKEAWAY', 'PLAIN ENGLISH']):
                html.append(f'<h2 style="color:#cc6600;font-size:15pt;margin-top:28px;border-bottom:2px solid #cc6600;padding-bottom:5px;">{heading_plain}</h2>')
            else:
                html.append(f'<h2 style="color:#0055a5;font-size:14pt;margin-top:26px;border-bottom:1px solid #c5d8f5;padding-bottom:5px;">{heading_plain}</h2>')
            continue

        # Bullet points — only single - or • (not **)
        if re.match(r'^[-•]\s', line) or re.match(r'^\*\s', line):
            if not in_ul:
                html.append('<ul style="margin:6px 0;padding-left:22px;line-height:1.75;">')
                in_ul = True
            content = re.sub(r'^[-•\*]\s+', '', line)
            html.append(f'<li style="margin-bottom:5px;">{bold(content)}</li>')
            continue

        if in_ul and line.strip():
            html.append('</ul>')
            in_ul = False

        if not line.strip():
            continue

        line_html = bold(line)

        # Styled callout lines
        if '**Official Source:**' in line or line.strip().startswith('**Official Source'):
            html.append(f'<p style="margin:8px 0;padding:6px 12px;background:#eef4ff;border-left:3px solid #0055a5;font-size:10pt;">{line_html}</p>')
        elif '**Your Action at Carina:**' in line or 'Your Action at Carina:' in line:
            html.append(f'<p style="margin:8px 0;padding:8px 14px;background:#efffef;border-left:4px solid #228822;font-size:11pt;">{line_html}</p>')
        elif '**FQHC Spotlight:**' in line or 'FQHC Spotlight:' in line:
            html.append(f'<p style="margin:8px 0;padding:6px 12px;background:#fff8e6;border-left:3px solid #cc8800;font-size:10pt;">{line_html}</p>')
        elif '**What\'s New:**' in line or "What's New:" in line:
            html.append(f'<p style="margin:10px 0 4px;font-weight:bold;color:#333;">{line_html}</p>')
        else:
            html.append(f'<p style="margin:5px 0;line-height:1.75;">{line_html}</p>')

    if in_ul:
        html.append('</ul>')

    return '\n'.join(html)


def build_email_html(main_brief, plain_english, articles):
    parts = []

    parts.append('<div style="font-family:Arial,sans-serif;font-size:11pt;max-width:820px;margin:0 auto;">')

    # Header banner
    parts.append(f'''
<div style="background:linear-gradient(135deg,#0055a5,#0077cc);color:white;padding:22px 20px;text-align:center;border-radius:8px 8px 0 0;">
  <div style="font-size:28pt;margin-bottom:4px;">💊</div>
  <h1 style="margin:0;font-size:20pt;font-weight:bold;">Healthcare Quality & Policy Brief</h1>
  <p style="margin:8px 0 0;font-size:10pt;opacity:0.9;">
    Week ending {datetime.now().strftime("%B %d, %Y")} &nbsp;·&nbsp;
    {len(articles)} articles analyzed &nbsp;·&nbsp;
    ✓ CMS-Verified
  </p>
  <p style="margin:4px 0 0;font-size:9pt;opacity:0.75;">
    For: Erika Alexander &nbsp;·&nbsp; Carina Health Network
  </p>
</div>
<div style="background:#deeaf7;padding:7px 16px;font-size:9pt;color:#444;text-align:center;border-bottom:2px solid #0055a5;">
  FQHC &nbsp;·&nbsp; Stars/HEDIS &nbsp;·&nbsp; Population Health &nbsp;·&nbsp; VBC &nbsp;·&nbsp; Risk Adjustment &nbsp;·&nbsp; MA Quality &nbsp;·&nbsp; Adherence &nbsp;·&nbsp; CMS-HCC &nbsp;·&nbsp; APMs
</div>
''')

    # Main content
    parts.append('<div style="padding:10px 24px;">')
    parts.append(md_to_html(main_brief))
    parts.append('</div>')

    # Plain English box
    print(f"Building email — plain English length: {len(plain_english)}")
    if plain_english and len(plain_english.strip()) > 20:
        parts.append('''
<div style="margin:20px 20px 10px;padding:22px;background:#fff8ee;border:2px solid #ff9900;border-radius:10px;">
  <h2 style="color:#cc6600;font-size:17pt;margin:0 0 4px;">🧠 Plain English — What This Actually Means</h2>
  <p style="color:#999;font-style:italic;font-size:9pt;margin:0 0 14px;">No jargon. No acronyms. Just what matters and what to do.</p>
''')
        for line in plain_english.split('\n'):
            line = line.strip()
            if not line:
                continue
            if re.match(r'^[-•*]\s', line) or re.match(r'^\d+\.\s', line):
                content = re.sub(r'^[-•*\d.]+\s*', '', line)
                content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
                parts.append(f'<p style="margin:10px 0;line-height:1.85;padding:8px 12px;background:white;border-left:4px solid #ff9900;border-radius:4px;">• {content}</p>')
            else:
                line_h = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
                parts.append(f'<p style="line-height:1.7;margin:6px 0;">{line_h}</p>')
        parts.append('</div>')
    else:
        parts.append('<p style="color:red;padding:10px 20px;">⚠️ Plain English section could not be generated this week.</p>')

    # Article references
    parts.append('''
<div style="margin:20px;padding:16px;background:#f7f9fc;border-radius:8px;border:1px solid #dde6f0;">
  <h2 style="color:#0055a5;font-size:13pt;margin-top:0;">📚 Articles Analyzed This Week</h2>
''')
    for i, a in enumerate(articles, 1):
        link_display = a['link'][:75] + '...' if len(a['link']) > 75 else a['link']
        parts.append(f'''
  <div style="margin-bottom:10px;padding:9px 12px;background:white;border-left:3px solid #0055a5;border-radius:3px;">
    <p style="margin:0;font-weight:bold;font-size:10pt;">{i}. {a["title"]}</p>
    <p style="margin:2px 0;font-size:9pt;color:#777;">{a["source"]} &nbsp;|&nbsp; {a["published"]}</p>
    <p style="margin:2px 0;font-size:9pt;"><a href="{a["link"]}" style="color:#0055a5;">{link_display}</a></p>
  </div>
''')
    parts.append('</div>')

    # Footer
    parts.append(f'''
<div style="text-align:center;padding:12px;font-size:9pt;color:#aaa;border-top:1px solid #eee;">
  Auto-generated {datetime.now().strftime("%Y-%m-%d %H:%M")} &nbsp;|&nbsp; Carina Health Network Quality Monitor
</div>
</div>
''')

    return '\n'.join(parts)


def send_email(html_content, num_articles):
    print("Sending email...")
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'💊 Healthcare Quality Brief — {datetime.now().strftime("%b %d, %Y")} ({num_articles} articles)'
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD.replace(' ', ''))
        server.send_message(msg)
        server.quit()
        print(f"✓ Email sent to {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"✗ Email failed: {e}")
        return False


def main():
    print("=" * 70)
    print("Healthcare Quality & Policy Weekly Monitor — Carina Health Network")
    print(f"Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    articles = collect_articles()

    if not articles:
        print("No relevant articles found this week.")
        return

    main_brief = generate_main_brief(articles)
    plain_english = generate_plain_english(main_brief)

    print(f"\nPlain English check: {len(plain_english)} chars")

    html = build_email_html(main_brief, plain_english, articles)
    success = send_email(html, len(articles))

    if success:
        print()
        print("=" * 70)
        print("SUCCESS!")
        print(f"  To: {RECIPIENT_EMAIL}")
        print(f"  Articles: {len(articles)}")
        print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)


if __name__ == "__main__":
    main()
