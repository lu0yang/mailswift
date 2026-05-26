import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(
    smtp_host: str,
    smtp_port: int,
    email_address: str,
    password: str,
    recipient: str,
    subject: str,
    body: str,
) -> tuple[bool, str]:
    """Send an email via SMTP. Returns (success, error_message)."""
    msg = MIMEMultipart()
    msg["From"] = email_address
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(email_address, password)
            server.sendmail(email_address, recipient, msg.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP 认证失败，请检查邮箱和密码是否正确"
    except smtplib.SMTPConnectError:
        return False, "无法连接到 SMTP 服务器，请检查网络"
    except smtplib.SMTPRecipientsRefused:
        return False, "收件人地址被拒收"
    except Exception as e:
        return False, str(e)
