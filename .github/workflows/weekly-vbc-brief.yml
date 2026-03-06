# ============================================================================
# Weekly Value-Based Care Brief for Carina Health Network
# ============================================================================
# Schedule: Every Friday at 7:00 AM MT (1:00 PM UTC)
# Also supports manual dispatch for testing
# ============================================================================

name: Weekly VBC Brief

on:
  schedule:
    # Every Friday at 7:00 AM Mountain Time (UTC-7 = 1:00 PM UTC)
    - cron: '0 13 * * 5'
  workflow_dispatch:
    inputs:
      test_mode:
        description: 'Run in test mode (shorter output)'
        required: false
        default: 'false'
        type: choice
        options:
          - 'false'
          - 'true'

jobs:
  send-weekly-brief:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Generate and send weekly brief
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          SENDER_EMAIL: ${{ secrets.SENDER_EMAIL }}
          RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
          TEST_MODE: ${{ github.event.inputs.test_mode || 'false' }}
        run: |
          python scripts/weekly_vbc_email.py

      - name: Log completion
        if: success()
        run: echo "✅ Weekly VBC Brief sent successfully at $(date -u)"

      - name: Log failure
        if: failure()
        run: echo "❌ Weekly VBC Brief FAILED at $(date -u)"
