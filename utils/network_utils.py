"""
Network utilities for managing ports and processes.
"""
import time
import subprocess
import psutil


def kill_process_on_port(port):
    """Kill processes using the specified port, but only if they appear to be our application."""
    try:
        print(f"🔍 Checking for processes on port {port}...")
        killed_any = False
        
        # Known process names that are likely our application
        target_processes = ['uvicorn', 'python', 'python3', 'fastapi']
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'connections']):
            try:
                connections = proc.info['connections']
                if connections:
                    for conn in connections:
                        if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port:
                            proc_name = proc.info['name']
                            cmdline = proc.info['cmdline'] or []
                            cmdline_str = ' '.join(cmdline)
                            
                            # Check if this looks like our application
                            is_our_app = (
                                proc_name.lower() in target_processes or
                                'fastapi_app' in cmdline_str or
                                'start_server.py' in cmdline_str or
                                'uvicorn' in cmdline_str
                            )
                            
                            if is_our_app:
                                print(f"🗑️  Killing our app process: {proc_name} (PID: {proc.info['pid']}) on port {port}")
                                print(f"    Command: {cmdline_str[:100]}{'...' if len(cmdline_str) > 100 else ''}")
                                proc.kill()
                                killed_any = True
                            else:
                                print(f"⚠️  Found process '{proc_name}' (PID: {proc.info['pid']}) on port {port}, but doesn't look like our app")
                                print(f"    Command: {cmdline_str[:100]}{'...' if len(cmdline_str) > 100 else ''}")
                                
                                # Ask user for confirmation for unknown processes
                                response = input(f"    Kill this process? (y/N): ").strip().lower()
                                if response in ['y', 'yes']:
                                    print(f"🗑️  User confirmed - killing process {proc_name} (PID: {proc.info['pid']})")
                                    proc.kill()
                                    killed_any = True
                                else:
                                    print(f"⏭️  Skipping process {proc_name} (PID: {proc.info['pid']})")
                            break
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if killed_any:
            time.sleep(2)  # Wait for processes to fully terminate
            print(f"✅ Port {port} is now free")
        else:
            print(f"✅ Port {port} is already free")
            
    except Exception as e:
        print(f"⚠️  Error checking port {port}: {e}")
        # Try fallback method using lsof with more details
        try:
            print("🔄 Trying fallback method...")
            result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    # Get process info for each PID
                    try:
                        proc = psutil.Process(int(pid))
                        proc_name = proc.name()
                        cmdline = ' '.join(proc.cmdline() or [])
                        
                        print(f"📋 Found process: {proc_name} (PID: {pid})")
                        print(f"    Command: {cmdline[:100]}{'...' if len(cmdline) > 100 else ''}")
                        
                        # Check if it looks like our app
                        is_our_app = (
                            proc_name.lower() in target_processes or
                            'fastapi_app' in cmdline or
                            'start_server.py' in cmdline or
                            'uvicorn' in cmdline
                        )
                        
                        if is_our_app:
                            print(f"🗑️  Killing our app process PID: {pid}")
                            subprocess.run(['kill', '-9', pid])
                        else:
                            response = input(f"    Kill this process? (y/N): ").strip().lower()
                            if response in ['y', 'yes']:
                                print(f"🗑️  User confirmed - killing PID: {pid}")
                                subprocess.run(['kill', '-9', pid])
                            else:
                                print(f"⏭️  Skipping PID: {pid}")
                                
                    except (psutil.NoSuchProcess, ValueError):
                        print(f"⚠️  Could not get info for PID: {pid}, skipping")
                        
                time.sleep(2)
                print(f"✅ Port cleanup completed")
        except Exception as fallback_error:
            print(f"⚠️  Fallback method also failed: {fallback_error}")


def check_port_available(port):
    """Check if a port is available (not in use)."""
    try:
        for proc in psutil.process_iter(['connections']):
            try:
                connections = proc.info['connections']
                if connections:
                    for conn in connections:
                        if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port:
                            return False
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return True
    except Exception:
        # Fallback method
        try:
            result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
            return result.returncode != 0 or not result.stdout.strip()
        except Exception:
            return True  # Assume available if we can't check


def find_free_port(start_port=8000, max_attempts=100):
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if check_port_available(port):
            return port
    return None


def get_processes_on_port(port):
    """Get information about processes using a specific port."""
    processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'connections']):
            try:
                connections = proc.info['connections']
                if connections:
                    for conn in connections:
                        if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port:
                            processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cmdline': ' '.join(proc.info['cmdline'] or [])
                            })
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        print(f"Error getting processes on port {port}: {e}")
    
    return processes
