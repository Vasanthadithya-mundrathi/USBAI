#!/usr/bin/env python
# File: main.py - Main entry point for the USB-AI project

import sys
import os
from pathlib import Path

def main():
    """Main entry point that launches the USB-AI application"""
    # Get the base path
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Ensure we're using the correct python interpreter and paths
    sys.path.insert(0, base_path)
    
    # Launch the application using the launcher
    from usb_ai_launcher import main as launcher_main
    launcher_main()

if __name__ == "__main__":
    main()
