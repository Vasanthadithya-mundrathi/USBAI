#!/usr/bin/env python3
"""
USB-AI - Offline AI Assistant
Main CLI interface for interacting with USB-AI system.
"""

import os
import sys
import click
import logging
from typing import Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename=os.path.join('logs', 'usbai.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('usbai')

class USBAI:
    """Main USB-AI system class"""
    
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        self.active_model = None
        self.session_active = False
        
    def get_available_models(self) -> list:
        """Get list of available models"""
        try:
            return [d for d in os.listdir(self.models_dir) 
                   if os.path.isdir(os.path.join(self.models_dir, d))]
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            return []
            
    def get_system_status(self) -> dict:
        """Get current system status"""
        return {
            'active_model': self.active_model,
            'session_active': self.session_active,
            'models_available': len(self.get_available_models()),
            'timestamp': datetime.now().isoformat()
        }

# CLI Commands
@click.group()
def cli():
    """USB-AI - Offline AI Assistant"""
    pass

@cli.command()
def status():
    """Show current USB-AI status"""
    try:
        usbai = USBAI()
        status = usbai.get_system_status()
        click.echo("\nUSB-AI Status:")
        click.echo("--------------")
        click.echo(f"Active Model: {status['active_model'] or 'None'}")
        click.echo(f"Session Active: {'Yes' if status['session_active'] else 'No'}")
        click.echo(f"Models Available: {status['models_available']}")
        click.echo(f"Timestamp: {status['timestamp']}\n")
    except Exception as e:
        logger.error(f"Error in status command: {str(e)}")
        click.echo(f"Error: {str(e)}")

@cli.command()
def list():
    """List available models"""
    try:
        usbai = USBAI()
        models = usbai.get_available_models()
        
        if not models:
            click.echo("\nNo models available.")
            return
            
        click.echo("\nAvailable Models:")
        click.echo("----------------")
        for model in models:
            click.echo(f"- {model}")
        click.echo()
    except Exception as e:
        logger.error(f"Error in list command: {str(e)}")
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.option('--model', help='Model to use (default: auto-select)')
def run(model: Optional[str]):
    """Start interactive session"""
    try:
        usbai = USBAI()
        
        # Auto-select model if none specified
        if not model:
            models = usbai.get_available_models()
            if not models:
                click.echo("Error: No models available")
                return
            model = models[0]
            click.echo(f"Auto-selected model: {model}")
            
        click.echo(f"\nStarting USB-AI session with model: {model}")
        click.echo("Type 'exit' or 'quit' to end session")
        click.echo("-" * 50)
        
        # Start interactive loop
        while True:
            try:
                user_input = click.prompt('User')
                
                if user_input.lower() in ['exit', 'quit']:
                    click.echo("\nEnding session...")
                    break
                    
                # TODO: Implement actual model inference
                click.echo(f"Assistant: Processing '{user_input}'...")
                
            except click.Abort:
                click.echo("\nSession aborted.")
                break
                
    except Exception as e:
        logger.error(f"Error in run command: {str(e)}")
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.argument('model_name')
@click.option('--force', is_flag=True, help='Force redownload')
def download(model_name: str, force: bool):
    """Download a model"""
    try:
        click.echo(f"\nDownloading model: {model_name}")
        click.echo("(Download functionality to be implemented)")
        # TODO: Implement model downloading
    except Exception as e:
        logger.error(f"Error in download command: {str(e)}")
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.argument('model_name')
def show(model_name: str):
    """Show model details"""
    try:
        usbai = USBAI()
        models = usbai.get_available_models()
        
        if model_name not in models:
            click.echo(f"Error: Model '{model_name}' not found")
            return
            
        click.echo(f"\nDetails for model: {model_name}")
        click.echo("(Model details functionality to be implemented)")
        # TODO: Implement model details display
    except Exception as e:
        logger.error(f"Error in show command: {str(e)}")
        click.echo(f"Error: {str(e)}")

@cli.command()
def stop():
    """Stop active session"""
    try:
        click.echo("\nStopping USB-AI session...")
        # TODO: Implement session cleanup
    except Exception as e:
        logger.error(f"Error in stop command: {str(e)}")
        click.echo(f"Error: {str(e)}")

@cli.command()
def help():
    """Show detailed help"""
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    click.echo("\nFor more information, see documentation.")

if __name__ == '__main__':
    try:
        cli()
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        click.echo(f"Critical error: {str(e)}")
        sys.exit(1)
