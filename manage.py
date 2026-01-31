import sys
import subprocess
import os
import time

def run_command(command, description):
    print(f"🚀 {description}...")
    try:
        # Use shell=True for Windows compatibility with complex commands
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped {description}.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py [command]")
        print("Commands:")
        print("  start      -> Run the Trading Bot")
        print("  ml         -> Run the ML Server")
        print("  diag       -> Run System Diagnostics")
        print("  backtest   -> Run Backtests")
        print("  clean      -> Remove __pycache__ and temp files")
        print("  install    -> Install dependencies")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "start":
        # Check if ML server is likely running (optional check could be added here)
        run_command("python -m app.main", "Starting Trading Bot")
    
    elif cmd == "ml":
        run_command("uvicorn ml.server:app --reload --port 8000", "Starting ML Advisor Server")
    
    elif cmd == "diag":
        run_command("python -m app.diagnostics", "Running Diagnostics")
        
    elif cmd == "backtest":
        run_command("python -m app.backtest_runner", "Running Backtests")
        
    elif cmd == "clean":
        print("🧹 Cleaning up...")
        if os.name == 'nt':
            subprocess.run("del /s /q __pycache__", shell=True)
            subprocess.run("del /s /q *.pyc", shell=True)
        else:
            subprocess.run("find . -type d -name __pycache__ -exec rm -r {} +", shell=True)
            subprocess.run("find . -name '*.pyc' -delete", shell=True)
        print("✅ Clean complete.")
        
    elif cmd == "install":
        run_command("pip install -r requirements.txt", "Installing Dependencies")
        
    else:
        print(f"❌ Unknown command: {cmd}")

if __name__ == "__main__":
    main()
