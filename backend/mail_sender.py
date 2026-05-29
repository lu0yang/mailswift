import base64

from exchangelib import (
    Account,
    Configuration,
    Credentials,
    DELEGATE,
    FileAttachment,
    Message,
    Mailbox,
    HTMLBody,
)

import logging

EWS_URL = "https://partner.outlook.cn/EWS/Exchange.asmx"

logger = logging.getLogger(__name__)


def _get_account(email_address: str, password: str) -> Account:
    creds = Credentials(username=email_address, password=password)

    # Try explicit URL first
    try:
        config = Configuration(service_endpoint=EWS_URL, credentials=creds)
        account = Account(
            primary_smtp_address=email_address,
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )
        account.inbox.total_count  # verify connectivity
        return account
    except Exception:
        logger.info("Explicit EWS URL failed, falling back to autodiscover")

    # Fall back to autodiscover
    return Account(
        primary_smtp_address=email_address,
        credentials=creds,
        autodiscover=True,
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
    attachments: list[dict] | None = None,
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
            text_body=body_plain,
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
        )

        if attachments:
            for att in attachments:
                content = base64.b64decode(att["content_base64"])
                m.attach(FileAttachment(name=att["filename"], content=content))

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
