import os
import time
import re
import random
from datetime import datetime, date, timedelta, time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from watch_data_manager import WatchDataManager

# Set your Gemini API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyDgflhQJ2v0VxGCpDdbtP6wBiOX92oQgeg"

# Persistent memory stores
store = {}
metadata_store = {}
response_memory_store = {}
health_metrics_store = {}
watch_managers = {}

class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    messages: list[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: list[BaseMessage]) -> None:
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    return store[session_id]

# Health metrics class
class HealthMetrics(BaseModel):
    """Track health metrics throughout the day"""
    last_meal_time: str = None
    last_meal_content: str = None
    sleep_duration: str = None
    sleep_quality: str = None
    heart_rate_readings: list = Field(default_factory=list)
    blood_sugar_readings: list = Field(default_factory=list)
    steps_count: int = 0
    sedentary_minutes: int = 0
    stress_level: str = "low"
    water_intake_ml: int = 0

def update_health_metrics(session_id, **metrics):
    """Update health metrics for a user"""
    if session_id not in health_metrics_store:
        health_metrics_store[session_id] = HealthMetrics()
    
    for key, value in metrics.items():
        if hasattr(health_metrics_store[session_id], key):
            setattr(health_metrics_store[session_id], key, value)

def update_metadata(session_id: str, last_meal_time: str = None, last_sleep_time: str = None, discussed=None):
    if session_id not in metadata_store:
        metadata_store[session_id] = {}
    if last_meal_time:
        metadata_store[session_id]['last_meal_time'] = last_meal_time
    if last_sleep_time:
        metadata_store[session_id]['last_sleep_time'] = last_sleep_time
    if session_id not in response_memory_store:
        response_memory_store[session_id] = {"greeting": False, "sleep": False, "meal": False}
    if discussed:
        for item in discussed:
            response_memory_store[session_id][item] = True

# Get context based on time of day
def get_context_for_time(time_str):
    hour = int(time_str.split(":")[0])
    if 5 <= hour < 10:
        return {
            "current_activity": "Morning routine",
            "sedentary_minutes": "0",
            "current_heart_rate": "72 bpm",
            "heart_rate_trend": "stable",
            "stress_indicators": "low",
            "blood_sugar": "110 mg/dL",
            "blood_sugar_trend": "rising slightly after breakfast"
        }
    elif 10 <= hour < 13:
        return {
            "current_activity": "Work meeting",
            "sedentary_minutes": "90",
            "current_heart_rate": "85 bpm",
            "heart_rate_trend": "elevated during meeting",
            "stress_indicators": "moderate - upcoming client presentation",
            "blood_sugar": "125 mg/dL",
            "blood_sugar_trend": "stable"
        }
    # Add more time periods as needed
    else:
        return {
            "current_activity": "Regular daily activities",
            "sedentary_minutes": "30",
            "current_heart_rate": "75 bpm", 
            "heart_rate_trend": "normal",
            "stress_indicators": "low",
            "blood_sugar": "115 mg/dL",
            "blood_sugar_trend": "stable"
        }

# Function to simulate watch data
def simulate_watch_data(session_id):
    """Simulate automated data from smartwatch"""
    current_hour = datetime.now().hour
    
    # Heart rate simulation based on time of day
    if 5 <= current_hour < 8:  # Morning, waking up
        heart_rate = random.randint(65, 75)
        trend = "rising"
    elif 8 <= current_hour < 12:  # Morning work
        heart_rate = random.randint(70, 85)
        trend = "stable"
    elif 12 <= current_hour < 14:  # Lunch time
        heart_rate = random.randint(75, 90)
        trend = "elevated"
    else:  # Afternoon/evening
        heart_rate = random.randint(68, 80)
        trend = "normal"
    
    # Steps simulation - accumulates throughout day
    current_metrics = health_metrics_store.get(session_id, HealthMetrics())
    current_steps = current_metrics.steps_count or 0
    
    # Add some random steps based on time
    new_steps = random.randint(200, 1000) if 8 <= current_hour < 22 else random.randint(0, 100)
    total_steps = current_steps + new_steps
    
    # Sedentary minutes calculation
    if new_steps < 300:  # Not much movement
        sedentary_increase = random.randint(25, 60)
    else:
        sedentary_increase = random.randint(0, 15)
    
    current_sedentary = current_metrics.sedentary_minutes or 0
    total_sedentary = current_sedentary + sedentary_increase
    
    # Update metrics
    update_health_metrics(
        session_id,
        heart_rate_readings=[(datetime.now().strftime("%H:%M"), heart_rate)],
        steps_count=total_steps,
        sedentary_minutes=total_sedentary
    )
    
    return {
        "current_heart_rate": f"{heart_rate} bpm",
        "heart_rate_trend": trend,
        "steps_count": str(total_steps),
        "sedentary_minutes": str(total_sedentary)
    }

