"""
Scheduler for periodic tasks like fingerprint cleanup
Runs every Friday at 18h55
"""

import threading
import time
from datetime import datetime, timedelta


class WeeklyScheduler:
    """Simple scheduler that runs a task every Friday at a specific time"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.tasks = []
    
    def add_task(self, func, day_of_week: int, hour: int, minute: int, name: str = "task"):
        """
        Add a weekly task.
        day_of_week: 0=Monday, 4=Friday, 6=Sunday
        """
        self.tasks.append({
            'func': func,
            'day': day_of_week,
            'hour': hour,
            'minute': minute,
            'name': name
        })
        print(f"[Scheduler] Added task '{name}' for day {day_of_week} at {hour:02d}:{minute:02d}")
    
    def _get_next_run(self, day: int, hour: int, minute: int) -> datetime:
        """Calculate the next run time for a task"""
        now = datetime.now()
        
        # Find next occurrence of the target day/time
        days_ahead = day - now.weekday()
        if days_ahead < 0:  # Target day already passed this week
            days_ahead += 7
        
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        next_run += timedelta(days=days_ahead)
        
        # If we're past the time today and it's the target day, go to next week
        if next_run <= now:
            next_run += timedelta(weeks=1)
        
        return next_run
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        print("[Scheduler] Started")
        
        while self.running:
            now = datetime.now()
            
            for task in self.tasks:
                next_run = self._get_next_run(task['day'], task['hour'], task['minute'])
                time_until = (next_run - now).total_seconds()
                
                # Check if it's time to run (within 60 seconds window)
                if time_until <= 60 and time_until > 0:
                    print(f"[Scheduler] Running task '{task['name']}'")
                    try:
                        task['func']()
                    except Exception as e:
                        print(f"[Scheduler] Error in task '{task['name']}': {e}")
                    # Sleep for 2 minutes to avoid running again
                    time.sleep(120)
                    break
            
            # Sleep for 30 seconds before checking again
            time.sleep(30)
        
        print("[Scheduler] Stopped")
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)


# Global scheduler instance
scheduler = WeeklyScheduler()


def setup_scheduled_tasks():
    """Setup all scheduled tasks"""
    from services.counter_service import get_counter_service
    
    # Cleanup fingerprints every Friday at 18h55
    scheduler.add_task(
        func=lambda: get_counter_service().cleanup_old_fingerprints(days_old=7),
        day_of_week=4,  # Friday
        hour=18,
        minute=55,
        name="fingerprint_cleanup"
    )
    
    # Start the scheduler
    scheduler.start()
    print("[Scheduler] Scheduled tasks initialized")
