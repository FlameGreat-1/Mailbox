           A terminal-based email client with Google Calendar integration, built in Python.

What This App Does:

Mailbox is a terminal email client that connects to Gmail (via OAuth 2.0 or App Password) and Zoho Mail. It runs entirely in the terminal using the Rich library for styled output — think colorful panels, progress bars, and formatted text instead of a browser or desktop GUI. It also integrates Google Calendar (OAuth only) and caches everything locally in a MySQL database for offline access.   
              
              
                    ┌─────────────┐
                    │   config    │
                    │  settings   │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    ┌──────────┐    ┌────────────┐    ┌──────────┐
    │ database │    │ encryption │    │ ui/styles│
    │connection│    └──────┬─────┘    │  theme   │
    └────┬─────┘           │          └────┬─────┘
         │                 │               │
         ▼                 ▼               ▼
    ┌──────────┐    ┌────────────┐    ┌──────────┐
    │  models  │    │   auth     │    │   ui     │
    └────┬─────┘    │  handlers  │    │components│
         │          └──────┬─────┘    └────┬─────┘
         ▼                 │               │
    ┌──────────┐           ▼               │
    │  repos   │    ┌────────────┐         │
    │(cred,    │◄───│   auth     │         │
    │email,cal)│    │  manager   │         │
    └────┬─────┘    └──────┬─────┘         │
         │                 │               │
         │    ┌────────────┴────────────┐  │
         │    │                         │  │
         │    ▼                         ▼  │
         │ ┌─────────┐           ┌─────────┐
         │ │ email   │           │calendar │
         │ │providers│           │providers│
         │ └────┬────┘           └────┬────┘
         │      │                     │
         │      ▼                     ▼
         │ ┌─────────┐           ┌─────────┐
         │ │ email   │           │calendar │
         │ │ client  │           │ client  │
         │ └────┬────┘           └────┬────┘
         │      │                     │
         │      └──────────┬──────────┘
         │                 │
         ▼                 ▼
    ┌─────────────────────────────┐
    │       sync handlers         │
    │    (email.py, calendar.py)  │
    └──────────────┬──────────────┘
                   │
                   ▼
    ┌─────────────────────────────┐
    │       sync manager          │
    └──────────────┬──────────────┘
                   │
                   ▼
    ┌─────────────────────────────┐◄─────────────┐
    │       ui/screens            │              │
    │  (login, menu, inbox, cal)  │              │
    └──────────────┬──────────────┘              │
                   │                             │
                   ▼                             │
    ┌─────────────────────────────┐              │
    │         ui/app.py           │──────────────┘
    └──────────────┬──────────────┘
                   │
                   ▼
    ┌─────────────────────────────┐
    │         main.py             │
    └─────────────────────────────┘





┌─────────────────────────────────────────────────────────────┐
│                      APP STARTUP                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Check credentials DB  │
              └────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
   ┌───────────────┐              ┌───────────────┐
   │ Credentials   │              │ No credentials│
   │ exist         │              │ found         │
   └───────────────┘              └───────────────┘
           │                               │
           ▼                               ▼
   ┌───────────────┐              ┌───────────────┐
   │ Decrypt &     │              │ Prompt: Choose│
   │ auto-auth     │              │ auth method   │
   └───────────────┘              └───────────────┘
           │                               │
           │                    ┌──────────┴──────────┐
           │                    ▼                     ▼
           │           ┌──────────────┐      ┌──────────────┐
           │           │App Pwd / Zoho│      │   OAuth 2.0  │
           │           │ flow         │      │   flow       │
           │           └──────────────┘      └──────────────┘
           │                    │                     │
           │                    └──────────┬──────────┘
           │                               │
           │                               ▼
           │                    ┌───────────────────┐
           │                    │ Store encrypted   │
           │                    │ credentials in DB │
           │                    └───────────────────┘
           │                               │
           └───────────────┬───────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   MAIN MENU            │
              │   1. Inbox             │
              │   2. Compose           │
              │   3. Calendar          │
              │   4. Settings          │
              │   5. Logout            │
              └────────────────────────┘




### **Core Technologies & Frameworks**

