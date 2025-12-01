# USB-AI

A portable, offline AI assistant that runs directly from your USB drive.

## Quick Start

1. Insert the USB drive (should mount as E:)
2. Run `python usb_ai_launcher.py` or `python main.py` to initialize the environment
3. Choose your interface:
   - CLI: Command line interface
   - GUI: Graphical user interface (recommended)
   - Voice: Voice-activated interface

## Current Model Status

⚠️ **Important Notice**: Currently, only the **Gemma-3-1B-IT** model is fully functional and working properly.

### Working Models:
- ✅ **Gemma-3-1B-IT** - Fully operational and recommended for use

### Models Under Development:
- 🔧 **TinyLLaMA** - Not fully functional yet
- 🔧 **DeepSeek-Coder-6.7B** - Not fully functional yet

**Recommendation**: Use the Gemma-3-1B-IT model for the best experience until other models are fully implemented.

## Features

- Offline operation with Gemma-3-1B-IT model
- Multiple interface options (CLI, GUI, Voice)
- Advanced AI engine with optimized generation
- Mathematical expression evaluation
- Code generation and assistance
- Secure operation with proper authentication
- Memory-efficient model loading
- Cross-platform compatibility (Windows primary)

## Requirements

- Windows OS (primary support)
- 8GB RAM minimum (16GB recommended for optimal performance)
- Python 3.8+ (Python 3.13 recommended)
- At least 10GB free storage space
- CUDA-compatible GPU (optional, for faster inference)

## Installation

1. Clone or download this repository to your USB drive
2. Install dependencies: `pip install -r requirements.txt`
3. Run the launcher: `python usb_ai_launcher.py`

## Usage

### GUI Interface (Recommended)
```bash
python usb_ai_launcher.py --interface gui
```

### CLI Interface
```bash
python usb_ai_launcher.py --interface cli
```

### Voice Interface
```bash
python usb_ai_launcher.py --interface voice
```

## Troubleshooting

- If you encounter model loading issues, ensure you're using the Gemma-3-1B-IT model
- For memory issues, try running on a system with 16GB+ RAM
- Check the logs folder for detailed error information
