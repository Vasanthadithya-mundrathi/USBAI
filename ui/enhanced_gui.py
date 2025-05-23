# File: ui/enhanced_gui.py
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, messagebox
import threading
import os
import time
import json
import sys
from pathlib import Path
from PIL import Image, ImageTk
import re
import importlib
import platform
import psutil

# Add parent directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

# Function to load the appropriate AI engine based on model selection
def load_engine(model_name):
    """Dynamically import the appropriate AI engine based on the selected model"""
    base_path = "E:/USBAI"
    
    # Map models to their engines
    engine_map = {
        "Gemma-3-1B-IT": ("ai_engine2", "USBAIEngine"),
        "TinyLLaMA": ("ai_engine2", "USBAIEngine"),
        "Phi-3.5-mini-instruct": ("ai_engine2", "USBAIEngine"),  # Future model
        "DeepSeek-Coder-6.7B-base": ("ai_engine2", "USBAIEngine"),    # Future model
    }
    
    if model_name not in engine_map:
        raise ValueError(f"Unknown model: {model_name}")
    
    # Add parent directory to path
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(parent_dir)
    
    # Import the engine dynamically
    try:
        module_name, class_name = engine_map[model_name]
        module = importlib.import_module(module_name)
        engine_class = getattr(module, class_name)
    except ImportError as e:
        raise ImportError(f"Failed to import engine for model {model_name}: {e}")
    except AttributeError as e:
        raise AttributeError(f"Failed to find engine class for model {model_name}: {e}")
    
    return engine_class

class ModelSettingsFrame(ttk.LabelFrame):
    """A frame for model settings and controls"""
    def __init__(self, parent, app):
        super().__init__(parent, text="Model Settings", padding=(10, 5))
        self.app = app
        
        # Create model selection widgets
        self.model_label = ttk.Label(self, text="AI Model:")
        self.model_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        # Model dropdown
        self.model_var = tk.StringVar(value=app.current_model)
        self.model_dropdown = ttk.Combobox(
            self,
            textvariable=self.model_var,
            values=app.available_models,
            state="readonly",
            width=20
        )
        self.model_dropdown.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.model_dropdown.bind("<<ComboboxSelected>>", self.change_model)
        
        # Temperature setting
        self.temp_label = ttk.Label(self, text="Temperature:")
        self.temp_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        self.temp_var = tk.DoubleVar(value=app.temperature)
        self.temp_scale = ttk.Scale(
            self,
            from_=0.1,
            to=1.0,
            orient="horizontal",
            variable=self.temp_var,
            command=self.update_temp_label
        )
        self.temp_scale.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        self.temp_value_label = ttk.Label(self, text=f"{app.temperature:.1f}")
        self.temp_value_label.grid(row=1, column=2, sticky="w", padx=5, pady=5)
        
        # Max tokens setting
        self.max_tokens_label = ttk.Label(self, text="Max Tokens:")
        self.max_tokens_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        
        self.max_tokens_var = tk.IntVar(value=app.max_tokens)
        self.max_tokens_spinbox = ttk.Spinbox(
            self,
            from_=10,
            to=500,
            textvariable=self.max_tokens_var,
            width=5
        )
        self.max_tokens_spinbox.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Configure grid to expand properly
        self.columnconfigure(1, weight=1)
    
    def change_model(self, event=None):
        """Change the active model"""
        new_model = self.model_var.get()
        if new_model != self.app.current_model:
            try:
                self.app.change_model(new_model)
            except Exception as e:
                messagebox.showerror("Model Error", f"Failed to change model: {e}")
                # Reset to the current model
                self.model_var.set(self.app.current_model)
    
    def update_temp_label(self, value=None):
        """Update the temperature value label"""
        value = self.temp_var.get()
        self.temp_value_label.config(text=f"{value:.1f}")
        self.app.temperature = value

