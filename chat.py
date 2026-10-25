import json
import re
import datetime
import ollama
from email_tools import search_emails, trash_uids

MODEL = "llama3.2:3b"
MAX_PER_RUN = 100
QUIT_WORDS = {"quit", "exit", "no", "n", "nope", "nah"}

SCHEMA = {
    "type": "object",
    "properties": {
        "sender": {"type": "string"},
        "search_in": {"type": "string", "enum": ["sender", "subject"]},
        "before": {"type": "string"},
        "after": {"type": "string"},
        "count": {"type": "integer"},
        "order": {"type": "string", "enum": ["oldest", "newest", "none"]},
    },
    "required": ["sender", "search_in", "before", "after", "count", "order"],
}

PROMPT = (
    "Read this email cleanup request and fill in the fields. "
    "sender: the company, person, or word to search for, lowercase, no 's. "
    "search_in: 'sender' unless the user literally says the word subject, "
    "in which case 'subject'. "
    "before: the date the emails must be older than, copied exactly as the user "
    "wrote it, or an empty string if none. "
    "after: the date the emails must be newer than, copied exactly as the user "
    "wrote it, or an empty string if none. "
    "count: how many emails the user wants, or 0 if they gave no number. "
    "order: 'newest' if the user asks for the most recent, latest, or last "
    "emails, 'oldest' if the user asks for the first or earliest emails, "
    "'none' if they say neither. Request: "
)


def parse_date(s):
    """Turn text like '2025' or 'March 2024' into a date. Raises ValueError."""
    s = (s or "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d{4}", s):
        return datetime.date(int(s), 1, 1)
    for fmt in ("%Y-%m-%d", "%B %Y", "%b %Y", "%B %d %Y", "%b %d %Y",
                "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(s)


def parse_request(text):
    t = text.strip()
    base = {"before": "", "after": "", "count": 0, "order": "none"}
    if t.lower().startswith("subject:"):
        return {**base, "sender": t[len("subject:"):].strip().lower(), "search_in": "subject"}
    if len(t.split()) <= 2:  # just a name, no model needed
        return {**base, "sender": t.lower(), "search_in": "sender"}

    r = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT + t}],
        format=SCHEMA,
    )
    req = json.loads(r.message.content)
    req["sender"] = re.sub(r"'s$", "", req["sender"].strip().lower())
    if req["search_in"] == "subject" and "subject" not in t.lower():
        req["search_in"] = "sender"
    for key in ("before", "after"):
        v = req[key].strip()
        if not (any(c.isdigit() for c in v) and len(v) <= 20 and v.lower() in t.lower()):
            v = ""
        req[key] = v

    # a year like 2025 is a date, not a count
    if req["count"] and str(req["count"]) in (req["before"] + " " + req["after"]):
        req["count"] = 0
    return req


print("Bot: Hi! What do you want to get rid of?")
prompt = "You: "

while True:
    user_input = input(prompt)
    cleaned = user_input.strip().lower()
    if cleaned in QUIT_WORDS:
        print("Bot: Bye!")
        break
    if cleaned in ("yes", "y"):
        print("Bot: Which one? Tell me a sender or subject.")
        continue
    if not cleaned:
        continue

    req = parse_request(user_input)
    try:
        before = parse_date(req["before"])
        after = parse_date(req["after"])
    except ValueError as e:
        print(f"Bot: I couldn't read the date '{e}'. Try a year or a month and year.")
        continue

    text, mode = req["sender"], req["search_in"]
    count = req["count"] or None
    order = req["order"]

    if order != "none" and not count:
        n = input("Bot: How many? (a number, or 'all') ").strip().lower()
        if n.isdigit():
            count = int(n)
        elif n != "all":
            print("Bot: Didn't catch that, try again.")
            continue
    if order == "none":
        order = "oldest"

    parts = [f"{mode} matching '{text}'"]
    if before:
        parts.append(f"before {before}")
    if after:
        parts.append(f"from {after} onward")
    if count:
        parts.append(f"{order} {count}")
    print("Bot: I understood: " + ", ".join(parts))

    result = search_emails(text, mode, before, after, count, order)
    print(f"Bot: Found {result['count']} emails to clear out "
          f"({result['protected']} protected: receipts, codes, etc.).")
    for s in result["samples"]:
        print("   ", s)
    for s in result["protected_samples"]:
        print("    kept:", s)

    prompt = "Bot: Another one? (tell me a sender or subject, or 'no' to quit)\nYou: "

    if result["count"] == 0:
        if result["protected"] > 0:
            answer = input(f"Bot: Everything matching is protected ({result['protected']} emails). "
                           "Move them to Trash anyway? (yes/no) ")
            if answer.strip().lower() == "yes":
                moved = trash_uids(result["protected_uids"][:MAX_PER_RUN])
                print(f"Bot: Moved {moved} to Trash.")
            else:
                print("Bot: Okay, left them alone.")
        else:
            print("Bot: Nothing to clear.")
        continue

    uids = result["uids"][:MAX_PER_RUN]
    answer = input(f"Bot: Move {len(uids)} of {result['count']} to Trash? (yes/no) ")
    if answer.strip().lower() == "yes":
        moved = trash_uids(uids)
        left = search_emails(text, mode, before, after)["count"]
        print(f"Bot: Moved {moved} to Trash. {left} matching still in your inbox.")
    else:
        print("Bot: Okay, left them alone.")