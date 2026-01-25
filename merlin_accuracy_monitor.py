"""
Merlin Accuracy Monitor for Milu Health
Tracks AI system accuracy metrics and flags anomalies
Reads from Google Sheet, emails weekly summary
Uses service account authentication
"""

import os
import anthropic
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Get credentials from environment
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

# Google Sheets configuration
SHEET_ID = '1PGYgCJf-_m8OnrXT3V2aX_X3DTjxqeahieNmqWtl6ok'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def get_google_credentials():
    """Authenticate with Google Sheets using service account"""
    print("Authenticating with Google Sheets...")
    
    # Parse service account credentials from environment
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    
    # Create credentials
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )
    
    return credentials


def read_sheet_data():
    """Read data from Google Sheet"""
    print("Reading Merlin accuracy data from Google Sheet...")
    
    creds = get_google_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    # Read all data
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range='A:H'  # All columns from A to H
    ).execute()
    
    values = result.get('values', [])
    
    if not values or len(values) < 2:
        return None
    
    # Parse data
    headers = values[0]
    data_rows = values[1:]
    
    # Convert to list of dicts
    records = []
    for row in data_rows:
        if len(row) >= 7:  # Must have at least 7 columns
            try:
                record = {
                    'date': row[0],
                    'ascvd_correct': int(row[1]) if row[1] else 0,
                    'ascvd_incorrect': int(row[2]) if row[2] else 0,
                    'drug_interactions_detected': int(row[3]) if row[3] else 0,
                    'drug_interactions_missed': int(row[4]) if row[4] else 0,
                    'false_positives': int(row[5]) if row[5] else 0,
                    'allergy_failures': int(row[6]) if row[6] else 0,
                    'notes': row[7] if len(row) > 7 else ''
                }
                records.append(record)
            except (ValueError, IndexError) as e:
                print(f"Skipping invalid row: {row} - {e}")
                continue
    
    print(f"Found {len(records)} weeks of data")
    return records


def analyze_metrics(records):
    """Use Claude to analyze metrics and identify trends/anomalies"""
    print("Analyzing metrics with Claude API...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Format data for Claude
    data_summary = "\n".join([
        f"Week of {r['date']}:\n"
        f"  ASCVD: {r['ascvd_correct']} correct, {r['ascvd_incorrect']} incorrect "
        f"({round(r['ascvd_correct']/(r['ascvd_correct']+r['ascvd_incorrect'])*100, 1) if (r['ascvd_correct']+r['ascvd_incorrect']) > 0 else 0}% accuracy)\n"
        f"  Drug Interactions: {r['drug_interactions_detected']} detected, {r['drug_interactions_missed']} missed\n"
        f"  False Positives: {r['false_positives']}\n"
        f"  Allergy Failures: {r['allergy_failures']}\n"
        f"  Notes: {r['notes']}\n"
        for r in records
    ])
    
    prompt = f"""You are analyzing {len(records)} weeks of accuracy data for Merlin, Milu Health's AI medication management system.

Merlin integrates with EHR systems to provide clinical decision support for medication adherence, drug interactions, and safety alerts.

Data:
{data_summary}

Please analyze this data and create:

1. EXECUTIVE SUMMARY (2-3 sentences):
   - Overall performance assessment
   - Most significant trend or concern

2. KEY METRICS & TRENDS (5-7 bullet points):
   - ASCVD calculation accuracy trends (improving/declining/stable?)
   - Drug interaction detection performance
   - False positive rate trends
   - Allergy detection failures
   - Week-over-week changes
   - Any concerning patterns

3. ANOMALIES & ALERTS (bullet points):
   - Flag any metrics that dropped significantly
   - Identify any sudden spikes in errors
   - Note any patterns that suggest systematic issues
   - If no anomalies, state "No significant anomalies detected"

4. RECOMMENDATIONS (3-5 bullet points):
   - Specific actions to address issues
   - Areas that need investigation
   - Process improvements
   - If performance is good, suggest areas for continued monitoring

Be specific with percentages and changes. Flag anything concerning immediately."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
        
    except Exception as e:
        print(f"Error analyzing metrics: {e}")
        return f"Error analyzing metrics: {str(e)}"


def create_html_email(analysis, num_weeks):
    """Create formatted HTML email"""
    print("Creating email...")
    
    html_parts = ['<div style="font-family: Arial, sans-serif; font-size: 12pt; max-width: 800px;">']
    
    # Header
    html_parts.append('<h1 style="color: #cc0000; text-align: center;">⚠️ Merlin Accuracy Weekly Report</h1>')
    html_parts.append(f'<p style="text-align: center; color: #666; font-size: 11pt;">Week ending {datetime.now().strftime("%B %d, %Y")}</p>')
    html_parts.append(f'<p style="text-align: center; color: #666; font-size: 10pt; font-style: italic;">Analyzing {num_weeks} weeks of data</p>')
    html_parts.append('<hr style="border: 1px solid #ddd; margin: 20px 0;">')
    
    # Process analysis
    lines = analysis.split('\n')
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Section headers
        if (line.startswith('##') or 'EXECUTIVE SUMMARY' in line or 'KEY METRICS' in line or 
            'ANOMALIES' in line or 'RECOMMENDATIONS' in line):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            section = line.replace('##', '').replace('#', '').strip()
            
            # Color code sections
            color = '#cc0000' if 'ANOMALIES' in section else '#0066cc'
            html_parts.append(f'<h2 style="color: {color}; margin-top: 20px;">{section}</h2>')
            continue
        
        # Bullet points
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            if not in_list:
                html_parts.append('<ul style="line-height: 1.6;">')
                in_list = True
            text = line[1:].strip().replace('**', '<strong>').replace('**', '</strong>')
            
            # Highlight concerning items
            if any(word in text.lower() for word in ['drop', 'decline', 'concern', 'alert', 'spike', 'failure']):
                text = f'<span style="color: #cc0000;">⚠️ {text}</span>'
            
            html_parts.append(f'<li>{text}</li>')
        else:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(f'<p style="line-height: 1.6;">{line}</p>')
    
    if in_list:
        html_parts.append('</ul>')
    
    # Footer
    html_parts.append('<hr style="border: 1px solid #ddd; margin: 30px 0;">')
    html_parts.append(f'<p style="font-size: 10pt; color: #666;">Data source: <a href="https://docs.google.com/spreadsheets/d/{SHEET_ID}" style="color: #0066cc;">Merlin Accuracy Tracking Google Sheet</a></p>')
    html_parts.append('</div>')
    
    return '\n'.join(html_parts)


def send_email(html_content, num_weeks):
    """Send email via Gmail"""
    print("Sending email...")
    
    sender_email = "erika@miluhealth.com"
    receiver_email = "erika@miluhealth.com"
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'⚠️ Merlin Accuracy Report - {datetime.now().strftime("%b %d, %Y")} ({num_weeks} weeks)'
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
    print("Merlin Accuracy Monitor - Milu Health")
    print(f"Run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    try:
        # Read data from Google Sheet
        records = read_sheet_data()
        
        if not records:
            print("No data found in Google Sheet")
            print("Make sure you have data in rows 2+ with the correct format")
            return
        
        # Analyze metrics
        analysis = analyze_metrics(records)
        
        # Create email
        html_content = create_html_email(analysis, len(records))
        
        # Send email
        success = send_email(html_content, len(records))
        
        if success:
            print()
            print("=" * 80)
            print("SUCCESS! Merlin accuracy report emailed")
            print(f"To: erika@miluhealth.com")
            print(f"Weeks analyzed: {len(records)}")
            print(f"Run completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