# Function to parse user input for health data
def parse_user_input(user_input, session_id):
    """Extract health metrics from user's natural language input"""
    input_lower = user_input.lower()
    updates = {}
    
    # Parse meal information
    meal_pattern = r"(ate|had|consumed|eating|having|food|meal|breakfast|lunch|dinner).*?([\w\s,]+)"
    meal_match = re.search(meal_pattern, input_lower)
    if meal_match:
        meal_content = meal_match.group(2).strip()
        updates["last_meal_content"] = meal_content
        updates["last_meal_time"] = datetime.now().strftime("%H:%M")
        update_metadata(session_id, last_meal_time=updates["last_meal_time"])
    
    # Parse blood glucose level
    glucose_pattern = r"(glucose|sugar|bg|blood sugar|blood glucose).*([\d\.]+)"
    glucose_match = re.search(glucose_pattern, input_lower)
    if glucose_match:
        glucose_value = glucose_match.group(2)
        current_metrics = health_metrics_store.get(session_id, HealthMetrics())
        readings = current_metrics.blood_sugar_readings or []
        readings.append((datetime.now().strftime("%H:%M"), float(glucose_value)))
        updates["blood_sugar_readings"] = readings
    
    # Parse water intake
    water_pattern = r"(water|drank|drinking).*([\d\.]+)\s*(ml|oz|glass|cup)"
    water_match = re.search(water_pattern, input_lower)
    if water_match:
        amount = float(water_match.group(2))
        unit = water_match.group(3).lower()
        
        # Convert to ml
        if unit == "oz":
            amount *= 29.57
        elif unit in ["glass", "cup"]:
            amount *= 240
            
        current_metrics = health_metrics_store.get(session_id, HealthMetrics())
        current_water = current_metrics.water_intake_ml or 0
        updates["water_intake_ml"] = current_water + int(amount)
    
    # Update health metrics if any found
    if updates:
        update_health_metrics(session_id, **updates)
    
    return updates

# Interactive prompt template
interactive_prompt = PromptTemplate.from_template(
    """You are {user_name}'s personal health assistant integrated with their smartwatch and health monitoring system.
You should respond conversationally to their inputs while providing health insights.

Current Context:
- Time: {current_time}
- Date: {date}
- Current Activity: {current_activity}

Health Data:
- Heart Rate: {current_heart_rate} (Trend: {heart_rate_trend})
- Steps Today: {steps_count}
- Sleep: {sleep_duration} (Quality: {sleep_quality})
- Last Meal: {last_meal_time} - {last_meal_content}
- Blood Sugar Level: {blood_sugar} (Trend: {blood_sugar_trend})
- Stress Indicators: {stress_indicators}
- Sedentary Time: {sedentary_minutes} minutes
- Water Intake: {water_intake_ml} ml

User Context:
- Diabetic Type: {diabetic_type}
- Communication Style: {communication_style}

Special Instructions:
- If the input contains [MORNING WAKE UP], provide a detailed sleep review and breakfast suggestions.
- If the input contains [MEALTIME REMINDER], ask what they plan to eat and offer suitable options.
- If the input contains [MOVEMENT REMINDER], encourage them to take a break and move around.
- If the input contains [GLUCOSE ALERT], provide guidance on managing their current blood sugar level.
- If the input contains [WATCH UPDATE], only respond if there's something significant to note.
- If the input contains [GOING TO SLEEP], offer relaxation tips and set expectations for tomorrow.

Previous conversation: {history}

User input: {input}

Respond conversationally to the user's input. If they've provided new health information, acknowledge it and provide relevant insights or suggestions. 
If they ask a question, answer it based on their health context.
Keep your responses friendly and focused on helping them manage their pre-diabetic condition.
Always prioritize addressing what the user has just said rather than introducing new topics.
"""
)