**Python Stack:**
- **Python 3.10+** - Primary language
- **Rich** (v13.7.0) - Terminal UI library for styled, formatted output

**Database:**
- **MySQL 8.0+** - Relational database for storing emails, calendar events, and credentials
- **mysql-connector-python** (v8.3.0) - MySQL database driver with connection pooling

**Authentication & Security:**
- **Cryptography** (v42.0.5) - Encryption library for storing credentials securely
- **python-dotenv** (v1.0.1) - Environment configuration management
- **Google Auth** (v2.28.1) - Google authentication framework
- **google-auth-oauthlib** (v1.2.0) - OAuth 2.0 implementation for Google
- **google-auth-httplib2** (v0.2.0) - HTTP transport for Google Auth
- **google-api-python-client** (v2.118.0) - Google APIs client

**Date/Time:**
- **python-dateutil** (v2.9.0) - Advanced datetime parsing and manipulation


### **Architecture Overview**

The app follows a **layered architecture** with clear separation of concerns:

#### **1. Configuration Layer** (/src/config/)
- Centralized settings management with dataclass-based configs
- Supports Database, Google, Email, Zoho, and App configurations
- Environment variable loading via .env

#### **2. Authentication Layer** (/src/auth/)
- **Multiple authentication methods:**
  - **OAuth 2.0** - Full access (email + calendar) with automatic browser flow
  - **App Password** - Email only, via IMAP/SMTP
  - **Zoho Mail** - Email only, via IMAP/SMTP
- **Encryption Module** - Secure credential storage using cryptography.fernet
- **Handlers:**
  - oauth.py - OAuth 2.0 flow with local callback server
  - app_password.py - Gmail App Password authentication
  - zoho_mail.py - Zoho Mail authentication
- **Manager** - Unified interface for all auth methods

#### **3. Database Layer** (/src/database/)
- **Connection Manager** - Singleton pattern with connection pooling
- **Models** - ORM-like dataclasses for Email, CalendarEvent, Credential, AuthType
- **Repositories** - Data access layer:
  - CredentialsRepository - Store/retrieve encrypted credentials
  - EmailsRepository - Email caching and retrieval
  - CalendarRepository - Calendar event storage

#### **4. Services Layer** (/src/services/)
**Email Service:**
- **Providers:**
  - IMAPProvider - IMAP for reading emails (App Password only)
  - SMTPProvider - SMTP for sending emails (App Password only)
  - GmailAPIProvider - Gmail API for OAuth users
- **Client** - High-level email operations with retry logic (exponential backoff)
- **Parser** - Email parsing and attachment handling

**Calendar Service:**
- **GoogleCalendarProvider** - Google Calendar API integration (OAuth only)
- **Client** - Calendar operations, event filtering, multiple view modes

#### **5. Sync Layer** (/src/sync/)
- **Manager** - Orchestrates email and calendar sync with threading
- **Handlers:**
  - EmailSyncHandler - Fetch, store, and sync emails
  - CalendarSyncHandler - Fetch, store, and sync calendar events
- **Result tracking** - Detailed sync status and error reporting

#### **6. UI Layer** (/src/ui/)
**Screens:**
- LoginScreen - Authentication selection and flow
- MainMenuScreen - Main navigation
- SettingsScreen - User preferences
- InboxListScreen - Email list with search
- EmailViewScreen - Full email display with reply/forward
- ComposeScreen - Email composition
- CalendarListScreen - Calendar events display
- EventViewScreen - Event details

**Components:**
- Header & Footer - UI frame elements
- TextInput & PasswordInput - Input components
- EmailList & CalendarList - Data display components

**Styling:**
- Theme - Rich console theme with color scheme
- Symbols - Unicode symbols for UI decoration



### **Key Features Implementation**

 **Email Management** - IMAP/SMTP (App Password / Zoho) + Gmail API (OAuth)
 **Calendar Integration** - Google Calendar API (OAuth only)
 **Multi-Provider Authentication** - OAuth 2.0, App Password, and Zoho support
 **Data Caching** - Local MySQL database for offline access
 **Encryption** - Encrypted credential storage using Fernet
 **Auto-login** - Persistent session restoration
 **Error Handling** - Exponential backoff retry logic
 **Terminal UI** - Rich-formatted interactive interface


