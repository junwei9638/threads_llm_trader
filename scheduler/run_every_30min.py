import time
import subprocess
import os

def run_loop():
    print("Starting Threads LLM Trader Loop...")
    
    while True:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting iteration...")
        
        try:
            # Step 1: Fetch posts
            print("Step 1: Fetching posts...")
            subprocess.run(["python3", "crawler/threads_fetch.py"], check=True)
            
            # Step 2: Analyze posts
            print("Step 2: Analyzing posts...")
            subprocess.run(["python3", "llm/gemini_analyzer.py"], check=True)
            
            # Step 3: Run simulation
            print("Step 3: Running simulation...")
            subprocess.run(["python3", "simulator/paper_trader.py"], check=True)
            
            print("Iteration complete. Sleeping for 30 minutes...")
            time.sleep(1800)
            
        except subprocess.CalledProcessError as e:
            print(f"Error during iteration: {e}")
            print("Retrying in 1 minute...")
            time.sleep(60)
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_loop()
