import logging

def start(engine):
    print("USB-AI Session Started. Type 'exit' or 'quit' to quit.")
    logging.info("CLI session started")
    while True:
        user_input = input("> ")
        if user_input.lower() in ["exit", "quit"]:
            break

        response = engine.process_input(user_input)
        print(response)
        logging.info(f"User: {user_input}")
        logging.info(f"AI: {response}")

    print("Session ended. Goodbye!")
    logging.info("CLI session ended")