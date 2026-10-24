# Email Assistant Chatbot

A command-line chatbot that cleans up my Gmail. Name a sender or subject, review what it found, confirm, and the emails move to Trash.

Runs locally on Llama 3.2 (via Ollama), so your email never touches a cloud AI service.

## Features

- Sender search: type sender name to match by sender name or address
- Subject search: type `subject: xyz ` to match subject lines
- Confirmation : lists every email it found and waits for a `yes`
- Trash: moves to trash after confirmation
- Protected emails: receipts, invoices, passwords, and verification codes are skipped by default
- Safety cap: 100 emails max per confirmation
- Quit with `no`, `quit`, or `exit`

## How it works

Llama 3.2 turns user input into a search term. Everything else (searching Gmail, filtering, trashing) is plain Python, the model never takes an action on its own.

## Setup

1. Install [Ollama](https://ollama.com) and run `ollama pull llama3.2:3b`
2. Install dependencies:
   ```
   pip install ollama imap-tools python-dotenv
   ```
3. Enable 2-Step Verification on your Google account and create an [app password](https://myaccount.google.com/apppasswords)
4. Create a `.env` file:
   ```
   GMAIL_ADDRESS=you@gmail.com
   GMAIL_APP_PASSWORD=your16characterpassword
   ```
5. Run:
   ```
   python chat.py
   ```

## Roadmap

- [ ] Date filters (e.g. "first 100 emails from xyz " or "everything from xyz before 2025")
- [ ] Automatic unsubscribe using the `List-Unsubscribe` header
- [ ] Optionally search All Mail, not just the Inbox
- [ ] Conversational replies
