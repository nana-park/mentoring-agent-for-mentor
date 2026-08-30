"""Local batch schedule. Importing this module never starts the scheduler."""
import datetime
import json
import os
import subprocess
import time
from mentoring.config import AUTOMATION_CONFIG_FILE, PROJECT_ROOT
from mentoring.web.processes import active_processes, pipeline_command

BASE_DIR = PROJECT_ROOT

CONFIG_FILE = AUTOMATION_CONFIG_FILE

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"enabled": False, "frequency": "daily", "time": "09:00", "day": "Monday"}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def scheduler_loop():
    while True:
        try:
            config = load_config()
            if config.get("enabled"):
                now = datetime.datetime.now()
                target_time_str = config.get("time", "09:00")
                if target_time_str:
                    target_hour, target_minute = map(int, target_time_str.split(':'))
                    is_time_match = (now.hour == target_hour and now.minute == target_minute)

                    is_day_match = True
                    if config.get("frequency") == "weekly":
                        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                        target_day = config.get("day", "Monday")
                        if days[now.weekday()] != target_day:
                            is_day_match = False

                    if is_time_match and is_day_match:
                        if "batch" not in active_processes or active_processes["batch"].poll() is not None:
                            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Automation triggered! Running batch mode in background...")
                            proc = subprocess.Popen(
                                pipeline_command("batch"),
                                cwd=BASE_DIR,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            active_processes["batch"] = proc
        except Exception as e:
            print(f"Scheduler error: {e}")

        now = datetime.datetime.now()
        sleep_time = 60 - now.second
        time.sleep(sleep_time)
