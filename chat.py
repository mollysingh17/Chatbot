import ollama

MODEL = "llama3.2:3b"
history = []

print("Chatbot ready. Type 'quit' to exit.")
while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break

    history.append({"role": "user", "content": user_input})
    response = ollama.chat(model="llama3.2:3b", messages=history)
    reply = response.message.content

    history.append({"role": "assistant", "content": reply})
    print("Bot:", reply)