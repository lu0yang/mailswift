"""
Test if EWS (Exchange Web Services) is available for your account.
Run this on your Windows machine:
    pip install exchangelib
    python test_ews.py
"""
from exchangelib import (
    Account, Configuration, Credentials, DELEGATE, FaultTolerance,
)

EWS_URL = "https://partner.outlook.cn/EWS/Exchange.asmx"
SMTP_HOST = "mail.21vianet.com"

email = input("邮箱地址: ").strip()
password = input("密码: ").strip()

print("\n--- Testing credentials ---")
creds = Credentials(username=email, password=password)

# 1. Try EWS
print(f"\n--- Test 1: EWS ({EWS_URL}) ---")
try:
    config = Configuration(
        server=EWS_URL,
        credentials=creds,
    )
    account = Account(
        primary_smtp_address=email,
        config=config,
        autodiscover=False,
        access_type=DELEGATE,
        default_timezone="Asia/Shanghai",
    )
    # Try to access inbox to verify connectivity
    count = account.inbox.total_count
    print(f"EWS OK — inbox has {count} items")

    # Try to access sent folder
    sent_count = account.sent.total_count
    print(f"Sent Items has {sent_count} items")

    ews_ok = True
except Exception as e:
    print(f"EWS FAILED: {e}")
    ews_ok = False

# 2. Try alternative EWS URLs
if not ews_ok:
    alt_urls = [
        "https://partner.outlook.cn/EWS/Exchange.asmx",
        "https://outlook.office365.com/EWS/Exchange.asmx",
        "https://mail.21vianet.com/EWS/Exchange.asmx",
    ]
    for url in alt_urls:
        print(f"\n--- Test: {url} ---")
        try:
            config = Configuration(server=url, credentials=creds)
            account = Account(
                primary_smtp_address=email,
                config=config,
                autodiscover=False,
                access_type=DELEGATE,
            )
            count = account.inbox.total_count
            print(f"OK — inbox has {count} items")
            ews_ok = True
            break
        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")

# 3. Try autodiscover
if not ews_ok:
    print("\n--- Test: Autodiscover ---")
    try:
        account = Account(
            primary_smtp_address=email,
            credentials=creds,
            autodiscover=True,
            access_type=DELEGATE,
        )
        count = account.inbox.total_count
        print(f"Autodiscover OK — inbox has {count} items")
        ews_ok = True
    except Exception as e:
        print(f"Autodiscover FAILED: {e}")

# Summary
print("\n" + "=" * 50)
if ews_ok:
    print("RESULT: EWS works! We can switch to exchangelib.")
else:
    print("RESULT: EWS is NOT available. Stick with smtplib.")
print("=" * 50)