# Set up the LLM chain
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
output_parser = StrOutputParser()
chain = interactive_prompt | llm | output_parser

with_history = RunnableWithMessageHistory(
    chain,
    get_session_history=get_by_session_id,
    input_messages_key="input",
    history_messages_key="history"
)

# Initialize user data
def initialize_user_data(session_id="user_session"):
    current_time = datetime.now().strftime("%H:%M")
    time_context = get_context_for_time(current_time)
    
    # Initialize with some base data
    user_data = {
        "user_name": "Samantha",
        "current_time": current_time,
        "date": date.today().isoformat(),
        "sleep_duration": "6 hours 15 minutes",
        "sleep_quality": "Fragmented with lower-than-optimal REM cycles",
        "steps_count": "0",
        "last_meal_time": "Not recorded yet",
        "last_meal_content": "Not recorded yet",
        "communication_style": "Friendly and direct",
        "diabetic_type": "Pre-diabetic",
        "current_activity": time_context["current_activity"],
        "current_heart_rate": time_context["current_heart_rate"],
        "heart_rate_trend": time_context["heart_rate_trend"],
        "blood_sugar": time_context["blood_sugar"],
        "blood_sugar_trend": time_context["blood_sugar_trend"],
        "stress_indicators": time_context["stress_indicators"],
        "sedentary_minutes": time_context["sedentary_minutes"]
    }
    
    # Initialize stores
    update_metadata(session_id)
    update_health_metrics(
        session_id,
        steps_count=0,
        sedentary_minutes=0,
        water_intake_ml=0
    )
    
    return user_data

def initialize_watch_manager(session_id="user_session"):
    """Initialize the watch data manager for this session"""
    if session_id not in watch_managers:
        watch_managers[session_id] = WatchDataManager(user_name=session_id)
    return watch_managers[session_id]