class ChatFrame(ttk.Frame):
    """A frame for the chat interface"""
    def __init__(self, parent, app):
        super().__init__(parent, padding=(10, 5))
        self.app = app
        
        # Chat history area (scrollable)
        self.chat_area = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            height=20,
            font=("Helvetica", 11),
            state="disabled"  # Read-only
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Define tags for styling
        self.chat_area.tag_configure("user", foreground="#1a73e8", font=("Helvetica", 11, "bold"))
        self.chat_area.tag_configure("ai", foreground="#34a853", font=("Helvetica", 11))
        self.chat_area.tag_configure("system", foreground="#888888", font=("Helvetica", 11, "italic"))
        self.chat_area.tag_configure("code", font=("Courier New", 10), background="#f0f0f0")
        
        # Thinking label (for animation)
        self.thinking_label = ttk.Label(
            self,
            text="",
            font=("Helvetica", 11, "italic")
        )
        self.thinking_label.pack(pady=5)
        
        # Input area
        self.input_frame = ttk.Frame(self)
        self.input_frame.pack(fill=tk.X, pady=5)
        
        # Text input box (multi-line)
        self.input_text = scrolledtext.ScrolledText(
            self.input_frame,
            wrap=tk.WORD,
            height=3,
            font=("Helvetica", 11)
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.input_text.bind("<Control-Return>", self.send_message)  # Ctrl+Enter to send
        
        # Buttons frame
        self.buttons_frame = ttk.Frame(self.input_frame)
        self.buttons_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Send button with improved styling
        self.send_button = ttk.Button(
            self.buttons_frame,
            text="Send",
            command=self.send_message,
            style="AccentButton.TButton"
        )
        self.send_button.pack(fill=tk.X, pady=(0, 5))
        
        # Clear chat button
        self.clear_button = ttk.Button(
            self.buttons_frame,
            text="Clear Chat",
            command=self.clear_chat
        )
        self.clear_button.pack(fill=tk.X, pady=(0, 5))
        
        # Save chat button (new)
        self.save_button = ttk.Button(
            self.buttons_frame,
            text="Save Chat",
            command=self.save_chat
        )
        self.save_button.pack(fill=tk.X)
    
    def clear_chat(self):
        """Clear the chat history"""
        self.chat_area.config(state="normal")
        self.chat_area.delete(1.0, tk.END)
        self.chat_area.config(state="disabled")
        # Add system message about clearing
        self.add_message("system", "Chat history cleared")
    
    def add_message(self, sender, message):
        """Add a message to the chat area with proper formatting"""
        # Enable editing
        self.chat_area.config(state=tk.NORMAL)
        
        # Add timestamp
        timestamp = time.strftime("[%H:%M:%S] ")
        self.chat_area.insert(tk.END, timestamp, "system")
        
        # Add prefix based on sender
        if sender == "user":
            self.chat_area.insert(tk.END, "You: ", "user")
        elif sender == "ai":
            self.chat_area.insert(tk.END, "USB-AI: ", "ai")
        elif sender == "system":
            self.chat_area.insert(tk.END, "System: ", "system")
        
        # Check if message contains code blocks
        if "```" in message:
            # Process code blocks
            parts = message.split("```")
            
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    if part.strip():
                        if sender == "user":
                            self.chat_area.insert(tk.END, part, "user")
                        elif sender == "ai":
                            self.chat_area.insert(tk.END, part, "ai")
                        else:
                            self.chat_area.insert(tk.END, part, "system")
                else:  # Code block
                    self.chat_area.insert(tk.END, f"\n{part}\n", "code")
            
        else:
            # Plain text message
            if sender == "user":
                self.chat_area.insert(tk.END, message, "user")
            elif sender == "ai":
                self.chat_area.insert(tk.END, message, "ai")
            else:
                self.chat_area.insert(tk.END, message, "system")
        
        # Add newline
        self.chat_area.insert(tk.END, "\n\n")
        
        # Scroll to bottom
        self.chat_area.see(tk.END)
        
        # Disable editing
        self.chat_area.config(state=tk.DISABLED)
    
    def send_message(self, event=None):
        """Handle sending a message"""
        # Get the input text
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input:
            return
        
        # Clear the input box
        self.input_text.delete("1.0", tk.END)
        
        # Process input in a separate thread
        threading.Thread(target=self.app.process_input, args=(user_input,), daemon=True).start()

    def save_chat(self):
        """Save the chat history to a file"""
        try:
            # Get the file path
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Chat As"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Get chat content
            content = self.chat_area.get(1.0, tk.END)
            
            # Save to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            self.add_message("system", f"Chat saved to {file_path}")
            
        except Exception as e:
            self.add_message("system", f"Error saving chat: {str(e)}")

class USBAIEnhancedGUI:
    """Main application class for the USB-AI Enhanced GUI interface"""
    def __init__(self, root):
        self.root = root
        self.root.title("USB-AI Enhanced Interface")
        self.root.geometry("900x700")  # Larger window size
        self.root.minsize(800, 600)    # Minimum window size
        
        # Initialize variables
        self.base_path = str(Path("E:/USBAI"))  # Convert to string right away
        self.current_model = "Gemma-3-1B-IT"
        self.available_models = ["Gemma-3-1B-IT", "TinyLLaMA", "Phi-3.5-mini-instruct", "DeepSeek-Coder-6.7B-base"]
        self.engine = None
        self.thinking = False
        self.temperature = 0.7
        self.max_tokens = 150
        self.theme = "Light"
        
        # Set up default file paths as strings
        self.logs_path = os.path.join(self.base_path, "logs")
        self.models_path = os.path.join(self.base_path, "models")
        
        # Ensure directories exist
        os.makedirs(self.logs_path, exist_ok=True)
        os.makedirs(self.models_path, exist_ok=True)
        
        # Initialize engine
        self.load_engine()
        
        # Set up UI theme
        self.style = ttk.Style()
        self.apply_theme()
        
        # Create main frames
        self.setup_layout()
        
        # Initialize with welcome message
        self.chat_frame.add_message("system", f"Welcome to USB-AI! Using {self.current_model}")
        self.chat_frame.add_message("ai", f"Hello! 👋 I'm USB-AI ({self.current_model}). How can I help you today?")
        
        # Start model status check
        self.check_model_status()
    
    def setup_layout(self):
        """Set up the main layout"""
        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chat tab
        self.chat_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chat_tab, text="Chat")
        
        # Model tab
        self.model_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.model_tab, text="Model Management")
        
        # Settings tab
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Status bar
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        self.status_label = ttk.Label(
            self.status_bar, 
            text=f"Model: {self.current_model} | Status: Ready", 
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT)
        
        self.memory_label = ttk.Label(
            self.status_bar,
            text="Memory: Calculating...",
            anchor=tk.E
        )
        self.memory_label.pack(side=tk.RIGHT)
        
        # Set up chat tab
        self.setup_chat_tab()
        
        # Set up model tab
        self.setup_model_tab()
        
        # Set up settings tab
        self.setup_settings_tab()
    
    def setup_chat_tab(self):
        """Set up the chat interface tab"""
        # Split the chat tab into sections
        self.chat_pane = ttk.PanedWindow(self.chat_tab, orient=tk.HORIZONTAL)
        self.chat_pane.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for settings
        self.left_panel = ttk.Frame(self.chat_pane)
        self.chat_pane.add(self.left_panel, weight=1)
        
        # Right panel for chat
        self.right_panel = ttk.Frame(self.chat_pane)
        self.chat_pane.add(self.right_panel, weight=4)
        
        # Add model settings to left panel
        self.model_settings = ModelSettingsFrame(self.left_panel, self)
        self.model_settings.pack(fill=tk.X, padx=5, pady=5)
        
        # Add chat history to right panel
        self.chat_frame = ChatFrame(self.right_panel, self)
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
    
    def setup_model_tab(self):
        """Set up the model management tab"""
        # Model information
        self.model_info_frame = ttk.LabelFrame(self.model_tab, text="Model Information")
        self.model_info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a two-column layout
        self.model_list_frame = ttk.Frame(self.model_info_frame)
        self.model_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.model_details_frame = ttk.Frame(self.model_info_frame)
        self.model_details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Model list label
        self.model_list_label = ttk.Label(self.model_list_frame, text="Available Models:")
        self.model_list_label.pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        # Model list
        self.model_listbox = tk.Listbox(
            self.model_list_frame,
            height=10,
            font=("Helvetica", 12),
            activestyle='dotbox',
            selectbackground='#1a73e8',
            selectforeground='white'
        )
        self.model_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.model_listbox.bind('<<ListboxSelect>>', self.display_model_details)
        
        # Scrollbar for model list
        self.model_scrollbar = ttk.Scrollbar(self.model_list_frame, orient=tk.VERTICAL, command=self.model_listbox.yview)
        self.model_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.model_listbox.config(yscrollcommand=self.model_scrollbar.set)
        
        # Model details
        self.model_details_label = ttk.Label(self.model_details_frame, text="Model Details:")
        self.model_details_label.pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        self.model_details_text = scrolledtext.ScrolledText(
            self.model_details_frame,
            height=8,
            font=("Helvetica", 11),
            wrap=tk.WORD
        )
        self.model_details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.model_details_text.config(state="disabled")
        
        # Model operations
        self.model_ops_frame = ttk.Frame(self.model_tab)
        self.model_ops_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Refresh model list button
        self.refresh_button = ttk.Button(
            self.model_ops_frame,
            text="Refresh Models",
            command=self.refresh_models
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Organize models button
        self.organize_button = ttk.Button(
            self.model_ops_frame,
            text="Organize Models",
            command=self.organize_models
        )
        self.organize_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Convert models button
        self.convert_button = ttk.Button(
            self.model_ops_frame,
            text="Convert to UAMF",
            command=self.convert_models
        )
        self.convert_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Download Model button (new)
        self.download_button = ttk.Button(
            self.model_ops_frame,
            text="Download Model",
            command=self.download_model,
            style="AccentButton.TButton"
        )
        self.download_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Load Model button (new)
        self.load_model_button = ttk.Button(
            self.model_ops_frame,
            text="Load Selected Model",
            command=self.load_selected_model
        )
        self.load_model_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Initialize model list
        self.refresh_models()

    def display_model_details(self, event=None):
        """Display details for the selected model"""
        try:
            # Get the selected model
            selection = self.model_listbox.curselection()
            if not selection:
                return
            
            model_name = self.model_listbox.get(selection[0])
            model_path = os.path.join(self.models_path, model_name)
            
            # Get model details
            details = []
            details.append(f"Model Name: {model_name}")
            
            # Check if model exists
            if os.path.exists(model_path):
                # Get size
                try:
                    size = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                            for dirpath, _, filenames in os.walk(model_path) 
                            for filename in filenames)
                    size_mb = size / (1024 * 1024)
                    details.append(f"Size: {size_mb:.2f} MB")
                except Exception:
                    details.append("Size: Unable to calculate")
                
                # Count files
                try:
                    file_count = sum(len(files) for _, _, files in os.walk(model_path))
                    details.append(f"Files: {file_count}")
                except Exception:
                    details.append("Files: Unable to count")
                
                # Last modified time
                try:
                    last_modified_files = []
                    for dirpath, _, filenames in os.walk(model_path):
                        for filename in filenames:
                            file_path = os.path.join(dirpath, filename)
                            last_modified_files.append(os.path.getmtime(file_path))
                    
                    if last_modified_files:
                        last_modified = max(last_modified_files)
                        details.append(f"Last Modified: {time.ctime(last_modified)}")
                    else:
                        details.append("Last Modified: Unknown")
                except Exception:
                    details.append("Last Modified: Unable to determine")
                
                # Model type based on name
                if "gemma" in model_name.lower():
                    details.append("Model Type: Gemma (Google)")
                elif "llama" in model_name.lower():
                    details.append("Model Type: LLaMA (Meta)")
                elif "phi" in model_name.lower():
                    details.append("Model Type: Phi (Microsoft)")
                elif "deepseek" in model_name.lower():
                    details.append("Model Type: DeepSeek (DeepSeek AI)")
                else:
                    details.append("Model Type: Unknown")
                
                # Status
                details.append("Status: Downloaded")
                
                # Check for UAMF conversion
                try:
                    uamf_files = [f for f in os.listdir(model_path) if f.endswith('.uamf')]
                    if uamf_files:
                        details.append("UAMF Status: Converted")
                    else:
                        details.append("UAMF Status: Not Converted")
                except Exception:
                    details.append("UAMF Status: Unknown")
            else:
                details.append("Status: Not Downloaded")
            
            # Update the details text
            self.model_details_text.config(state="normal")
            self.model_details_text.delete(1.0, tk.END)
            self.model_details_text.insert(tk.END, "\n".join(details))
            self.model_details_text.config(state="disabled")
            
        except Exception as e:
            self.model_details_text.config(state="normal")
            self.model_details_text.delete(1.0, tk.END)
            self.model_details_text.insert(tk.END, f"Error getting model details: {str(e)}")
            self.model_details_text.config(state="disabled")

    def download_model(self):
        """Download a model from Hugging Face"""
        # Create a top-level window for the download dialog
        download_window = tk.Toplevel(self.root)
        download_window.title("Download Model")
        download_window.geometry("500x400")
        download_window.transient(self.root)  # Set to be on top of the main window
        download_window.grab_set()  # Make window modal
        
        # Model selection frame
        model_frame = ttk.LabelFrame(download_window, text="Select Model")
        model_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Model options
        available_models = [
            "microsoft/phi-3.5-mini-instruct",
            "deepseek-ai/deepseek-coder-6.7b-base",
            "google/gemma-3-1b-it",
            "TinyLLama/TinyLlama-1.1B-Chat-v1.0"
        ]
        
        model_var = tk.StringVar(value=available_models[0])
        
        for i, model in enumerate(available_models):
            ttk.Radiobutton(
                model_frame, 
                text=model, 
                value=model, 
                variable=model_var
            ).pack(anchor=tk.W, padx=20, pady=5)
        
        # Token frame
        token_frame = ttk.LabelFrame(download_window, text="Hugging Face Token (if needed)")
        token_frame.pack(fill=tk.X, padx=10, pady=10)
        
        token_var = tk.StringVar(value="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")  # Default from memory
        token_entry = ttk.Entry(token_frame, textvariable=token_var, width=40)
        token_entry.pack(padx=10, pady=10, fill=tk.X)
        
        # Button frame
        button_frame = ttk.Frame(download_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Status label
        status_label = ttk.Label(download_window, text="")
        status_label.pack(pady=10)
        
        # Function to start download
        def start_download():
            model = model_var.get()
            token = token_var.get()
            
            # Show loading indicator
            status_label.config(text=f"Starting download of {model}...")
            
            # Show message in main window
            self.chat_frame.add_message("system", f"Starting download of {model}...")
            self.chat_frame.add_message("system", "This may take several hours. You can continue using the app.")
            
            # In a real implementation, we would use transformers to download the model
            # For this demo, just show a message
            messagebox.showinfo("Download Started", 
                               f"The download of {model} has been initiated.\n\n" +
                               "Due to size limitations, this is a simulated download. In a real application, " +
                               "this would download the actual model using the Hugging Face libraries.")
            
            # Close the dialog
            download_window.destroy()
        
        # Download button
        download_button = ttk.Button(
            button_frame,
            text="Start Download",
            command=start_download,
            style="AccentButton.TButton"
        )
        download_button.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=download_window.destroy
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)

    def load_selected_model(self):
        """Load the selected model from the model list"""
        try:
            # Get the selected model
            selection = self.model_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Model Selected", "Please select a model from the list first.")
                return
            
            model_name = self.model_listbox.get(selection[0])
            
            # Set as current model
            self.current_model = model_name
            
            # Re-initialize the engine
            self.chat_frame.add_message("system", f"Loading model: {model_name}...")
            
            # Reset engine
            if self.engine:
                del self.engine
                self.engine = None
            
            # Load the engine with the new model
            self.load_engine()
            
            # Update status
            self.status_label.config(text=f"Model loaded: {model_name}")
            self.chat_frame.add_message("system", f"Model loaded: {model_name}")
            
        except Exception as e:
            error_msg = f"Error loading model: {str(e)}"
            self.chat_frame.add_message("system", error_msg)
            self.status_label.config(text=error_msg)

    def setup_settings_tab(self):
        """Set up the settings tab"""
        # Theme settings
        self.theme_frame = ttk.LabelFrame(self.settings_tab, text="Theme")
        self.theme_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.theme_var = tk.StringVar(value=self.theme)
        self.theme_light = ttk.Radiobutton(
            self.theme_frame,
            text="Light",
            variable=self.theme_var,
            value="Light",
            command=self.change_theme
        )
        self.theme_light.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.theme_dark = ttk.Radiobutton(
            self.theme_frame,
            text="Dark",
            variable=self.theme_var,
            value="Dark",
            command=self.change_theme
        )
        self.theme_dark.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Paths settings
        self.paths_frame = ttk.LabelFrame(self.settings_tab, text="File Paths")
        self.paths_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Models path
        self.models_path_frame = ttk.Frame(self.paths_frame)
        self.models_path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.models_path_label = ttk.Label(self.models_path_frame, text="Models Path:")
        self.models_path_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.models_path_var = tk.StringVar(value=self.models_path)
        self.models_path_entry = ttk.Entry(self.models_path_frame, textvariable=self.models_path_var, width=40)
        self.models_path_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        self.models_path_button = ttk.Button(
            self.models_path_frame,
            text="Browse",
            command=lambda: self.browse_directory(self.models_path_var)
        )
        self.models_path_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # System info
        self.system_frame = ttk.LabelFrame(self.settings_tab, text="System Information")
        self.system_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Basic system info
        system_info = [
            f"Operating System: {platform.system()} {platform.release()}",
            f"Python Version: {platform.python_version()}",
            f"CPU: {psutil.cpu_count(logical=False)} physical cores, {psutil.cpu_count()} logical cores",
            f"Memory: {psutil.virtual_memory().total / (1024 * 1024 * 1024):.2f} GB total",
            f"Disk: {psutil.disk_usage('/').total / (1024 * 1024 * 1024):.2f} GB total",
            f"USB-AI Version: 1.0.0"
        ]
        
        for i, info in enumerate(system_info):
            ttk.Label(self.system_frame, text=info).pack(anchor=tk.W, padx=10, pady=2)
    
    def load_engine(self):
        """Load the AI engine for the current model"""
        try:
            # Convert model name to lowercase for directory lookup
            model_name_lower = self.current_model.lower().replace(" ", "-")
            model_dir = os.path.join(self.models_path, model_name_lower)
            
            # Special handling for common model names
            if "gemma" in model_name_lower:
                model_dir = os.path.join(self.models_path, "gemma-3-1b-it")
            elif "tiny" in model_name_lower and "llama" in model_name_lower:
                model_dir = os.path.join(self.models_path, "tinyllama-1.1b-chat-v1.0")
            elif "phi-3.5" in model_name_lower:
                model_dir = os.path.join(self.models_path, "phi-3.5-mini-instruct")
            elif "deepseek" in model_name_lower:
                model_dir = os.path.join(self.models_path, "deepseek-coder-6.7b-base")
            
            # Import the ai_engine2 module directly
            sys.path.append(self.base_path)
            from ai_engine2 import USBAIEngine
            
            # Create engine instance with appropriate model path
            self.engine = USBAIEngine(base_path=self.base_path, model_name=os.path.basename(model_dir))
            
            # Log successful engine loading (without using status_bar)
            print(f"Engine loaded: {self.current_model}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to load engine: {str(e)}"
            print(error_msg)  # Print to console instead of status bar
            messagebox.showerror("Engine Error", error_msg)
            return False
    
    def apply_theme(self):
        """Apply the selected theme to the GUI"""
        if self.theme == "Light":
            self.style.theme_use("clam")
            self.style.configure(".", background="#f0f2f5", foreground="#333333")
            self.style.configure("TLabel", background="#f0f2f5", foreground="#333333")
            self.style.configure("TFrame", background="#f0f2f5")
            self.style.configure("TLabelframe", background="#f0f2f5")
            self.style.configure("TLabelframe.Label", background="#f0f2f5", foreground="#333333")
            self.style.configure("TButton", background="#f0f2f5", foreground="#333333")
            # Create accent button style for important actions
            self.style.configure("AccentButton.TButton", background="#1a73e8", foreground="#ffffff")
            self.style.map("AccentButton.TButton", 
                          background=[("active", "#135cbc")],
                          foreground=[("active", "#ffffff")])
        else:  # Dark theme
            self.style.theme_use("clam")
            self.style.configure(".", background="#2c2c2c", foreground="#e0e0e0")
            self.style.configure("TLabel", background="#2c2c2c", foreground="#e0e0e0")
            self.style.configure("TFrame", background="#2c2c2c")
            self.style.configure("TLabelframe", background="#2c2c2c")
            self.style.configure("TLabelframe.Label", background="#2c2c2c", foreground="#e0e0e0")
            self.style.configure("TButton", background="#2c2c2c", foreground="#e0e0e0")
            # Create accent button style for important actions
            self.style.configure("AccentButton.TButton", background="#1a73e8", foreground="#ffffff")
            self.style.map("AccentButton.TButton", 
                          background=[("active", "#135cbc")],
                          foreground=[("active", "#ffffff")])
        
            # Scrollbar colors
            self.style.configure("TScrollbar", background="#2c2c2c", troughcolor="#1e1e1e", 
                               arrowcolor="#e0e0e0", bordercolor="#1e1e1e")
    
    def change_theme(self, event=None):
        """Change the theme"""
        self.theme = self.theme_var.get()
        self.apply_theme()
    
    def change_model(self, new_model):
        """Change the active model"""
        old_model = self.current_model
        self.current_model = new_model
        
        # Update status
        self.status_label.config(text=f"Model: {self.current_model} | Status: Loading...")
        self.root.update_idletasks()
        
        # Try to load the engine
        success = self.load_engine()
        
        if success:
            self.chat_frame.add_message("system", f"Switched to {self.current_model} model.")
            self.status_label.config(text=f"Model: {self.current_model} | Status: Ready")
        else:
            self.current_model = old_model
            self.model_settings.model_var.set(old_model)
            self.status_label.config(text=f"Model: {self.current_model} | Status: Ready")
    
    def browse_directory(self, path_var):
        """Open file dialog to browse for directory"""
        directory = filedialog.askdirectory(initialdir=path_var.get())
        if directory:
            path_var.set(directory)
    
    def update_thinking_animation(self):
        """Update the thinking animation"""
        if not self.thinking:
            self.chat_frame.thinking_label.config(text="")
            return
        
        dots = "..." if self.chat_frame.thinking_label.cget("text").count(".") >= 3 else self.chat_frame.thinking_label.cget("text") + "."
        self.chat_frame.thinking_label.config(text=f"Thinking{dots}")
        self.root.after(500, self.update_thinking_animation)
    
    def process_input(self, user_input):
        """Process the user input using the AI engine"""
        try:
            # Add user message to chat
            self.chat_frame.add_message("user", user_input)
            
            # Disable input controls
            self.root.after(0, lambda: self.disable_input_controls())
            
            # Start thinking animation
            self.thinking = True
            self.update_thinking_animation()
            
            # Process input with AI engine
            if self.engine:
                try:
                    # Get response from AI engine - Note: ai_engine2.py doesn't accept temperature or max_tokens
                    response = self.engine.process_input(user_input)
                    
                    # Display response in GUI thread
                    if response:
                        self.root.after(0, lambda: self.display_response(response))
                    else:
                        self.root.after(0, lambda: self.chat_frame.add_message("system", "No response received from model"))
                
                except Exception as e:
                    # Handle errors
                    error_msg = str(e)
                    self.root.after(0, lambda: self.chat_frame.add_message("system", f"Error: {error_msg}"))
            else:
                self.root.after(0, lambda: self.chat_frame.add_message("system", "No engine loaded"))
            
            # Stop thinking animation
            self.thinking = False
            self.root.after(0, lambda: self.chat_frame.thinking_label.config(text=""))
            
            # Re-enable input controls
            self.root.after(0, lambda: self.enable_input_controls())
            
        except Exception as e:
            # Handle unexpected errors
            self.thinking = False
            self.root.after(0, lambda: self.chat_frame.thinking_label.config(text=""))
            self.root.after(0, lambda: self.chat_frame.add_message("system", f"Unexpected error: {str(e)}"))
            self.root.after(0, lambda: self.enable_input_controls())
            print(f"Error in process_input: {e}")
    
    def disable_input_controls(self):
        """Disable input controls during processing"""
        self.chat_frame.input_text.config(state="disabled")
        self.chat_frame.send_button.config(state="disabled")
        self.chat_frame.clear_button.config(state="disabled")
    
    def enable_input_controls(self):
        """Re-enable input controls after processing"""
        self.chat_frame.input_text.config(state="normal")
        self.chat_frame.send_button.config(state="normal")
        self.chat_frame.clear_button.config(state="normal")
        self.chat_frame.input_text.focus()
    
    def display_response(self, response):
        """Display the AI's response in the chat area"""
        try:
            # Handle emoji characters that might cause encoding issues
            response = response.encode('utf-8', errors='ignore').decode('utf-8')
            self.chat_frame.add_message("ai", response)
        except Exception as e:
            self.chat_frame.add_message("system", f"Error displaying response: {str(e)}")
            print(f"Error displaying response: {e}")
    
    def refresh_models(self):
        """Refresh the model list"""
        # Clear the current list
        self.model_listbox.delete(0, tk.END)
        
        # Check models directory
        if not os.path.exists(self.models_path):
            self.model_listbox.insert(tk.END, "Models directory not found")
            return
        
        # List all model directories
        model_dirs = [d for d in os.listdir(self.models_path) if os.path.isdir(os.path.join(self.models_path, d))]
        if not model_dirs:
            self.model_listbox.insert(tk.END, "No models found")
            return
        
        # Add standard model names
        standard_models = ["Gemma-3-1B-IT", "TinyLLaMA", "Phi-3.5-mini-instruct", "DeepSeek-Coder-6.7B-base"]
        for model_name in standard_models:
            # Check if the model directory exists or a close match
            matching_dirs = [d for d in model_dirs if model_name.lower() in d.lower()]
            if matching_dirs:
                # Model exists in some form, use exact name for consistency
                self.model_listbox.insert(tk.END, model_name)
                # Remove matched directory from the list to avoid duplicates
                for match in matching_dirs:
                    if match in model_dirs:
                        model_dirs.remove(match)
        
        # Add any remaining model directories
        for model_dir in model_dirs:
            self.model_listbox.insert(tk.END, model_dir)
            
        # Select the current model if it's in the list
        for i in range(self.model_listbox.size()):
            if self.model_listbox.get(i) == self.current_model:
                self.model_listbox.selection_set(i)
                self.model_listbox.see(i)
                self.display_model_details()
                break
    
    def organize_models(self):
        """Organize the models using organize_models.py"""
        try:
            # Import the organize_models module
            import sys
            sys.path.append(str(self.base_path))
            
            # Check if organize_models.py exists
            organize_script = os.path.join(self.base_path, "organize_models.py")
            
            if os.path.exists(organize_script):
                # Create a module spec
                spec = importlib.util.spec_from_file_location("organize_models", organize_script)
                organize_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(organize_module)
                
                # Call the organize function
                organize_module.organize(self.models_path)
                
                # Refresh the model list
                self.refresh_models()
                messagebox.showinfo("Models Organized", "Models have been organized successfully.")
            else:
                messagebox.showerror("Error", "organize_models.py script not found.")
        except Exception as e:
            messagebox.showerror("Organization Error", f"Failed to organize models: {e}")
    
    def convert_models(self):
        """Convert models to UAMF format using convert_to_uamf.py"""
        try:
            # Import the convert_to_uamf module
            import sys
            sys.path.append(str(self.base_path))
            
            # Get the path to convert_to_uamf.py
            convert_script = os.path.join(self.base_path, "convert_to_uamf.py")
            
            if os.path.exists(convert_script):
                # Create a module spec
                spec = importlib.util.spec_from_file_location("convert_to_uamf", convert_script)
                convert_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(convert_module)
                
                # Call the convert function (assuming it has a similar interface)
                convert_module.convert(self.models_path)
                
                # Refresh the model list
                self.refresh_models()
                messagebox.showinfo("Models Converted", "Models have been converted to UAMF format successfully.")
            else:
                messagebox.showerror("Error", "convert_to_uamf.py script not found.")
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Failed to convert models: {e}")
    
    def update_system_info(self):
        """Update system information display"""
        try:
            # Get system info
            import platform
            import psutil
            
            system_info = []
            system_info.append(f"OS: {platform.system()} {platform.version()}")
            system_info.append(f"Python: {platform.python_version()}")
            system_info.append(f"CPU: {platform.processor()}")
            
            # Memory information
            mem = psutil.virtual_memory()
            system_info.append(f"RAM: {mem.total / (1024**3):.2f} GB (Used: {mem.percent}%)")
            
            # Disk information
            disk = psutil.disk_usage(self.base_path)
            system_info.append(f"Disk: {disk.total / (1024**3):.2f} GB (Used: {disk.percent}%)")
            
            # USB-AI specific info
            system_info.append("\nUSB-AI Information:")
            system_info.append(f"Base Path: {self.base_path}")
            system_info.append(f"Current Model: {self.current_model}")
            
            # Update text widget
            self.system_text.config(state="normal")
            self.system_text.delete(1.0, tk.END)
            self.system_text.insert(tk.END, "\n".join(system_info))
            self.system_text.config(state="disabled")
            
            # Update memory label
            self.memory_label.config(text=f"Memory: {mem.percent}% used")
            
        except ImportError:
            # psutil might not be available
            self.system_text.config(state="normal")
            self.system_text.delete(1.0, tk.END)
            self.system_text.insert(tk.END, "Install psutil for detailed system information")
            self.system_text.config(state="disabled")
    
    def check_model_status(self):
        """Check the status of downloaded models"""
        # This function periodically checks model status
        try:
            # Check for the required model directories
            required_models = ["microsoft/phi-3.5-mini-instruct", "deepseek-ai/deepseek-coder-6.7b-base"]
            found_models = []
            
            for model_name in required_models:
                model_dir = os.path.join(self.models_path, model_name)
                if os.path.exists(model_dir) and any(os.listdir(model_dir)):
                    found_models.append(model_name)
            
            # Update status based on models found
            if len(found_models) == len(required_models):
                self.status_label.config(text=f"Model: {self.current_model} | Status: All models downloaded")
            elif found_models:
                self.status_label.config(text=f"Model: {self.current_model} | Status: Some models downloaded ({len(found_models)}/{len(required_models)})")
            else:
                self.status_label.config(text=f"Model: {self.current_model} | Status: No required models found")
                
        except Exception as e:
            print(f"Error checking model status: {e}")
            
        # Schedule next check in 30 seconds
        self.root.after(30000, self.check_model_status)

def main():
    """Main function to start the application"""
    root = tk.Tk()
    app = USBAIEnhancedGUI(root)
    
    # Set up window icon
    try:
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.png')
        if os.path.exists(icon_path):
            icon = ImageTk.PhotoImage(file=icon_path)
            root.iconphoto(True, icon)
    except Exception as e:
        print(f"Failed to load icon: {e}")
    
    # Configure grid weights
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    
    # Start the main event loop
    root.mainloop()

if __name__ == "__main__":
    main()
