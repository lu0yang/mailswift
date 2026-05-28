import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def verify_smtp_connection(
    smtp_host: str,
    smtp_port: int,
    email_address: str,
    password: str,
) -> tuple[bool, str]:
    """Verify SMTP credentials by connecting + authenticating, without sending any email."""
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(email_address, password)
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP 认证失败，请检查邮箱和密码是否正确"
    except smtplib.SMTPConnectError:
        return False, "无法连接到 SMTP 服务器，请检查网络"
    except Exception as e:
        return False, str(e)


def send_email(
    smtp_host: str,
    smtp_port: int,
    email_address: str,
    password: str,
    recipient: str,
    subject: str,
    body_html: str,
    body_plain: str,
    cc: str = "",
) -> tuple[bool, str, bytes]:
    """Send an email via SMTP with HTML + plain text multipart.

    Returns (success, error_message, raw_message_bytes).
    The raw bytes can be used for IMAP APPEND archiving.
    """
    msg = MIMEMultipart("alternative")
    msg["From"] = email_address
    msg["To"] = recipient
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(body_plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    all_recipients = [recipient]
    if cc:
        all_recipients += [addr.strip() for addr in cc.split(",") if addr.strip()]

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(email_address, password)
            server.sendmail(email_address, all_recipients, msg.as_string())
        return True, "", msg.as_bytes()
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP 认证失败，请检查邮箱和密码是否正确", b""
    except smtplib.SMTPConnectError:
        return False, "无法连接到 SMTP 服务器，请检查网络", b""
    except smtplib.SMTPRecipientsRefused:
        return False, "收件人地址被拒收", b""
    except Exception as e:
        return False, str(e), b""
