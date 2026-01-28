
# Mailbox

A terminal-based email client and Google Calendar integration app that connects to Gmail using OAuth 2.0 or App Password authentication.

## Features

- **Email Management**
  - Read emails in terminal with rich formatting
  - Compose and send emails via Gmail
  - Reply to and forward emails
  - Search emails
  - Save attachments
  - Mark emails as read/unread

- **Calendar Integration** (OAuth only)
  - View upcoming events
  - Today/Week/Month views
  - Search events
  - Open meeting links

- **Authentication**
  - OAuth 2.0 (recommended for full features)
  - App Password (simpler setup, email only)
  - Secure encrypted credential storage
  - Auto-reconnect on app restart

- **Data Sync**
  - Sync emails to local database
  - Sync calendar events to local database
  - Offline access to synced data

## Requirements

- Python 3.10+
- MySQL database
- Gmail account with either:
  - App Password (requires 2FA enabled)
  - OAuth 2.0 credentials from Google Cloud Console

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Mailbox
