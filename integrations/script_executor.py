# -*- coding: utf-8 -*-
"""
Script Execution Environment
Phase 5.1: PowerShell, Batch, and Python script execution
"""

import logging
import subprocess
import platform
import os
import sys
from typing import Optional, Dict, Tuple, List
from pathlib import Path
import tempfile


class ScriptExecutor:
    """
    Executes PowerShell, Batch, and Python scripts.
    """
    
    def __init__(self):
        """Initialize Script Executor."""
        if platform.system() != 'Windows':
            logging.warning("Script executor optimized for Windows")
    
    def execute_powershell(self, script: str, parameters: Optional[Dict] = None,
                          as_file: bool = False, timeout: int = 300) -> Tuple[bool, str, str]:
        """
        Execute PowerShell script.
        
        Args:
            script: PowerShell script content or file path
            parameters: Optional parameters to pass
            as_file: If True, treat script as file path
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if as_file:
                script_path = script
                if not os.path.exists(script_path):
                    return False, "", f"Script file not found: {script_path}"
            else:
                # Create temporary script file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as f:
                    f.write(script)
                    script_path = f.name
            
            try:
                # Build PowerShell command
                cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path]
                
                # Add parameters if provided
                if parameters:
                    for key, value in parameters.items():
                        cmd.extend([f"-{key}", str(value)])
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                success = result.returncode == 0
                return success, result.stdout, result.stderr
                
            finally:
                # Clean up temporary file if we created it
                if not as_file and os.path.exists(script_path):
                    try:
                        os.unlink(script_path)
                    except:
                        pass
                        
        except subprocess.TimeoutExpired:
            return False, "", "Script execution timeout"
        except Exception:
            logging.exception("Failed to execute PowerShell script")
            return False, "", "Failed to execute PowerShell script"
    
    def execute_batch(self, script: str, parameters: Optional[Dict] = None,
                     as_file: bool = False, timeout: int = 300) -> Tuple[bool, str, str]:
        """
        Execute Batch script.
        
        Args:
            script: Batch script content or file path
            parameters: Optional parameters (passed as environment variables)
            as_file: If True, treat script as file path
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if as_file:
                script_path = script
                if not os.path.exists(script_path):
                    return False, "", f"Script file not found: {script_path}"
            else:
                # Create temporary script file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False) as f:
                    f.write(script)
                    script_path = f.name
            
            try:
                # Build command
                cmd = [script_path]
                
                # Set environment variables for parameters
                env = os.environ.copy()
                if parameters:
                    for key, value in parameters.items():
                        env[f"PARAM_{key}"] = str(value)
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='ignore',
                    env=env,
                    shell=True
                )
                
                success = result.returncode == 0
                return success, result.stdout, result.stderr
                
            finally:
                # Clean up temporary file if we created it
                if not as_file and os.path.exists(script_path):
                    try:
                        os.unlink(script_path)
                    except:
                        pass
                        
        except subprocess.TimeoutExpired:
            return False, "", "Script execution timeout"
        except Exception:
            logging.exception("Failed to execute Batch script")
            return False, "", "Failed to execute Batch script"
    
    def execute_python(self, script: str, parameters: Optional[Dict] = None,
                      as_file: bool = False, timeout: int = 300) -> Tuple[bool, str, str]:
        """
        Execute Python script.
        
        Args:
            script: Python script content or file path
            parameters: Optional parameters (passed as script arguments or environment)
            as_file: If True, treat script as file path
            timeout: Execution timeout in seconds
            use_current_env: If True, use current Python environment
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if as_file:
                script_path = script
                if not os.path.exists(script_path):
                    return False, "", f"Script file not found: {script_path}"
            else:
                # Create temporary script file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(script)
                    script_path = f.name
            
            try:
                # Build Python command
                python_exe = sys.executable
                cmd = [python_exe, script_path]
                
                # Add parameters as command-line arguments
                if parameters:
                    for key, value in parameters.items():
                        cmd.extend([f"--{key}", str(value)])
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                success = result.returncode == 0
                return success, result.stdout, result.stderr
                
            finally:
                # Clean up temporary file if we created it
                if not as_file and os.path.exists(script_path):
                    try:
                        os.unlink(script_path)
                    except:
                        pass
                        
        except subprocess.TimeoutExpired:
            return False, "", "Script execution timeout"
        except Exception:
            logging.exception("Failed to execute Python script")
            return False, "", "Failed to execute Python script"
    
    def execute_command(self, command: str, shell: bool = True,
                       timeout: int = 60) -> Tuple[bool, str, str]:
        """
        Execute a generic shell command.
        
        Args:
            command: Command to execute
            shell: Use shell execution
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='ignore'
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Command execution timeout"
        except Exception:
            logging.exception("Failed to execute command")
            return False, "", "Failed to execute command"