# Main interactive loop
def interactive_chatbot():
    """Run the interactive chatbot with both watch data and user inputs"""
    session_id = "user_session"
    user_data = initialize_user_data(session_id)
    watch_manager = initialize_watch_manager(session_id)
    
    print("\n=== Health Assistant Interactive Chatbot ===")
    print("(Type 'exit' to quit, 'wake' when you wake up, 'sleep' when going to bed, or enter your message)")
    print("Bot: Hi there! I'm your personal health assistant. How can I help you today?")
    
    last_watch_update = datetime.now()
    watch_update_interval = timedelta(minutes=5)  # Update watch data every 5 minutes for testing
    
    while True:
        # Check if it's time for a watch update
        now = datetime.now()
        if now - last_watch_update >= watch_update_interval:
            print("\n[Updating watch data...]")
            watch_data = watch_manager.get_current_watch_data()
            user_data.update(watch_data)
            last_watch_update = now
            
            # Check for time-based events
            events = watch_manager.check_for_events()
            for event in events:
                if event["type"] == "meal_reminder":
                    meal = event["meal"]
                    print(f"\n[Time for {meal}]")
                    response = with_history.invoke(
                        {"input": f"[MEALTIME REMINDER: {meal}]", **user_data},
                        config={"configurable": {"session_id": session_id}}
                    )
                    print(f"Bot: {response}")
                
                elif event["type"] == "sedentary_warning":
                    print("\n[Sedentary warning]")
                    response = with_history.invoke(
                        {"input": "[MOVEMENT REMINDER]", **user_data},
                        config={"configurable": {"session_id": session_id}}
                    )
                    print(f"Bot: {response}")
                
                elif event["type"] == "glucose_warning":
                    print("\n[Blood sugar alert]")
                    response = with_history.invoke(
                        {"input": f"[GLUCOSE ALERT: {event['level']} mg/dL, trend: {event['trend']}]", **user_data},
                        config={"configurable": {"session_id": session_id}}
                    )
                    print(f"Bot: {response}")
        
        # Get user input
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            print("Bot: Goodbye! Take care of your health.")
            break
        
        # Special commands
        if user_input.lower() == 'wake':
            print("\n[Morning wake-up detected]")
            morning_summary = watch_manager.simulate_sleep_data(wake_up=True)
            watch_data = watch_manager.get_current_watch_data()
            user_data.update(watch_data)
            user_data.update({
                "sleep_duration": morning_summary["sleep_duration"],
                "sleep_quality": morning_summary["sleep_quality"]
            })
            
            response = with_history.invoke(
                {"input": "[MORNING WAKE UP]", **user_data},
                config={"configurable": {"session_id": session_id}}
            )
            print(f"Bot: {response}")
            continue
        
        elif user_input.lower() == 'sleep':
            print("\n[Going to sleep]")
            watch_manager.simulate_sleep_data(wake_up=False)
            response = with_history.invoke(
                {"input": "[GOING TO SLEEP]", **user_data},
                config={"configurable": {"session_id": session_id}}
            )
            print(f"Bot: {response}")
            continue
        
        # Parse user input for meal information
        if re.search(r"(ate|had|consumed|eating|having|food|meal|breakfast|lunch|dinner)", user_input.lower()):
            # Extract meal type
            meal_type = None
            if "breakfast" in user_input.lower():
                meal_type = "breakfast"
            elif "lunch" in user_input.lower():
                meal_type = "lunch" 
            elif "dinner" in user_input.lower():
                meal_type = "dinner"
            
            # Extract food items (anything after "ate", "had", etc.)
            food_match = re.search(r"(ate|had|consumed|eating|having|food|meal).*?([\w\s,]+)", user_input.lower())
            if food_match:
                foods = food_match.group(2).strip()
                watch_manager.record_meal(meal_type, foods)
                
                # Update user data with new meal info
                watch_data = watch_manager.get_current_watch_data()
                user_data.update(watch_data)
                user_data["last_meal_content"] = foods
                user_data["last_meal_time"] = datetime.now().strftime("%H:%M")
        
        # Parse blood glucose level
        glucose_match = re.search(r"(glucose|sugar|bg|blood sugar|blood glucose).*([\d\.]+)", user_input.lower())
        if glucose_match:
            glucose_value = float(glucose_match.group(2))
            watch_manager.update_glucose(manual_value=glucose_value)
            
            # Update user data with new glucose info
            watch_data = watch_manager.get_current_watch_data()
            user_data.update(watch_data)
        
        # Process standard input through the regular parser
        updates = parse_user_input(user_input, session_id)
        if updates:
            # Update user_data with any extracted health information
            if "last_meal_content" in updates:
                user_data["last_meal_content"] = updates["last_meal_content"]
                user_data["last_meal_time"] = updates["last_meal_time"]
            if "blood_sugar_readings" in updates and updates["blood_sugar_readings"]:
                latest = updates["blood_sugar_readings"][-1]
                user_data["blood_sugar"] = f"{latest[1]} mg/dL"
            if "water_intake_ml" in updates:
                user_data["water_intake_ml"] = str(updates["water_intake_ml"])
        
        # Get response from the bot
        response = with_history.invoke(
            {"input": user_input, **user_data},
            config={"configurable": {"session_id": session_id}}
        )
        
        print(f"Bot: {response}")

