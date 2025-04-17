import random
from datetime import datetime, time, timedelta
import json
import os

class WatchDataManager:
    def __init__(self, user_name="Samantha"):
        self.user_name = user_name
        self.data_file = f"watch_data_{user_name.lower()}.json"
        self.watch_data = self._load_data()
        self.last_checked_time = None
        self.daily_routine = {
            "wake_up": time(6, 0),       # 6:00 AM
            "breakfast": time(7, 30),    # 7:30 AM
            "lunch": time(12, 30),       # 12:30 PM
            "dinner": time(19, 0),       # 7:00 PM
            "bedtime": time(22, 0)       # 10:00 PM
        }
        self.meal_reminders = {
            "breakfast": False,
            "lunch": False,
            "dinner": False
        }
    
    def _load_data(self):
        """Load watch data from file or create new if doesn't exist"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return self._initialize_data()
        else:
            return self._initialize_data()
    
    def _initialize_data(self):
        """Initialize empty watch data structure"""
        return {
            "sleep": {
                "last_sleep_time": None,
                "wake_up_time": None,
                "duration": "0",
                "quality": "unknown",
                "deep_sleep_percentage": 0,
                "rem_sleep_percentage": 0,
                "light_sleep_percentage": 0,
                "awake_periods": 0
            },
            "heart_rate": {
                "readings": [],
                "resting": 65,
                "current": 65,
                "trend": "stable",
                "min_today": 65,
                "max_today": 65
            },
            "activity": {
                "steps": 0,
                "active_minutes": 0,
                "sedentary_minutes": 0,
                "calories_burned": 0
            },
            "glucose": {
                "readings": [],
                "current": 100,
                "trend": "stable",
                "min_today": 100,
                "max_today": 100
            },
            "meals": {
                "breakfast": None,
                "lunch": None, 
                "dinner": None,
                "snacks": []
            },
            "water_intake_ml": 0,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _save_data(self):
        """Save watch data to file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.watch_data, f, indent=2)
    
    def simulate_sleep_data(self, wake_up=False):
        """Simulate or update sleep data"""
        now = datetime.now()
        
        # If this is a wake-up event
        if wake_up:
            # Calculate sleep duration from last_sleep_time
            if self.watch_data["sleep"]["last_sleep_time"]:
                sleep_time = datetime.strptime(self.watch_data["sleep"]["last_sleep_time"], "%Y-%m-%d %H:%M:%S")
                duration_minutes = (now - sleep_time).total_seconds() / 60
                hours = int(duration_minutes / 60)
                mins = int(duration_minutes % 60)
                
                # Simulate sleep quality metrics
                deep_sleep = random.randint(15, 30)  # Percentage
                rem_sleep = random.randint(15, 25)   # Percentage
                light_sleep = 100 - deep_sleep - rem_sleep
                awake_periods = random.randint(1, 5)
                
                # Determine sleep quality
                if deep_sleep > 25 and rem_sleep > 20 and awake_periods < 3:
                    quality = "Excellent"
                elif deep_sleep > 20 and rem_sleep > 18 and awake_periods < 4:
                    quality = "Good"
                elif deep_sleep > 15 and rem_sleep > 15:
                    quality = "Fair"
                else:
                    quality = "Poor"
                
                # Update sleep data
                self.watch_data["sleep"].update({
                    "wake_up_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration": f"{hours} hours {mins} minutes",
                    "quality": quality,
                    "deep_sleep_percentage": deep_sleep,
                    "rem_sleep_percentage": rem_sleep,
                    "light_sleep_percentage": light_sleep,
                    "awake_periods": awake_periods
                })
            
            # Set heart rate for morning
            hr = random.randint(65, 75)
            self.watch_data["heart_rate"].update({
                "current": hr,
                "trend": "rising",
                "readings": self.watch_data["heart_rate"]["readings"] + [
                    {"time": now.strftime("%H:%M"), "value": hr}
                ]
            })
            
            # Reset steps for new day if needed
            current_date = now.strftime("%Y-%m-%d")
            if self.watch_data["last_update"].split()[0] != current_date:
                self.watch_data["activity"]["steps"] = 0
                self.watch_data["activity"]["active_minutes"] = 0
                self.watch_data["activity"]["sedentary_minutes"] = 0
                self.watch_data["activity"]["calories_burned"] = 0
                self.watch_data["water_intake_ml"] = 0
                self.meal_reminders = {key: False for key in self.meal_reminders}
            
            self.watch_data["last_update"] = now.strftime("%Y-%m-%d %H:%M:%S")
            self._save_data()
            
            return self.get_morning_summary()
        else:
            # Record sleep start time
            self.watch_data["sleep"]["last_sleep_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
            self.watch_data["last_update"] = now.strftime("%Y-%m-%d %H:%M:%S")
            self._save_data()
            return None
    
    def update_heart_rate(self):
        """Simulate heart rate updates based on time of day and activity"""
        now = datetime.now()
        hour = now.hour
        current = self.watch_data["heart_rate"]["current"]
        
        # Simulate heart rate based on time of day
        if 5 <= hour < 8:  # Morning, waking up
            new_hr = random.randint(65, 75)
            trend = "rising"
        elif 8 <= hour < 12:  # Morning work
            new_hr = random.randint(70, 85)
            trend = "stable"
        elif 12 <= hour < 14:  # Lunch time
            new_hr = random.randint(75, 90)
            trend = "elevated"
        elif 14 <= hour < 18:  # Afternoon work
            new_hr = random.randint(70, 85)
            trend = "stable"
        elif 18 <= hour < 22:  # Evening
            new_hr = random.randint(65, 80)
            trend = "decreasing"
        else:  # Night
            new_hr = random.randint(60, 70)
            trend = "low (resting)"
        
        # Add some randomness
        new_hr = max(50, min(120, new_hr + random.randint(-5, 5)))
        
        # Update readings and stats
        self.watch_data["heart_rate"]["readings"].append({
            "time": now.strftime("%H:%M"), 
            "value": new_hr
        })
        
        # Keep only the last 24 readings
        if len(self.watch_data["heart_rate"]["readings"]) > 24:
            self.watch_data["heart_rate"]["readings"] = self.watch_data["heart_rate"]["readings"][-24:]
        
        self.watch_data["heart_rate"]["current"] = new_hr
        self.watch_data["heart_rate"]["trend"] = trend
        self.watch_data["heart_rate"]["min_today"] = min(
            self.watch_data["heart_rate"]["min_today"], 
            new_hr
        )
        self.watch_data["heart_rate"]["max_today"] = max(
            self.watch_data["heart_rate"]["max_today"], 
            new_hr
        )
        
        self.watch_data["last_update"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self._save_data()
        
        return new_hr, trend
    
    def update_steps(self, active=True):
        """Update step count and activity data"""
        now = datetime.now()
        hour = now.hour
        
        # Determine step increase based on time and activity level
        if active:
            if 6 <= hour < 9:  # Morning activity
                new_steps = random.randint(500, 1500)
                active_mins = random.randint(5, 15)
            elif 12 <= hour < 14:  # Lunch walk
                new_steps = random.randint(800, 2000)
                active_mins = random.randint(10, 20)
            elif 17 <= hour < 20:  # Evening activity
                new_steps = random.randint(1000, 3000)
                active_mins = random.randint(15, 30)
            else:
                new_steps = random.randint(300, 800)
                active_mins = random.randint(3, 8)
            sedentary_mins = 0
        else:
            # Minimal activity
            new_steps = random.randint(50, 200)
            active_mins = 0
            # Add sedentary time
            sedentary_mins = random.randint(25, 60)
        
        # Update activity metrics
        self.watch_data["activity"]["steps"] += new_steps
        self.watch_data["activity"]["active_minutes"] += active_mins
        self.watch_data["activity"]["sedentary_minutes"] += sedentary_mins
        
        # Calculate calories (very rough estimate - ~0.04 calories per step)
        new_calories = int(new_steps * 0.04)
        self.watch_data["activity"]["calories_burned"] += new_calories
        
        self.watch_data["last_update"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self._save_data()
        
        return {
            "steps": self.watch_data["activity"]["steps"],
            "active_minutes": self.watch_data["activity"]["active_minutes"],
            "sedentary_minutes": self.watch_data["activity"]["sedentary_minutes"],
            "calories_burned": self.watch_data["activity"]["calories_burned"]
        }
    
    def update_glucose(self, manual_value=None):
        """Simulate or record blood glucose readings"""
        now = datetime.now()
        hour = now.hour
        
        if manual_value:
            # User provided a measurement
            glucose = manual_value
        else:
            # Simulate based on time of day and meals
            last_meal = None
            for meal_type, meal_time in self.daily_routine.items():
                if meal_type in self.watch_data["meals"] and self.watch_data["meals"][meal_type]:
                    meal_datetime = datetime.strptime(self.watch_data["meals"][meal_type]["time"], "%Y-%m-%d %H:%M:%S")
                    if now - meal_datetime < timedelta(hours=3):
                        last_meal = meal_type
                        time_since_meal = (now - meal_datetime).total_seconds() / 60
                        break
            
            # Base glucose level
            base_glucose = 100
            
            # Adjust based on time since last meal
            if last_meal:
                if time_since_meal < 30:
                    # Rising after meal
                    glucose = base_glucose + random.randint(20, 40)
                elif time_since_meal < 90:
                    # Peak after meal
                    glucose = base_glucose + random.randint(30, 50)
                else:
                    # Coming down
                    glucose = base_glucose + random.randint(10, 25)
            elif 5 <= hour < 8:
                # Morning glucose (dawn phenomenon)
                glucose = base_glucose + random.randint(5, 15)
            else:
                # Regular glucose
                glucose = base_glucose + random.randint(-10, 10)
        
        # Determine trend by comparing to previous reading
        if len(self.watch_data["glucose"]["readings"]) > 0:
            last_glucose = self.watch_data["glucose"]["readings"][-1]["value"]
            if glucose > last_glucose + 10:
                trend = "rising"
            elif glucose < last_glucose - 10:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Update glucose data
        self.watch_data["glucose"]["readings"].append({
            "time": now.strftime("%H:%M"),
            "value": glucose
        })
        
        # Keep only the last 10 readings
        if len(self.watch_data["glucose"]["readings"]) > 10:
            self.watch_data["glucose"]["readings"] = self.watch_data["glucose"]["readings"][-10:]
        
        self.watch_data["glucose"]["current"] = glucose
        self.watch_data["glucose"]["trend"] = trend
        self.watch_data["glucose"]["min_today"] = min(
            self.watch_data["glucose"]["min_today"],
            glucose
        )
        self.watch_data["glucose"]["max_today"] = max(
            self.watch_data["glucose"]["max_today"],
            glucose
        )
        
        self.watch_data["last_update"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self._save_data()
        
        return glucose, trend
    
    def record_meal(self, meal_type, food_items):
        """Record a meal"""
        now = datetime.now()
        
        # Determine meal type if not specified
        if not meal_type:
            hour = now.hour
            if 5 <= hour < 10:
                meal_type = "breakfast"
            elif 11 <= hour < 15:
                meal_type = "lunch"
            elif 17 <= hour < 22:
                meal_type = "dinner"
            else:
                meal_type = "snack"
        
        # Record the meal
        if meal_type in ["breakfast", "lunch", "dinner"]:
            self.watch_data["meals"][meal_type] = {
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "foods": food_items
            }
            # Mark meal reminder as handled
            if meal_type in self.meal_reminders:
                self.meal_reminders[meal_type] = True
        else:
            self.watch_data["meals"]["snacks"].append({
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "foods": food_items
            })
        
        # Update glucose after meal
        self.update_glucose()
        
        self.watch_data["last_update"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self._save_data()
    
    def check_for_events(self):
        """Check for time-based events like meal times"""
        now = datetime.now()
        current_time = now.time()
        events = []
        
        # Check for meal reminders
        for meal, meal_time in self.daily_routine.items():
            if meal in ["breakfast", "lunch", "dinner"] and not self.meal_reminders[meal]:
                # Check if it's meal time (within 30 min after scheduled time)
                time_diff = datetime.combine(datetime.today(), current_time) - datetime.combine(datetime.today(), meal_time)
                if 0 <= time_diff.total_seconds() < 1800:  # Within 30 minutes after meal time
                    events.append({
                        "type": "meal_reminder",
                        "meal": meal
                    })
                    self.meal_reminders[meal] = True  # Mark as reminded
        
        # Check for sedentary warnings
        if self.watch_data["activity"]["sedentary_minutes"] > 60:
            events.append({
                "type": "sedentary_warning",
                "minutes": self.watch_data["activity"]["sedentary_minutes"]
            })
        
        # Check for glucose warnings
        if self.watch_data["glucose"]["current"] > 140:
            events.append({
                "type": "glucose_warning",
                "level": self.watch_data["glucose"]["current"],
                "trend": self.watch_data["glucose"]["trend"]
            })
        
        return events
    
    def get_morning_summary(self):
        """Generate morning summary after wake up"""
        sleep_data = self.watch_data["sleep"]
        
        summary = {
            "sleep_duration": sleep_data["duration"],
            "sleep_quality": sleep_data["quality"],
            "deep_sleep": f"{sleep_data['deep_sleep_percentage']}%",
            "rem_sleep": f"{sleep_data['rem_sleep_percentage']}%",
            "awake_periods": sleep_data["awake_periods"],
            "resting_heart_rate": self.watch_data["heart_rate"]["resting"],
            "glucose_morning": self.watch_data["glucose"]["current"]
        }
        
        # Include recommendations based on sleep quality
        if sleep_data["quality"] == "Poor":
            summary["recommendations"] = [
                "Consider a short 15-minute morning meditation",
                "Avoid heavy carbs at breakfast to prevent energy crashes",
                "Prioritize protein in your breakfast to stabilize energy"
            ]
        elif sleep_data["quality"] == "Fair":
            summary["recommendations"] = [
                "A morning stretch might help you feel more refreshed",
                "Consider a balanced breakfast with protein and fiber"
            ]
        else:
            summary["recommendations"] = [
                "Great sleep! Consider a morning walk to maintain energy",
                "Your body is well-rested - a balanced breakfast will help maintain this state"
            ]
        
        return summary
    
    def get_current_watch_data(self):
        """Get current watch data for the chatbot"""
        # Update metrics first
        self.update_heart_rate()
        sedentary = (datetime.now().hour >= 8)  # Assume sedentary during work hours
        self.update_steps(not sedentary)
        self.update_glucose()
        
        return {
            "heart_rate": f"{self.watch_data['heart_rate']['current']} bpm",
            "heart_rate_trend": self.watch_data["heart_rate"]["trend"],
            "steps_count": str(self.watch_data["activity"]["steps"]),
            "active_minutes": str(self.watch_data["activity"]["active_minutes"]),
            "sedentary_minutes": str(self.watch_data["activity"]["sedentary_minutes"]),
            "blood_sugar": f"{self.watch_data['glucose']['current']} mg/dL",
            "blood_sugar_trend": self.watch_data["glucose"]["trend"],
            "calories_burned": str(self.watch_data["activity"]["calories_burned"]),
            "sleep_duration": self.watch_data["sleep"]["duration"],
            "sleep_quality": self.watch_data["sleep"]["quality"],
            "water_intake_ml": str(self.watch_data["water_intake_ml"])
        }

# Example usage:
if __name__ == "__main__":
    # Test the watch data manager
    manager = WatchDataManager()
    
    # Simulate sleep
    manager.simulate_sleep_data(False)  # Going to sleep
    
    # Fast-forward time (in a real app, this would happen naturally)
    print("Simulating sleep...")
    
    # Wake up
    morning_summary = manager.simulate_sleep_data(True)  # Waking up
    print("Morning summary:", json.dumps(morning_summary, indent=2))
    
    # Get current data
    print("Current watch data:", json.dumps(manager.get_current_watch_data(), indent=2))
    
    # Record breakfast
    manager.record_meal("breakfast", ["oatmeal with berries", "green tea"])
    print("After breakfast glucose:", manager.watch_data["glucose"]["current"])
    
    # Check for events
    events = manager.check_for_events()
    print("Events:", events)