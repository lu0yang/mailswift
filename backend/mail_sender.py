from exchangelib import (
    Account,
    Configuration,
    Credentials,
    DELEGATE,
    Message,
    Mailbox,
    HTMLBody,
)

EWS_URL = "https://partner.outlook.cn/EWS/Exchange.asmx"


def _get_account(email_address: str, password: str) -> Account:
    creds = Credentials(username=email_address, password=password)
    config = Configuration(server=EWS_URL, credentials=creds)
    return Account(
        primary_smtp_address=email_address,
        config=config,
        autodiscover=False,
        access_type=DELEGATE,
    )


def send_email(
    email_address: str,
    password: str,
    recipient: str,
    subject: str,
    body_html: str,
    body_plain: str,
    cc: str = "",
) -> tuple[bool, str]:
    """Send an email via Exchange EWS. The message is automatically saved to Sent Items."""
    try:
        account = _get_account(email_address, password)

        to_recipients = [Mailbox(email_address=recipient)]
        cc_recipients = None
        if cc:
            cc_recipients = [
                Mailbox(email_address=addr.strip())
                for addr in cc.split(",")
                if addr.strip()
            ]

        m = Message(
            account=account,
            subject=subject,
            body=HTMLBody(body_html),
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
        )
        m.send()
        return True, ""
    except Exception as e:
        return False, str(e)


def verify_connection(email_address: str, password: str) -> tuple[bool, str]:
    """Verify credentials by connecting to Exchange EWS."""
    try:
        account = _get_account(email_address, password)
        account.inbox.total_count
        return True, ""
    except Exception as e:
        return False, str(e)
