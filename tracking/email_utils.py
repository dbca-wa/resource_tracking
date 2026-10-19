import logging
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default
from email.utils import parseaddr
from imaplib import IMAP4_SSL
from ssl import SSLEOFError
from typing import Any, Literal

from django.conf import settings

LOGGER = logging.getLogger("tracking")


def normalise_imap_uid(value: str | bytes | int | None) -> str | None:
    """Return a valid IMAP UID string, or None when the value is unusable."""
    if value is None:
        return None

    if isinstance(value, bytes):
        value = value.decode("ascii", errors="ignore")
    elif isinstance(value, int):
        value = str(value)

    value = str(value).strip()
    if not value or value == "0":
        return None

    try:
        int(value)
    except ValueError:
        return None

    return value


def get_imap(mailbox: str = "INBOX") -> IMAP4_SSL | Literal[False]:
    """Instantiate a new IMAP object, login, and connect to a mailbox."""
    try:
        imap = IMAP4_SSL(settings.EMAIL_HOST)
        imap.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        imap.select(mailbox)
        return imap
    except (IMAP4_SSL.abort, IMAP4_SSL.error, SSLEOFError) as err:
        LOGGER.warning(f"Unable to log into mailbox: {err}")
        return False


def email_get_unread(imap: IMAP4_SSL) -> tuple[str, list] | tuple[Literal[False], Literal[False]]:
    """Returns (status, [list of UIDs]) of unread emails."""
    try:
        status, response = imap.uid("SEARCH", "UNSEEN", "UNFLAGGED")
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to search unread emails: {err}")
        return False, False

    if status != "OK":
        return status, response

    return status, response[0].split() if response and response[0] else []


def email_fetch(imap: IMAP4_SSL, uid: str) -> tuple[str, EmailMessage] | tuple[Literal[False], Literal[False]]:
    """Fetch a single email and return a tuple of status, EmailMessage."""
    uid_value = normalise_imap_uid(uid)
    if not uid_value:
        LOGGER.warning(f"Unable to fetch email: invalid message UID {uid!r}")
        return False, False

    try:
        status, msg_data = imap.uid("FETCH", uid_value, "(RFC822)")
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to fetch email: {err}")
        return False, False

    if status != "OK" or not msg_data or msg_data[0] is None:
        return False, False

    raw_email = msg_data[0][1]
    if not isinstance(raw_email, bytes):
        return False, False

    email_msg = message_from_bytes(s=raw_email, policy=default)

    return status, email_msg


def email_mark_read(imap: IMAP4_SSL, uid: str) -> tuple[str, list[Any]] | tuple[Literal[False], Literal[False]]:
    """Flag an email as 'Seen' based on passed-in UID."""
    uid_value = normalise_imap_uid(uid)
    if not uid_value:
        return False, False

    try:
        status, response = imap.uid("STORE", uid_value, "+FLAGS", r"(\Seen)")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to mark email read: {err}")
        return False, False


def email_mark_unread(imap: IMAP4_SSL, uid: str) -> tuple[str, list[Any]] | tuple[Literal[False], Literal[False]]:
    """Remove the 'Seen' flag from an email based on passed-in UID."""
    uid_value = normalise_imap_uid(uid)
    if not uid_value:
        return False, False

    try:
        status, response = imap.uid("STORE", uid_value, "-FLAGS", r"(\Seen)")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to mark email unread: {err}")
        return False, False


def email_mark_deleted(imap: IMAP4_SSL, uid: str) -> tuple[str, list[Any]] | tuple[Literal[False], Literal[False]]:
    """Flag an email for deletion."""
    uid_value = normalise_imap_uid(uid)
    if not uid_value:
        return False, False

    try:
        status, response = imap.uid("STORE", uid_value, "+FLAGS", r"(\Deleted)")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to delete email: {err}")
        return False, False


def email_flag(imap: IMAP4_SSL, uid: str) -> tuple[str, list[Any]] | tuple[Literal[False], Literal[False]]:
    """Flag an email as unprocessable."""
    uid_value = normalise_imap_uid(uid)
    if not uid_value:
        return False, False

    try:
        status, response = imap.uid("STORE", uid_value, "+FLAGS", r"(\Flagged)")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to flag email: {err}")
        return False, False


def get_message_text(msg: EmailMessage) -> str | None:
    """
    Return the body of the message, prefer 'text/plain', fall back to 'text/html'.
    Content is a string if found, else None.
    """
    if msg.is_multipart():
        body = msg.get_body(preferencelist=("plain", "html"))
        return body.get_content() if body else None

    content = msg.get_content()
    return content if isinstance(content, str) else None


def get_sender_email(message: EmailMessage) -> str | None:
    """Return the sender email from an email message, or None."""
    from_header = message.get("From")
    if not from_header:
        return None

    _, address = parseaddr(from_header)
    if not address:
        return None

    return address.lower()
