import subprocess
import colorama
from colorama import Fore, Style
import sys
import logging

def start(engine):
    try:
        colorama.init()
        print(f"{Fore.BLUE}=== USB-AI CLI Interface ==={Style.RESET_ALL}")
        
        while True:
            try:
                user_input = input(f"{Fore.GREEN}You: {Style.RESET_ALL}").strip()
                if not user_input:
                    continue
                if user_input.lower() == "exit":
                    break
                
                response = engine.process_input(user_input)
                print(f"{Fore.CYAN}AI: {response}{Style.RESET_ALL}")
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                logging.error(f"CLI error: {e}")
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
        logging.error(f"Fatal CLI error: {e}")
        sys.exit(1)

def launch_new_console():
    subprocess.Popen(["cmd.exe", "/c", "python", "E:\\USBAI\\ui\\cli.py"])
