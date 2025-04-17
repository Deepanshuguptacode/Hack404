import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from datetime import datetime, date

# Set your Gemini API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyDgflhQJ2v0VxGCpDdbtP6wBiOX92oQgeg"

# Persistent memory store
store = {}
metadata_store = {}  # New metadata store for last meal/sleep tracking
response_memory_store = {}

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

# def check_time_difference(past_time_str, threshold_hours):
#     if not past_time_str:
#         return False
#     past_time = datetime.strptime(past_time_str, "%H:%M")
#     now = datetime.now()
#     current_time = datetime.strptime(now.strftime("%H:%M"), "%H:%M")
#     diff = current_time - past_time
#     return diff.total_seconds() / 3600 > threshold_hours

# Add time-specific context generation
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

# Initialize metrics store
health_metrics_store = {}

def update_health_metrics(session_id, **metrics):
    """Update health metrics for a user"""
    if session_id not in health_metrics_store:
        health_metrics_store[session_id] = HealthMetrics()
    
    for key, value in metrics.items():
        if hasattr(health_metrics_store[session_id], key):
            setattr(health_metrics_store[session_id], key, value)

prompt_template = PromptTemplate.from_template(
    """You are {user_name}'s personal health assistant integrated with their smartwatch and health monitoring system.

Create a narrative section of {user_name}'s day, focusing on the current time period ({current_time}).
Format your response as a story with timestamps, interactions, and personalized insights.

Current Context:
- Time: {current_time}
- Date: {date}
- Last recorded activity: {current_activity}

Health Data:
- Sleep Duration: {sleep_duration}
- Sleep Quality: {sleep_quality}
- Heart Rate: {current_heart_rate} (Trend: {heart_rate_trend})
- Steps Today: {steps_count}
- Last Meal: {last_meal_time} - {last_meal_content}
- Blood Sugar Level: {blood_sugar} (Trend: {blood_sugar_trend})
- Stress Indicators: {stress_indicators}
- Sedentary Time: {sedentary_minutes} minutes

User Context:
- Diabetic Type: {diabetic_type}
- Communication Style: {communication_style}
- Upcoming Events: {upcoming_event}

Based on this context, create a narrative that:
1. Addresses {user_name} directly in a {communication_style} tone
2. Weaves in personalized health insights based on the time of day
3. Offers specific, actionable advice related to her pre-diabetic condition
4. Suggests contextual interventions (movement breaks, food choices, stress management)
5. Simulates how a proactive health assistant would interact throughout the day

Write this as if it's an actual interaction happening at {current_time}, not a summary of the whole day.
"""
)

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
output_parser = StrOutputParser()
chain = prompt_template | llm | output_parser

with_history = RunnableWithMessageHistory(
    chain,
    get_session_history=get_by_session_id,
    input_messages_key="input",
    history_messages_key="history"
)

# Simulated Input - modify this section
current_time = "10:00"  # You can change this to simulate different times of day
time_context = get_context_for_time(current_time)

# Enhanced user data with more specific context
user_data = {
    "user_name": "Samantha",
    "current_time": current_time,
    "date": date.today().isoformat(),
    "sleep_duration": "6 hours 15 minutes",
    "sleep_quality": "Fragmented with lower-than-optimal REM cycles",
    "steps_count": "2,450 steps so far",
    "last_meal_time": "7:00 AM",
    "last_meal_content": "Cereal and toast with jam (high carbohydrate)",
    "communication_style": "Friendly, direct, and proactive",
    "diabetic_type": "Pre-diabetic",
    "upcoming_event": "Client meeting at 10:00 AM",
    **time_context  # Add the time-specific context
}

session_id = "samantha_session"
update_metadata(session_id, last_meal_time="07:00", last_sleep_time="06:30")

response = with_history.invoke(
    user_data,
    config={"configurable": {"session_id": session_id}}
)

# Assume it mentioned breakfast/sleep if those fields were sent
discussed_items = []
if "sleep_duration" in user_data:
    discussed_items.append("sleep")
if "last_meal_time" in user_data:
    discussed_items.append("meal")
if not response_memory_store[session_id]["greeting"]:
    discussed_items.append("greeting")

update_metadata(session_id, discussed=discussed_items)

print(response)

def simulate_health_assistant_at_time(time_str, session_id="samantha_session"):
    """Generate a narrative health interaction for a specific time"""
    global user_data
    user_data["current_time"] = time_str
    user_data.update(get_context_for_time(time_str))
    
    response = with_history.invoke(
        user_data,
        config={"configurable": {"session_id": session_id}}
    )
    
    print(f"\n--- Interaction at {time_str} ---\n")
    print(response)
    print("\n" + "-" * 50 + "\n")
    
    return response

# Simulate multiple interactions throughout the day
simulate_health_assistant_at_time("6:30")
simulate_health_assistant_at_time("7:00")
simulate_health_assistant_at_time("9:30")
simulate_health_assistant_at_time("12:30")