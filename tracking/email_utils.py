import logging
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default
from imaplib import IMAP4_SSL
from typing import List, Literal, Optional, Tuple

from django.conf import settings

LOGGER = logging.getLogger("tracking")


def get_imap(mailbox: str = "INBOX") -> IMAP4_SSL | Literal[False]:
    """Instantiate a new IMAP object, login, and connect to a mailbox."""
    try:
        imap = IMAP4_SSL(settings.EMAIL_HOST)
        imap.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        imap.select(mailbox)
        return imap
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to log into mailbox: {err}")
        return False


def email_get_unread(imap: IMAP4_SSL, from_email_address: str) -> Tuple[str, List] | Literal[False]:
    """Returns (status, [list of UIDs]) of unread emails from a sending email address."""
    search = '(UNSEEN UNFLAGGED FROM "{}")'.format(from_email_address)
    try:
        status, response = imap.search(None, search)
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to search unread emails: {err}")
        return False

    if status != "OK":
        return status, response
    # Return status and list of unread email UIDs.
    return status, response[0].split()


def email_fetch(imap, uid: str) -> Tuple[str, EmailMessage] | Literal[False]:
    """Fetch a single email and return a tuple of status, EmailMessage"""
    try:
        status, msg_data = imap.fetch(uid, "(RFC822)")
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to fetch email: {err}")
        return False

    if status != "OK":
        return False

    raw_email = msg_data[0][1]
    msg = message_from_bytes(raw_email, policy=default)

    return status, msg


def email_mark_read(imap, uid) -> Tuple[Optional[str], Optional[str]] | Literal[False]:
    """Flag an email as 'Seen' based on passed-in UID."""
    try:
        status, response = imap.store(str(uid), "+FLAGS", r"\Seen")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to mark email read: {err}")
        return False


def email_mark_unread(imap, uid) -> Tuple[Optional[str], Optional[str]] | Literal[False]:
    """Remove the 'Seen' flag from an email based on passed-in UID."""
    try:
        status, response = imap.store(str(uid), "-FLAGS", r"\Seen")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to mark email unread: {err}")
        return False


def email_delete(imap, uid) -> Tuple[Optional[str], Optional[str]] | Literal[False]:
    """Flag an email for deletion."""
    try:
        status, response = imap.store(str(uid), "+FLAGS", r"\Deleted")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to delete email: {err}")
        return False


def email_flag(imap, uid) -> Tuple[Optional[str], Optional[str]] | Literal[False]:
    """Flag an email as unprocessable."""
    try:
        status, response = imap.store(str(uid), "+FLAGS", r"\Flagged")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to flag email: {err}")
        return False


def email_get_body(msg: EmailMessage) -> Tuple[Optional[str], Optional[str]]:
    """
    Return the body of the message, prefer 'text/plain', fall back to 'text/html'.
    Returns (content, content_type). Content is a string if found, else None.
    """
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is None:
        return None, None

    content = body.get_content()
    ctype = body.get_content_type()
    return content, ctype
