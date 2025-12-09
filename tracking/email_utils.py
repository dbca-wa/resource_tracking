import email
import logging
from email.policy import default
from imaplib import IMAP4_SSL

from django.conf import settings

LOGGER = logging.getLogger("tracking")


def get_imap(mailbox="INBOX"):
    """Instantiate a new IMAP object, login, and connect to a mailbox."""
    try:
        imap = IMAP4_SSL(settings.EMAIL_HOST)
        imap.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        imap.select(mailbox)
        return imap
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to log into mailbox: {err}")
        return None


def email_get_unread(imap, from_email_address):
    """Returns (status, [list of UIDs]) of unread emails from a sending email address."""
    search = '(UNSEEN UNFLAGGED FROM "{}")'.format(from_email_address)
    try:
        status, response = imap.search(None, search)
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to search unread emails: {err}")
        return None

    if status != "OK":
        return status, response
    # Return status and list of unread email UIDs.
    return status, response[0].split()


def email_fetch(imap, uid: str):
    try:
        status, msg_data = imap.fetch(uid, "(RFC822)")
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to fetch email: {err}")
        return None

    if status != "OK":
        return False

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email, policy=default)

    return status, msg


def email_mark_read(imap, uid):
    """Flag an email as 'Seen' based on passed-in UID."""
    try:
        status, response = imap.store(str(uid), "+FLAGS", r"\Seen")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to mark email read: {err}")
        return None


def email_mark_unread(imap, uid):
    """Remove the 'Seen' flag from an email based on passed-in UID."""
    try:
        status, response = imap.store(str(uid), "-FLAGS", r"\Seen")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to mark email unread: {err}")
        return None


def email_delete(imap, uid):
    """Flag an email for deletion."""
    try:
        status, response = imap.store(str(uid), "+FLAGS", r"\Deleted")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to delete email: {err}")
        return None


def email_flag(imap, uid):
    """Flag an email as unprocessable."""
    try:
        status, response = imap.store(str(uid), "+FLAGS", r"\Flagged")
        return status, response
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to flag email: {err}")
        return None
