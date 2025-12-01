#!/usr/bin/env python3
"""
USB-AI Installer
Handles installation and PATH configuration for USB-AI
"""

import os
import sys
import click
import logging
import winreg
import shutil
from typing import Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    filename=os.path.join('logs', 'installer.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('installer')

class USBAIInstaller:
    """Handle USB-AI installation"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.install_dir = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'USB-AI')
        self.scripts_dir = os.path.join(self.install_dir, 'scripts')
        
    def install(self, symlink: bool = True) -> bool:
        """Install USB-AI"""
        try:
            # Create installation directory
            os.makedirs(self.install_dir, exist_ok=True)
            os.makedirs(self.scripts_dir, exist_ok=True)
            
            # Copy or symlink files
            self._install_files(symlink)
            
            # Create command wrapper
            self._create_command_wrapper()
            
            # Add to PATH
            self._add_to_path()
            
            logger.info("USB-AI installation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Installation failed: {str(e)}")
            raise
            
    def uninstall(self) -> bool:
        """Uninstall USB-AI"""
        try:
            # Remove from PATH
            self._remove_from_path()
            
            # Remove installation directory
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir)
                
            logger.info("USB-AI uninstallation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Uninstallation failed: {str(e)}")
            raise
            
    def _install_files(self, symlink: bool):
        """Install USB-AI files"""
        try:
            # Copy/link Python scripts
            src_files = [
                os.path.join(self.base_dir, 'src', 'usbai.py'),
                os.path.join(self.base_dir, 'src', 'convert_to_uamf.py')
            ]
            
            for src in src_files:
                dst = os.path.join(self.scripts_dir, os.path.basename(src))
                if symlink:
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.symlink(src, dst)
                else:
                    shutil.copy2(src, dst)
                    
            logger.info("Files installed successfully")
            
        except Exception as e:
            logger.error(f"Error installing files: {str(e)}")
            raise
            
    def _create_command_wrapper(self):
        """Create command wrapper script"""
        wrapper_path = os.path.join(self.install_dir, 'usbai.cmd')
        
        try:
            with open(wrapper_path, 'w') as f:
                f.write('@echo off\n')
                f.write('python "%~dp0scripts\\usbai.py" %*\n')
                
            logger.info("Command wrapper created successfully")
            
        except Exception as e:
            logger.error(f"Error creating command wrapper: {str(e)}")
            raise
            
    def _add_to_path(self):
        """Add installation directory to PATH"""
        try:
            # Open the registry key for the system PATH
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'System\CurrentControlSet\Control\Session Manager\Environment',
                0,
                winreg.KEY_ALL_ACCESS
            )
            
            # Get current PATH
            path = winreg.QueryValueEx(key, 'Path')[0]
            
            # Add our directory if not already present
            if self.install_dir not in path:
                new_path = f"{path};{self.install_dir}"
                winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
                
            winreg.CloseKey(key)
            logger.info("Added to PATH successfully")
            
        except Exception as e:
            logger.error(f"Error modifying PATH: {str(e)}")
            raise
            
    def _remove_from_path(self):
        """Remove installation directory from PATH"""
        try:
            # Open the registry key for the system PATH
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'System\CurrentControlSet\Control\Session Manager\Environment',
                0,
                winreg.KEY_ALL_ACCESS
            )
            
            # Get current PATH
            path = winreg.QueryValueEx(key, 'Path')[0]
            
            # Remove our directory
            paths = [p for p in path.split(';') if p and p != self.install_dir]
            new_path = ';'.join(paths)
            
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            logger.info("Removed from PATH successfully")
            
        except Exception as e:
            logger.error(f"Error modifying PATH: {str(e)}")
            raise

@click.group()
def cli():
    """USB-AI Installer"""
    pass

@cli.command()
@click.option('--symlink/--no-symlink', default=True,
              help='Use symlinks instead of copying files')
def install(symlink: bool):
    """Install USB-AI"""
    try:
        installer = USBAIInstaller()
        
        click.echo("\nInstalling USB-AI...")
        if installer.install(symlink):
            click.echo("Installation completed successfully!")
            click.echo("\nYou may need to restart your terminal for the PATH changes to take effect.")
        else:
            click.echo("Installation failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error in install command: {str(e)}")
        click.echo(f"Error: {str(e)}")
        sys.exit(1)

@cli.command()
def uninstall():
    """Uninstall USB-AI"""
    try:
        installer = USBAIInstaller()
        
        click.echo("\nUninstalling USB-AI...")
        if installer.uninstall():
            click.echo("Uninstallation completed successfully!")
            click.echo("\nYou may need to restart your terminal for the PATH changes to take effect.")
        else:
            click.echo("Uninstallation failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error in uninstall command: {str(e)}")
        click.echo(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    if not os.name == 'nt':
        click.echo("Error: This installer only supports Windows.")
        sys.exit(1)
    
    if not os.environ.get('PROGRAMFILES'):
        click.echo("Error: Cannot determine Program Files directory.")
        sys.exit(1)
        
    cli()
