import json
import ollama
from email_tools import search_emails, trash_uids

MODEL = "llama3.2:3b"
QUIT_WORDS = {"quit", "exit", "no", "n", "nope", "nah"}

SCHEMA = {
    "type": "object",
    "properties": {"sender": {"type": "string"}},
    "required": ["sender"],
}


def parse_request(text):
    """Returns (mode, search_text)."""
    t = text.strip()
    if t.lower().startswith("subject:"):
        return "subject", t[len("subject:"):].strip().lower()
    words = t.split()
    if len(words) <= 2:  
        return "sender", " ".join(words).lower()
    r = ollama.chat(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": "Extract the company or sender name from this message "
                       f"as one lowercase word. Message: {t}",
        }],
        format=SCHEMA,
    )
    return "sender", json.loads(r.message.content)["sender"].strip().lower()


print("Bot: Hi! Who or what do you want to get rid of? I can clear out a sender's emails.")
print("     Type a sender name, or 'subject: ...' to search subject lines. Type 'no' or 'quit' to exit.")
prompt = "You: "

while True:
    user_input = input(prompt)
    cleaned = user_input.strip().lower()
    if cleaned in QUIT_WORDS:
        print("Bot: Bye!")
        break
    if cleaned in ("yes", "y"):
        print("Bot: Which one? (a sender name, or 'subject: ...')")
        continue
    if not cleaned:
        continue

    mode, text = parse_request(user_input)
    result = search_emails(text, mode)
    label = "subject containing" if mode == "subject" else "sender matching"
    print(f"Bot: Found {result['count']} emails with {label} '{text}' to clear out "
          f"({result['protected']} protected: receipts, codes, etc.).")
    for s in result["samples"]:
        print("   ", s)
    for s in result["protected_samples"]:
        print("    kept:", s)

    prompt = "Bot: Another one? (type a sender, 'subject: ...', or 'no' to quit)\nYou: "

    if result["count"] == 0:
        if result["protected"] > 0:
            answer = input(f"Bot: Everything matching is protected ({result['protected']} emails). "
                           "Move them to Trash anyway? (yes/no) ")
            if answer.strip().lower() == "yes":
                moved = trash_uids(result["protected_uids"][:100])
                print(f"Bot: Moved {moved} to Trash.")
            else:
                print("Bot: Okay, left them alone.")
        else:
            print("Bot: Nothing to clear.")
        continue

    uids = result["uids"][:100]
    answer = input(f"Bot: Move {len(uids)} of {result['count']} to Trash? (yes/no) ")
    if answer.strip().lower() == "yes":
        moved = trash_uids(uids)
        left = search_emails(text, mode)["count"]
        print(f"Bot: Moved {moved} to Trash. {left} still in your inbox.")
    else:
        print("Bot: Okay, left them alone.")