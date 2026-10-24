import os
import re
from dotenv import load_dotenv
from imap_tools import MailBox, AND

load_dotenv()

KEEP_WORDS = ["receipt", "order", "invoice", "payment", "confirmation",
              "statement", "password", "login code", "verification"]

KEEP_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in KEEP_WORDS) + r")s?\b", re.IGNORECASE
)


def _login():
    return MailBox("imap.gmail.com").login(
        os.getenv("GMAIL_ADDRESS"), os.getenv("GMAIL_APP_PASSWORD")
    )


def _is_protected(subject):
    return bool(KEEP_PATTERN.search(subject or ""))


def _matches(msg, text, mode):
    if mode == "subject":
        return text in (msg.subject or "").lower()
    name = msg.from_values.name if msg.from_values else ""
    return text in (msg.from_ or "").lower() or text in (name or "").lower()


def search_emails(text: str, mode: str = "sender"):
    """Find emails by sender (name or address) or by subject line."""
    text = str(text).strip().lower()
    criteria = AND(subject=text) if mode == "subject" else AND(from_=text)
    with _login() as mailbox:
        msgs = list(mailbox.fetch(criteria, headers_only=True, bulk=True))
    msgs = [m for m in msgs if _matches(m, text, mode)]
    trashable = [m for m in msgs if not _is_protected(m.subject)]
    protected = [m for m in msgs if _is_protected(m.subject)]
    return {
        "count": len(trashable),
        "protected": len(protected),
        "uids": [m.uid for m in trashable],
        "samples": [f"{m.from_} | {m.subject}" for m in trashable],
        "protected_samples": [m.subject for m in protected],
        "protected_uids": [m.uid for m in protected],
    }


def trash_uids(uids, batch: int = 50):
    """Move exactly these emails to Trash, a few at a time."""
    moved = 0
    with _login() as mailbox:
        for i in range(0, len(uids), batch):
            chunk = uids[i:i + batch]
            mailbox.move(chunk, "[Gmail]/Trash")
            moved += len(chunk)
    return moved