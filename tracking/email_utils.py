import email
import logging
from imaplib import IMAP4_SSL

from django.conf import settings

LOGGER = logging.getLogger("tracking")


def get_imap(mailbox="INBOX"):
    """Instantiate a new IMAP object, login, and connect to a mailbox."""
    try:
        imap = IMAP4_SSL(settings.EMAIL_HOST, timeout=10)
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


def email_fetch(imap, uid):
    """Returns (status, message) for an email by UID.
    Email is returned as an email.Message class object.
    """
    message = None
    try:
        status, response = imap.fetch(str(uid), "(BODY.PEEK[])")
    except (IMAP4_SSL.abort, IMAP4_SSL.error) as err:
        LOGGER.warning(f"Unable to fetch email: {err}")
        return None

    if status != "OK":
        return status, response

    for i in response:
        if isinstance(i, tuple):
            s = i[1]
            if isinstance(s, bytes):
                s = s.decode("utf-8")
            message = email.message_from_string(s)

    return status, message


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
