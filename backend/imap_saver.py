import imaplib
import logging
from email.message import Message

logger = logging.getLogger(__name__)

SENT_FOLDER_CANDIDATES = ["Sent Items", "Sent", "已发送邮件", "已发送"]


def save_to_sent_items(
    imap_host: str,
    imap_port: int,
    email_address: str,
    password: str,
    msg_bytes: bytes,
) -> tuple[bool, str]:
    """Append a sent email to the Sent Items folder via IMAP.

    Returns (success, error_message).
    """
    try:
        with imaplib.IMAP4_SSL(imap_host, imap_port, timeout=30) as conn:
            conn.login(email_address, password)

            sent_folder = _find_sent_folder(conn)
            if sent_folder is None:
                return False, "找不到已发送邮件文件夹"

            result = conn.append(sent_folder, "\\Seen", None, msg_bytes)
            if result[0] != "OK":
                return False, f"IMAP APPEND 失败: {result}"

            logger.info("Email archived to %s", sent_folder)
            return True, ""

    except imaplib.IMAP4.error as e:
        return False, f"IMAP 认证失败: {e}"
    except OSError as e:
        return False, f"无法连接到 IMAP 服务器: {e}"
    except Exception as e:
        return False, str(e)


def _find_sent_folder(conn: imaplib.IMAP4_SSL) -> str | None:
    """Try to find the Sent Items folder among common names."""
    try:
        status, folders = conn.list()
        if status != "OK":
            return None

        folder_names = set()
        for line in folders:
            if isinstance(line, bytes):
                parts = line.decode(errors="replace").split(' "/" ')
                if len(parts) > 1:
                    name = parts[-1].strip('" ')
                    folder_names.add(name)

        for candidate in SENT_FOLDER_CANDIDATES:
            if candidate in folder_names:
                return candidate

            lower = candidate.lower()
            for name in folder_names:
                if name.lower() == lower:
                    return name

        return None
    except Exception:
        return None
