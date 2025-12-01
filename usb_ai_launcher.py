#!/usr/bin/env python
# File: usb_ai_launcher.py - Main launcher for the USB-AI project

import os
import sys
import logging
import argparse
from pathlib import Path

# Setup core paths
BASE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
LOGS_PATH = BASE_PATH / "logs"
MODELS_PATH = BASE_PATH / "models"

# Ensure directories exist
LOGS_PATH.mkdir(parents=True, exist_ok=True)
MODELS_PATH.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=str(LOGS_PATH / "usb_ai.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def setup_environment():
    """Setup the necessary environment for USB-AI"""
    # Add the parent directory to sys.path to ensure imports work
    sys.path.append(str(BASE_PATH))
    
    # Suppress HF warnings
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    
    # Set PyTorch threads to avoid CPU overload
    try:
        import torch
        # Allow configuring thread count via environment variable `USBAI_NUM_THREADS`.
        # If not set, default to the machine's logical CPU count. We no longer
        # artificially cap the requested value here; the effective number of
        # threads will ultimately be determined by the OS/PyTorch runtime.
        num_cores = os.cpu_count() or 4
        env_threads = os.environ.get("USBAI_NUM_THREADS")
        if env_threads:
            try:
                desired = int(env_threads)
            except ValueError:
                desired = num_cores
        else:
            desired = num_cores

        num_threads = max(1, desired)

        # Align native BLAS/OpenMP thread environment variables with the requested threads.
        # Set these before PyTorch spawns internal threads so native libraries respect them.
        os.environ.setdefault("OMP_NUM_THREADS", str(num_threads))
        os.environ.setdefault("MKL_NUM_THREADS", str(num_threads))
        os.environ.setdefault("OPENBLAS_NUM_THREADS", str(num_threads))

        # Now import torch and set the python-level thread count.
        import torch
        torch.set_num_threads(num_threads)
        logging.info(f"PyTorch threads set to {num_threads} (requested={desired}, cpu_count={num_cores})")
    except ImportError:
        logging.warning("PyTorch not found, skipping thread limitation")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="USB-AI - Offline AI on a USB drive")
    
    # Interface selection
    parser.add_argument("--interface", "-i", choices=["cli", "gui", "voice"], default="gui",
                      help="Interface to use (default: gui)")
    
    # Model selection
    parser.add_argument("--model", "-m", default="Gemma-3-1B-IT",
                      help="Model to use (default: Gemma-3-1B-IT)")
    
    # Debug mode
    parser.add_argument("--debug", "-d", action="store_true",
                      help="Enable debug mode with more verbose output")
    
    return parser.parse_args()

def start_interface(interface_type, model_name, debug=False):
    """Start the specified interface with the specified model"""
    logging.info(f"Starting {interface_type} interface with model {model_name}")
    
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug mode enabled")
    
    try:
        if interface_type == "gui":
            # Start the enhanced GUI
            from ui.enhanced_gui import main as gui_main
            gui_main()
        
        elif interface_type == "cli":
            # Start the CLI interface
            from ui.cli import start as cli_start
            
            # Choose the appropriate engine based on model name
            if model_name.lower() in ["gemma-3-1b-it", "phi-3.5-mini-instruct", "deepseek-coder-6.7b-base"]:
                from ai_engine2 import USBAIEngine
            else:
                from ai_engine import USBAIEngine
                
            engine = USBAIEngine(base_path=str(BASE_PATH), model_name=model_name.lower())
            cli_start(engine)
        
        elif interface_type == "voice":
            # Start the voice interface
            from ui.voice import start as voice_start
            
            # Choose the appropriate engine based on model name
            if model_name.lower() in ["gemma-3-1b-it", "phi-3.5-mini-instruct", "deepseek-coder-6.7b-base"]:
                from ai_engine2 import USBAIEngine
            else:
                from ai_engine import USBAIEngine
                
            engine = USBAIEngine(base_path=str(BASE_PATH), model_name=model_name.lower())
            voice_start(engine)
    
    except ImportError as e:
        logging.error(f"Failed to import required module: {e}")
        print(f"Error: Failed to import required module: {e}")
        print("Make sure all dependencies are installed by running: pip install -r requirements.txt")
        sys.exit(1)
    
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)

def main():
    """Main entry point for the USB-AI application"""
    # Setup environment
    setup_environment()
    
    # Parse command line arguments
    args = parse_arguments()
    
    print("USB-AI Launcher - Offline AI on a USB drive")
    print(f"Starting with interface: {args.interface}, model: {args.model}")
    
    # Start the specified interface
    start_interface(args.interface, args.model, args.debug)

if __name__ == "__main__":
    main()
