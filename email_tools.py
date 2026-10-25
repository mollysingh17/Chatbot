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


def search_emails(text, mode="sender", before=None, after=None,
                  count=None, order="oldest"):
    """Find emails by sender or subject, optionally filtered by date and count."""
    text = str(text).strip().lower()
    kwargs = {"subject": text} if mode == "subject" else {"from_": text}
    if before:
        kwargs["date_lt"] = before
    if after:
        kwargs["date_gte"] = after

    with _login() as mailbox:
        msgs = list(mailbox.fetch(AND(**kwargs), headers_only=True, bulk=True))
    msgs = [m for m in msgs if _matches(m, text, mode)]
    msgs.sort(key=lambda m: m.date.timestamp(), reverse=(order == "newest"))

    trashable = [m for m in msgs if not _is_protected(m.subject)]
    protected = [m for m in msgs if _is_protected(m.subject)]
    if count:
        trashable = trashable[:count]

    return {
        "count": len(trashable),
        "protected": len(protected),
        "uids": [m.uid for m in trashable],
        "protected_uids": [m.uid for m in protected],
        "samples": [f"{m.date:%Y-%m-%d} | {m.from_} | {m.subject}" for m in trashable],
        "protected_samples": [m.subject for m in protected],
    }


def trash_uids(uids, batch=50):
    """Move exactly these emails to Trash, a few at a time."""
    moved = 0
    with _login() as mailbox:
        for i in range(0, len(uids), batch):
            chunk = uids[i:i + batch]
            mailbox.move(chunk, "[Gmail]/Trash")
            moved += len(chunk)
    return moved