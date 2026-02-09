import smtplib
import imaplib

def gmail_bauth(email, password):
    
    print(f"\n Attempting SMTP connection...")
    try:
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        smtp.starttls()
        smtp.login(email, password)
        smtp.quit()
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f" SMTP Failed: {e}")
        print(f"   Error Code: {e.smtp_code}")
        print(f"   Error Message: {e.smtp_error.decode()}")
    except Exception as e:
        print(f" SMTP Error: {e}")
    
    print(f"\n Attempting IMAP connection..")
    try:
        imap = imaplib.IMAP4_SSL('imap.gmail.com')
        imap.login(email, password)
        imap.logout()
        return True
    except imaplib.IMAP4.error as e:
        print(f" IMAP Failed: {e}")
    except Exception as e:
        print(f" IMAP Error: {e}")
    
    return False

if __name__ == "__main__":
    email = input("Enter Gmail address: ")
    password = input("Enter password: ")
    
    result = gmail_bauth(email, password)
    
    if not result:
        print("\n" + "="*60)
        print("="*60)