### **External Services Integration**

- **Gmail API** - Email read/send for OAuth users
- **Google Calendar API** - Calendar access for OAuth users
- **IMAP/SMTP** - Standard email protocols for App Password & Zoho users
- **OAuth 2.0 Flow** - Automatic browser-based authentication with local callback

### **Project Structure Summary**

- **Scripts** - Database initialization, testing, and data clearing utilities
- **Credentials** - OAuth client secrets storage
- **Config** - Central settings and constants
- **Database** - Connection management, models, and repositories
- **Services** - Business logic for email and calendar
- **Auth** - Authentication and security
- **Sync** - Data synchronization layer
- **UI** - User interface and screens


---

## End-to-End Flow

Here's exactly what happens from the moment you run `python src/main.py`:

### 1. Startup
- `main.py` calls `run_app()` → creates `MailboxApp` → calls `app.run()`
- `run()` sets up file-based logging (`mailbox.log`), shows a startup progress bar (config → DB connection test → services init)

### 2. Login
- Always shows login screen (no auto-login)
- User picks: **"Sign in with Google"** or **"Zoho Mail"**
- **Google OAuth path**: starts a threaded HTTP server on `localhost:8080`, opens browser, waits up to 5 minutes for the user to authorize, captures the authorization code from the redirect, exchanges it for tokens, builds Gmail + Calendar API services, encrypts and stores everything in MySQL
- **Zoho path**: prompts for email + password, connects via IMAP, encrypts and stores credentials

### 3. Initial Sync
- After successful login, progress bar shows: "Fetching emails..." → "Fetching calendar events..."
- Fetches latest 20 emails from provider (IMAP or Gmail API) and stores in MySQL
- If OAuth, also fetches 30 days of calendar events
- Shows summary: "X new emails, Y new events"

### 4. Main Menu (Dashboard)
- Displays: unread count, upcoming event count, 3 most recent emails, today's events
- 6 options: Inbox, Compose, Calendar, Search, Sync, Settings

### 5. Using the App
- **Inbox**: Paginated email list from MySQL → select email → view full content (fetches body from provider if not cached) → reply/forward
- **Compose**: To/CC/BCC/Subject/Body inputs → sends via SMTP or Gmail API
- **Search**: Searches local DB first, falls back to provider search
- **Calendar**: Today/Week/Month views of events → view details → open meeting links
- **Sync**: Manual sync with progress bar — re-fetches from providers and updates MySQL
- **Settings**: Preferences and logout (with option to clear stored credentials)

### 6. Shutdown
- `Ctrl+C` or `q` → `_cleanup()` logs out the session (clears in-memory state) but **keeps encrypted credentials in MySQL** so next launch can restore the session

---

## Key Design Decisions

1. **Singleton pattern everywhere** — ensures exactly one DB pool, one auth session, one encryption key, one sync manager. Prevents resource leaks and inconsistent state.

2. **Exponential backoff retries** — every external call (IMAP, SMTP, Gmail API, Calendar API) retries up to 3 times with delays of 1s, 2s, 4s. Handles transient network issues without crashing.

3. **Provider abstraction** — `EmailClient` doesn't care whether it's talking to IMAP or Gmail API. The `AuthManager.active_method` enum routes to the correct provider. This means adding a new email provider (e.g., Outlook) only requires a new handler + provider, no changes to the client.

4. **Encrypt-at-rest** — credentials never exist as plaintext in MySQL. Even the access tokens are individually encrypted. The encryption key lives only in `.env` (or memory).

5. **Local OAuth callback server** — instead of asking users to copy-paste authorization codes, the app spins up a temporary HTTP server, captures the redirect automatically, and shows a styled HTML page confirming success/failure. The server validates the `state` parameter to prevent CSRF attacks.

6. **Screen state machine** — the UI uses a simple `_current_screen` string pattern instead of a framework. Each handler returns `(next_screen, data)`, making navigation explicit and debuggable.

7. **DB-first reads** — email list views always read from MySQL (fast, offline-capable). Full email bodies are fetched from the provider only when actually opened, then cached.
