#!/usr/bin/env python3
"""
Startup script for the Scholar Bot FastAPI server with ngrok.
This script starts the FastAPI server and optionally exposes it via ngrok.
"""
import os
import subprocess
import sys
import time
import signal
import argparse
from dotenv import load_dotenv
from utils.network_utils import kill_process_on_port

load_dotenv()


def start_ngrok(port=8000):
    """Start ngrok tunnel."""
    # Try using pyngrok first (Python package)
    try:
        from pyngrok import ngrok
        print(f"🌐 Starting ngrok tunnel on port {port} (using pyngrok)...")
        
        # Set auth token if available
        ngrok_authtoken = os.environ.get("NGROK_AUTHTOKEN")
        if ngrok_authtoken:
            ngrok.set_auth_token(ngrok_authtoken)
            print("🔐 Using ngrok auth token for better performance")
        else:
            print("💡 Tip: Set NGROK_AUTHTOKEN for better performance (see MIGRATION.md)")
        
        # Start ngrok tunnel
        public_url = ngrok.connect(port)
        print(f"✅ Public URL: {public_url}")
        print(f"📝 Add this to your Slack app's event subscriptions:")
        print(f"   Events: {public_url}/slack/events")
        print(f"   Interactions: {public_url}/slack/interactions")
        
        # Return a mock process object since pyngrok manages this internally
        class MockProcess:
            def poll(self):
                return None  # Always running
            def terminate(self):
                ngrok.disconnect(public_url)
            def wait(self, timeout=None):
                pass
            def kill(self):
                ngrok.kill()
        
        return MockProcess(), str(public_url)
    
    except ImportError:
        print("📦 pyngrok not available, trying ngrok binary...")
    except Exception as e:
        print(f"⚠️  pyngrok failed: {e}, trying ngrok binary...")
    
    # Fallback to ngrok binary
    try:
        print(f"🌐 Starting ngrok tunnel on port {port} (using binary)...")
        ngrok_process = subprocess.Popen(
            ["ngrok", "http", str(port), "--log=stdout"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for ngrok to start
        time.sleep(3)
        
        # Try to get the public URL
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:4040/api/tunnels"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                import json
                tunnels = json.loads(result.stdout)
                if tunnels.get("tunnels"):
                    public_url = tunnels["tunnels"][0]["public_url"]
                    print(f"✅ Public URL: {public_url}")
                    print(f"📝 Add this to your Slack app's event subscriptions:")
                    print(f"   Events: {public_url}/slack/events")
                    print(f"   Interactions: {public_url}/slack/interactions")
                    return ngrok_process, public_url
        except Exception as e:
            print(f"⚠️  Could not get ngrok URL automatically: {e}")
            print("🔍 Check http://localhost:4040 for the ngrok dashboard")
        
        return ngrok_process, None
        
    except FileNotFoundError:
        print("❌ ngrok not found. Please install ngrok first:")
        print("   Option 1 (pip): pip install pyngrok")
        print("   Option 2 (binary): https://ngrok.com/download")
        return None, None
    except Exception as e:
        print(f"❌ Error starting ngrok: {e}")
        return None, None


def start_uvicorn(port=8000, reload=False):
    """Start the FastAPI server with uvicorn."""
    print(f"🚀 Starting FastAPI server on port {port}...")
    
    cmd = ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", str(port)]
    if reload:
        cmd.append("--reload")
    
    try:
        return subprocess.Popen(cmd)
    except FileNotFoundError:
        print("❌ uvicorn not found. Please install it:")
        print("   pip install uvicorn")
        return None


def main():
    parser = argparse.ArgumentParser(description="Start Scholar Bot FastAPI server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--no-ngrok", action="store_true", help="Don't start ngrok tunnel")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    processes = []
    
    try:
        # Kill any existing processes on the port
        kill_process_on_port(args.port)
        
        # Start uvicorn server
        uvicorn_process = start_uvicorn(args.port, args.reload)
        if not uvicorn_process:
            return 1
        processes.append(uvicorn_process)
        
        # Start ngrok if requested
        ngrok_process = None
        if not args.no_ngrok:
            ngrok_process, public_url = start_ngrok(args.port)
            if ngrok_process:
                processes.append(ngrok_process)
        
        print("\n" + "="*60)
        print("🎉 Scholar Bot is running!")
        print(f"📍 Local server: http://localhost:{args.port}")
        print(f"📊 Health check: http://localhost:{args.port}/health")
        if not args.no_ngrok and ngrok_process:
            print(f"🌐 ngrok dashboard: http://localhost:4040")
        print("="*60)
        print("\n💡 Tips:")
        print("  - Press Ctrl+C to stop all services")
        print("  - Update your Slack app's URLs to point to the ngrok tunnel")
        print("  - Check the README for environment variable setup")
        print("\n⏳ Waiting for requests...")
        
        # Wait for processes
        while True:
            # Check if any process has died
            for i, process in enumerate(processes):
                if process.poll() is not None:
                    print(f"\n❌ Process {i} has exited with code {process.returncode}")
                    return process.returncode
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⏰ Force killing process...")
                process.kill()
            except Exception as e:
                print(f"⚠️  Error stopping process: {e}")
        
        print("✅ All services stopped")
        return 0
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
