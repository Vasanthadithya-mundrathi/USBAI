# File: ui/gui.py
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import os
from pathlib import Path
from PIL import Image, ImageTk
import sys

# Dynamically import the appropriate AI engine based on the selected model
def load_engine(model_name):
    if model_name == "Gemma-3-1B-IT":
        sys.path.append(str(Path("E:/USBAI")))
        from ai_engine2 import USBAIEngine
    else:  # TinyLLaMA
        sys.path.append(str(Path("E:/USBAI")))
        from ai_engine import USBAIEngine
    return USBAIEngine

class USBAIGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("USB-AI Chat")
        self.root.geometry("600x700")  # Set window size
        self.root.resizable(True, True)  # Allow resizing

        # Set window icon (optional, if you have an icon file)
        try:
            icon_path = Path("E:/USBAI/assets/icon.ico")
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Could not load icon: {e}")

        # Initialize variables
        self.current_model = "Gemma-3-1B-IT"  # Default model
        self.engine = load_engine(self.current_model)(model_name=self.current_model.lower())
        self.thinking = False  # Flag to track if the AI is processing
        self.thinking_frames = []  # For the spinner animation
        self.current_frame = 0  # Current frame of the spinner
        self.theme = "Light"  # Default theme

        # Load the spinner GIF
        try:
            spinner_path = Path("E:/USBAI/assets/spinner.gif")
            if spinner_path.exists():
                self.load_spinner_gif(str(spinner_path))
            else:
                print("Spinner GIF not found at E:/USBAI/assets/spinner.gif. Falling back to text animation.")
                self.spinner_available = False
        except Exception as e:
            print(f"Failed to load spinner GIF: {e}. Falling back to text animation.")
            self.spinner_available = False

        # Create the main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Model selection dropdown
        self.model_var = tk.StringVar(value=self.current_model)
        self.model_dropdown = ttk.Combobox(
            self.main_frame,
            textvariable=self.model_var,
            values=["Gemma-3-1B-IT", "TinyLLaMA"],
            state="readonly",
            font=("Helvetica", 12)
        )
        self.model_dropdown.pack(pady=5)
        self.model_dropdown.bind("<<ComboboxSelected>>", self.change_model)

        # Theme selection dropdown
        self.theme_var = tk.StringVar(value=self.theme)
        self.theme_dropdown = ttk.Combobox(
            self.main_frame,
            textvariable=self.theme_var,
            values=["Light", "Dark"],
            state="readonly",
            font=("Helvetica", 12)
        )
        self.theme_dropdown.pack(pady=5)
        self.theme_dropdown.bind("<<ComboboxSelected>>", self.change_theme)

        # Title label
        self.title_label = ttk.Label(
            self.main_frame,
            text="USB-AI Chat",
            font=("Helvetica", 16, "bold"),
            foreground="#1a73e8"  # Google Blue
        )
        self.title_label.pack(pady=10)

        # Chat history area (scrollable)
        self.chat_area = scrolledtext.ScrolledText(
            self.main_frame,
            wrap=tk.WORD,
            height=25,
            font=("Helvetica", 12),
            state="disabled"  # Read-only
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Thinking label (for animation)
        self.thinking_label = ttk.Label(
            self.main_frame,
            text="",
            font=("Helvetica", 12, "italic"),
            compound="left"  # For the spinner GIF
        )
        self.thinking_label.pack(pady=5)

        # Input frame (for entry and buttons)
        self.input_frame = ttk.Frame(self.main_frame)
        self.input_frame.pack(fill=tk.X, pady=5)

        # Input field
        self.input_entry = ttk.Entry(
            self.input_frame,
            font=("Helvetica", 12)
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", self.send_message)  # Bind Enter key to send

        # Send button
        self.send_button = ttk.Button(
            self.input_frame,
            text="Send",
            command=self.send_message
        )
        self.send_button.pack(side=tk.LEFT, padx=(0, 5))

        # Clear chat button
        self.clear_button = ttk.Button(
            self.input_frame,
            text="Clear Chat",
            command=self.clear_chat
        )
        self.clear_button.pack(side=tk.LEFT)

        # Apply the theme after all widgets are created
        self.apply_theme()

        # Initial message in chat area
        self.add_to_chat("AI", f"Hello! 👋 I'm USB-AI ({self.current_model}). How can I help you today? 😊")

    def load_spinner_gif(self, path):
        """Load the spinner GIF frames."""
        self.spinner_available = True
        image = Image.open(path)
        self.thinking_frames = []
        try:
            while True:
                frame = ImageTk.PhotoImage(image.copy())
                self.thinking_frames.append(frame)
                image.seek(len(self.thinking_frames))  # Move to the next frame
        except EOFError:
            pass  # End of GIF frames

    def apply_theme(self):
        """Apply the selected theme to the GUI."""
        if self.theme == "Light":
            self.root.configure(bg="#f0f2f5")
            self.chat_area.configure(bg="#ffffff", fg="#333333")
            self.thinking_label.configure(foreground="#888888")
        else:  # Dark
            self.root.configure(bg="#333333")
            self.chat_area.configure(bg="#444444", fg="#ffffff")
            self.thinking_label.configure(foreground="#bbbbbb")

    def change_model(self, event=None):
        """Change the active model."""
        new_model = self.model_var.get()
        if new_model != self.current_model:
            self.current_model = new_model
            self.engine = load_engine(self.current_model)(model_name=self.current_model.lower())
            self.add_to_chat("System", f"Switched to {self.current_model} model.")

    def change_theme(self, event=None):
        """Change the theme."""
        self.theme = self.theme_var.get()
        self.apply_theme()

    def clear_chat(self):
        """Clear the chat history."""
        self.chat_area.configure(state="normal")
        self.chat_area.delete(1.0, tk.END)
        self.chat_area.configure(state="disabled")

    def add_to_chat(self, sender, message):
        """Add a message to the chat area."""
        self.chat_area.configure(state="normal")  # Enable editing
        if sender == "User":
            self.chat_area.insert(tk.END, f"You: {message}\n", "user")
        elif sender == "AI":
            self.chat_area.insert(tk.END, f"AI: {message}\n", "ai")
        elif sender == "System":
            self.chat_area.insert(tk.END, f"System: {message}\n", "system")
        self.chat_area.configure(state="disabled")  # Disable editing
        self.chat_area.see(tk.END)  # Scroll to the bottom

        # Define tags for styling
        self.chat_area.tag_configure("user", foreground="#1a73e8", font=("Helvetica", 12, "bold"))  # Blue for user
        self.chat_area.tag_configure("ai", foreground="#34a853", font=("Helvetica", 12))  # Green for AI
        self.chat_area.tag_configure("system", foreground="#888888", font=("Helvetica", 12, "italic"))  # Gray for system messages

    def update_thinking_animation(self):
        """Update the thinking animation."""
        if not self.thinking:
            self.thinking_label.config(text="", image="")
            return
        if self.spinner_available and self.thinking_frames:
            # Update the spinner GIF frame
            self.current_frame = (self.current_frame + 1) % len(self.thinking_frames)
            self.thinking_label.config(image=self.thinking_frames[self.current_frame])
        else:
            # Fallback to text animation
            dots = "..." if len(self.thinking_label.cget("text").replace("Thinking", "")) >= 3 else self.thinking_label.cget("text").replace("Thinking", "") + "."
            self.thinking_label.config(text=f"Thinking{dots}")
        self.root.after(100 if self.spinner_available else 500, self.update_thinking_animation)  # Faster for GIF

    def send_message(self, event=None):
        """Handle sending a message."""
        user_input = self.input_entry.get().strip()
        if not user_input:
            return

        # Add user message to chat
        self.add_to_chat("User", user_input)
        self.input_entry.delete(0, tk.END)  # Clear the input field

        # Disable the send button and input field while processing
        self.send_button.config(state="disabled")
        self.input_entry.config(state="disabled")
        self.clear_button.config(state="disabled")

        # Start the thinking animation
        self.thinking = True
        self.update_thinking_animation()

        # Process the input in a separate thread to avoid freezing the GUI
        threading.Thread(target=self.process_input, args=(user_input,), daemon=True).start()

    def process_input(self, user_input):
        """Process the user input using the AI engine."""
        try:
            response = self.engine.process_input(user_input)
            self.root.after(0, lambda: self.display_response(response))
        except Exception as e:
            self.root.after(0, lambda: self.display_response(f"Error: {str(e)}"))

    def display_response(self, response):
        """Display the AI's response in the chat area."""
        # Stop the thinking animation
        self.thinking = False
        self.thinking_label.config(text="", image="")

        # Add AI response to chat
        self.add_to_chat("AI", response)

        # Re-enable the send button and input field
        self.send_button.config(state="normal")
        self.input_entry.config(state="normal")
        self.clear_button.config(state="normal")
        self.input_entry.focus()  # Set focus back to the input field

def main():
    root = tk.Tk()
    app = USBAIGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()