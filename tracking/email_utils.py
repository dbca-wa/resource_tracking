from django.conf import settings
import email
from imaplib import IMAP4, IMAP4_SSL
import logging

LOGGER = logging.getLogger("tracking")


def get_imap(mailbox="INBOX"):
    """Instantiate a new IMAP object, login, and connect to a mailbox."""
    imap = IMAP4_SSL(settings.EMAIL_HOST)
    try:
        imap.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        imap.select(mailbox)
        return imap
    except IMAP4.error:
        LOGGER.error("Unable to log into mailbox")
        return None


def email_get_unread(imap, from_email_address):
    """Returns (status, list of UIDs) of unread emails from a sending email address."""
    search = '(UNSEEN UNFLAGGED FROM "{}")'.format(from_email_address)
    status, response = imap.search(None, search)
    if status != "OK":
        return status, response
    # Return status and list of unread email UIDs.
    return status, response[0].split()


def email_fetch(imap, uid):
    """Returns (status, message) for an email by UID.
    Email is returned as an email.Message class object.
    """
    message = None
    status, response = imap.fetch(str(uid), "(BODY.PEEK[])")

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
    status, response = imap.store(str(uid), "+FLAGS", r"\Seen")
    return status, response


def email_mark_unread(imap, uid):
    """Remove the 'Seen' flag from an email based on passed-in UID."""
    status, response = imap.store(str(uid), "-FLAGS", r"\Seen")
    return status, response


def email_delete(imap, uid):
    """Flag an email for deletion."""
    status, response = imap.store(str(uid), "+FLAGS", r"\Deleted")
    return status, response


def email_flag(imap, uid):
    """Flag an email as unprocessable."""
    status, response = imap.store(str(uid), "+FLAGS", r"\Flagged")
    return status, response
