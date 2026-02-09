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
           │           │ App Password │      │   OAuth 2.0  │
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
- Supports Database, Google, Email, and App configurations
- Environment variable loading via .env

#### **2. Authentication Layer** (/src/auth/)
- **Dual authentication methods:**
  - **OAuth 2.0** - Full access (email + calendar)
  - **App Password** - Email only, simpler setup
- **Encryption Module** - Secure credential storage using cryptography.fernet
- **Handlers:**
  - oauth.py - OAuth 2.0 flow with automatic token refresh
  - app_password.py - Gmail App Password authentication
- **Manager** - Unified interface for both auth methods

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

 **Email Management** - IMAP/SMTP (App Password) + Gmail API (OAuth)
 **Calendar Integration** - Google Calendar API (OAuth only)
 **Dual Authentication** - OAuth 2.0 and App Password support
 **Data Caching** - Local MySQL database for offline access
 **Encryption** - Encrypted credential storage using Fernet
 **Auto-login** - Persistent session restoration
 **Error Handling** - Exponential backoff retry logic
 **Terminal UI** - Rich-formatted interactive interface


### **External Services Integration**

- **Gmail API** - Email read/send for OAuth users
- **Google Calendar API** - Calendar access for OAuth users
- **IMAP/SMTP** - Standard email protocols for App Password users
- **OAuth 2.0 Flow** - Browser-based authentication

### **Project Structure Summary**

- **Scripts** - Database initialization, testing, and data clearing utilities
- **Credentials** - OAuth client secrets storage
- **Config** - Central settings and constants
- **Database** - Connection management, models, and repositories
- **Services** - Business logic for email and calendar
- **Auth** - Authentication and security
- **Sync** - Data synchronization layer
- **UI** - User interface and screens