# Enhanced interactive loop with automatic triggers
def interactive_chatbot_enhanced():
    """Run the interactive chatbot with proactive triggering based on watch data changes"""
    session_id = "user_session"
    user_data = initialize_user_data(session_id)
    watch_manager = initialize_watch_manager(session_id)
    
    print("\n=== Health Assistant Interactive Chatbot (Enhanced) ===")
    print("(Type 'exit' to quit, or enter your message)")
    print("Bot: Hi there! I'm your personal health assistant. I'll be monitoring your health data throughout the day.")
    
    last_watch_update = datetime.now()
    watch_update_interval = timedelta(minutes=1)  # Check more frequently - each minute
    
    # Track states to detect changes
    last_sleep_state = None
    last_meal_times = {
        "breakfast": None,
        "lunch": None,
        "dinner": None
    }
    last_glucose = None
    last_activity = {
        "steps": 0,
        "sedentary_minutes": 0
    }
    
    # Meal timeframes (when we should check if meals were recorded)
    meal_timeframes = {
        "breakfast": (time(7, 0), time(9, 30)),
        "lunch": (time(12, 0), time(14, 0)),
        "dinner": (time(18, 0), time(20, 30))
    }
    
    meal_reminders_sent = {
        "breakfast": False,
        "lunch": False,
        "dinner": False
    }
    
    activity_reminder_time = datetime.now()
    
    while True:
        # Check for user input (non-blocking)
        user_input = input_with_timeout("\nYou: ", 1)
        
        if user_input == "exit":
            print("Bot: Goodbye! Take care of your health.")
            break
            
        # Process user input if provided
        if user_input:
            # Parse meal information
            if re.search(r"(ate|had|consumed|eating|having|food|meal|breakfast|lunch|dinner)", user_input.lower()):
                # Extract meal type
                meal_type = None
                if "breakfast" in user_input.lower():
                    meal_type = "breakfast"
                    meal_reminders_sent["breakfast"] = True
                elif "lunch" in user_input.lower():
                    meal_type = "lunch"
                    meal_reminders_sent["lunch"] = True
                elif "dinner" in user_input.lower():
                    meal_type = "dinner"
                    meal_reminders_sent["dinner"] = True
                
                # Extract food items
                food_match = re.search(r"(ate|had|consumed|eating|having|food|meal).*?([\w\s,]+)", user_input.lower())
                if food_match:
                    foods = food_match.group(2).strip()
                    watch_manager.record_meal(meal_type, foods)
                    
                    # Update user data with new meal info
                    watch_data = watch_manager.get_current_watch_data()
                    user_data.update(watch_data)
                    user_data["last_meal_content"] = foods
                    user_data["last_meal_time"] = datetime.now().strftime("%H:%M")
                    
                    # Update last meal times
                    if meal_type:
                        last_meal_times[meal_type] = datetime.now()
            
            # Parse blood glucose
            glucose_match = re.search(r"(glucose|sugar|bg|blood sugar|blood glucose).*([\d\.]+)", user_input.lower())
            if glucose_match:
                glucose_value = float(glucose_match.group(2))
                watch_manager.update_glucose(manual_value=glucose_value)
                
                # Update user data with new glucose info
                watch_data = watch_manager.get_current_watch_data()
                user_data.update(watch_data)
                last_glucose = glucose_value
            
            # Process other health data
            updates = parse_user_input(user_input, session_id)
            if updates:
                if "water_intake_ml" in updates:
                    user_data["water_intake_ml"] = str(updates["water_intake_ml"])
            
            # Get response from the bot
            response = with_history.invoke(
                {"input": user_input, **user_data},
                config={"configurable": {"session_id": session_id}}
            )
            
            print(f"Bot: {response}")
        
        # Check watch data periodically
        now = datetime.now()
        if now - last_watch_update >= watch_update_interval:
            # Update watch data
            watch_data = watch_manager.get_current_watch_data()
            user_data.update(watch_data)
            last_watch_update = now
            current_time = now.time()
            
            # ======= DETECT STATE CHANGES AND TRIGGER INTERACTIONS =======
            
            # 1. WAKE/SLEEP DETECTION
            # Check if sleep state has changed (simulate with watch data)
            # This would normally be detected by actual smartwatch sensors
            if 5 <= now.hour <= 9:  # Morning hours
                # Simulate wake detection if we haven't already detected it
                if last_sleep_state != "awake" and watch_manager.watch_data["sleep"]["last_sleep_time"]:
                    print("\n[Watch detected: User waking up]")
                    morning_summary = watch_manager.simulate_sleep_data(wake_up=True)
                    watch_data = watch_manager.get_current_watch_data()
                    user_data.update(watch_data)
                    user_data.update({
                        "sleep_duration": morning_summary["sleep_duration"],
                        "sleep_quality": morning_summary["sleep_quality"]
                    })
                    
                    response = with_history.invoke(
                        {"input": "[MORNING WAKE UP]", **user_data},
                        config={"configurable": {"session_id": session_id}}
                    )
                    print(f"Bot: {response}")
                    last_sleep_state = "awake"
            
            if 22 <= now.hour <= 23:  # Evening hours
                # Simulate bedtime detection
                if last_sleep_state != "sleeping":
                    # This could be triggered by several factors:
                    # - No movement for extended period during night hours
                    # - Heart rate dropping to resting levels
                    # - Typical bedtime based on user history
                    heart_rate = int(watch_data["heart_rate"].split()[0])
                    if heart_rate < 70:  # Lower heart rate suggesting rest
                        print("\n[Watch detected: User going to sleep]")
                        watch_manager.simulate_sleep_data(wake_up=False)
                        
                        response = with_history.invoke(
                            {"input": "[GOING TO SLEEP]", **user_data},
                            config={"configurable": {"session_id": session_id}}
                        )
                        print(f"Bot: {response}")
                        last_sleep_state = "sleeping"
            
            # 2. MEAL DETECTION
            # Check if it's time for a meal but no meal has been recorded
            for meal, (start_time, end_time) in meal_timeframes.items():
                # Check if we're in the timeframe for this meal
                if start_time <= current_time <= end_time:
                    # Check if meal hasn't been recorded and reminder hasn't been sent
                    if not watch_manager.watch_data["meals"][meal] and not meal_reminders_sent[meal]:
                        # Only send meal reminders during appropriate hours
                        time_since_start = (datetime.combine(date.today(), current_time) - 
                                           datetime.combine(date.today(), start_time)).total_seconds() / 60
                        
                        # Wait at least 30 minutes into the meal window before reminding
                        if time_since_start >= 30:
                            print(f"\n[Watch detected: {meal.capitalize()} time but no meal recorded]")
                            
                            response = with_history.invoke(
                                {"input": f"[MEALTIME REMINDER: {meal}]", **user_data},
                                config={"configurable": {"session_id": session_id}}
                            )
                            print(f"Bot: {response}")
                            meal_reminders_sent[meal] = True
            
            # 3. ACTIVITY DETECTION
            # Check for prolonged inactivity
            sedentary_minutes = int(watch_data["sedentary_minutes"])
            if sedentary_minutes > 60 and (now - activity_reminder_time).total_seconds() / 60 > 60:
                # Only send reminder if we haven't sent one in the last hour
                print("\n[Watch detected: Extended inactivity]")
                
                response = with_history.invoke(
                    {"input": "[MOVEMENT REMINDER]", **user_data},
                    config={"configurable": {"session_id": session_id}}
                )
                print(f"Bot: {response}")
                activity_reminder_time = now
            
            # 4. GLUCOSE ALERTS
            # Check for concerning glucose readings
            if watch_manager.watch_data["glucose"]["current"] > 140:
                if not last_glucose or last_glucose < 140:  # Only alert on crossing threshold
                    print("\n[Watch detected: Elevated blood sugar]")
                    
                    response = with_history.invoke(
                        {"input": f"[GLUCOSE ALERT: {watch_manager.watch_data['glucose']['current']} mg/dL, trend: {watch_manager.watch_data['glucose']['trend']}]", **user_data},
                        config={"configurable": {"session_id": session_id}}
                    )
                    print(f"Bot: {response}")
                last_glucose = watch_manager.watch_data["glucose"]["current"]
            
            # 5. Check for other time-based events
            events = watch_manager.check_for_events()
            for event in events:
                if event["type"] == "meal_reminder" and not meal_reminders_sent[event["meal"]]:
                    print(f"\n[Time for {event['meal']}]")
                    response = with_history.invoke(
                        {"input": f"[MEALTIME REMINDER: {event['meal']}]", **user_data},
                        config={"configurable": {"session_id": session_id}}
                    )
                    print(f"Bot: {response}")
                    meal_reminders_sent[event["meal"]] = True

# Helper function for non-blocking input
def input_with_timeout(prompt, timeout=1):
    """Get input with timeout to allow for watch data checking (Windows compatible)"""
    import msvcrt
    import time
    
    print(prompt, end='', flush=True)
    start_time = time.time()
    input_str = ''
    
    while (time.time() - start_time) < timeout:
        # Check if keyboard input is available
        if msvcrt.kbhit():
            char = msvcrt.getche().decode('utf-8')
            
            # Handle Enter key
            if char == '\r':
                print('')  # Add newline
                return input_str
            # Handle Backspace
            elif char == '\b':
                if input_str:
                    # Remove the last character from input string
                    input_str = input_str[:-1]
                    # Overwrite the character on console (backspace, space, backspace)
                    print('\b \b', end='', flush=True)
            else:
                input_str += char
                
        # Small pause to reduce CPU usage
        time.sleep(0.05)
    
    # Return None if timeout occurred with no complete input
    print('')  # Add newline
    return None if not input_str else input_str

# Run the enhanced interactive chatbot
if __name__ == "__main__":
    interactive_chatbot_enhanced()