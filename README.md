
# Mailbox

A terminal-based email client with Google Calendar integration. Connects to Gmail using OAuth 2.0 or App Password authentication.

## Features

### Email Management
- Read, compose, reply, and forward emails
- Search emails by keyword
- Save attachments
- Mark as read/unread
- Rich terminal formatting

### Calendar Integration (OAuth only)
- View upcoming events
- Today/Week/Month views
- Search events
- Open meeting links directly

### Authentication
- **OAuth 2.0** - Full features (email + calendar)
- **App Password** - Email only, simpler setup
- Encrypted credential storage
- Auto-login on restart

### Data Sync
- Local database caching
- Offline access to synced data
- Retry with exponential backoff

## Requirements

- Python 3.10+
- MySQL 8.0+
- Rich v13.7.0
- mysql-connector-python v8.3.0
- Cryptography v42.0.5
- Gmail account with:
  - 2FA enabled (for App Password), or
  - OAuth 2.0 credentials (for full features)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/FlameGreat-1/MailBox.git
cd Mailbox
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name

ENCRYPTION_KEY=your_generated_key
```

### 5. Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add the output to `ENCRYPTION_KEY` in `.env`.

### 6. Initialize Database

```bash
python scripts/init_db.py
```

### 7. Setup Authentication

#### Option A: App Password (Email Only)

1. Enable 2FA: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Select "Mail" → "Other" → Name it "Mailbox"
4. Copy the 16-character password

#### Option B: OAuth 2.0 (Full Features)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable APIs:
   - Gmail API
   - Google Calendar API
4. Configure OAuth consent screen:
   - User type: External
   - Add your email as test user
5. Create OAuth 2.0 credentials:
   - Application type: Desktop app
   - Download JSON
6. Save as `credentials/client_secret.json`

## Usage

### Run Application

```bash
python src/main.py
```

### First Time Setup

1. Choose authentication method
2. Enter credentials
3. Wait for initial sync
4. Navigate using keyboard shortcuts

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1-9` | Select item |
| `b` | Back |
| `q` | Quit |
| `r` | Refresh/Reply |
| `c` | Compose |
| `f` | Forward |
| `s` | Search |
| `u` | Mark unread |
| `n` | Next page |
| `p` | Previous page |

### Main Menu

| Key | Screen |
|-----|--------|
| `1` | Inbox |
| `2` | Compose |
| `3` | Calendar |
| `4` | Search |
| `5` | Sync |
| `6` | Settings |

## Project Structure

```
Mailbox/
├── src/
│   ├── auth/           # Authentication handlers
│   ├── config/         # Configuration management
│   ├── database/       # Database models & repositories
│   ├── services/       # Email & calendar services
│   ├── sync/           # Data synchronization
│   └── ui/             # Terminal user interface
├── scripts/            # Utility scripts
├── credentials/        # OAuth credentials (gitignored)
├── requirements.txt    # Python dependencies
└── .env.example        # Environment template
```

## Scripts

```bash
# Initialize database
python scripts/init_db.py

# Clear all data (for switching accounts)
python scripts/clear_data.py

# Test database connection
python scripts/test_connection.py
```

