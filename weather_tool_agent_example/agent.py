# This script demonstrates how to create a simple weather tool agent using the Google Gemini API.
from google.adk.agents import Agent
from zoneinfo import ZoneInfo
import datetime
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
import asyncio
from google.genai import types

import warnings
warnings.filterwarnings("ignore")

import logging
import os
from dotenv import load_dotenv
logging.basicConfig(level=logging.ERROR)

print("Libraries imported successfully from agent.py...")
load_dotenv()

######################################## 1. Define the Tool  ########################################
def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.
    Args:
        city (str): The name of the city for which to retrieve the weather report.
    Returns:
        dict: A dictionary containing the weather information. Includes 'status' key ('success' or 'error').
        If 'status' is 'success', it contains 'report' key with the weather details.
        If 'status' is 'error', it contains 'error_message' key with the error details.
    """
    print(f"--- Tool: Executing get_weather tool for city: {city} ---")
    city_normalized = city.lower().replace(" ", "")
    mock_weather_db = {
        "newyork": {"status": "success", "report": "The weather in New York is sunny with a temperature of 25 degrees Celsius."},
        "london": {"status": "success", "report": "It's cloudy in London with a temperature of 15° Celsius."},
        "tokyo": {"status": "success", "report": "Tokyo is experiencing light rain and a temperature of 18°C."} 
    }
    if city_normalized in mock_weather_db:
        return mock_weather_db[city_normalized]
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available."
        }
print(get_weather("New York"))
print(get_weather("Paris"))


def get_current_time(city: str) -> dict:
    """Retrieves the current time in a specified city.
    Args:
        city (str): The name of the city for which to retrieve the current time.
    Returns:
        dict: status and result or error msg.
    """
    print(f"--- Tool: Executing get_current_time tool for city: {city} ---") # Added print
    # Simplified city check for demonstration
    if city.lower().replace(" ", "") == "newyork":
        tz_identifier = "America/New_York"
    elif city.lower().replace(" ", "") == "london":
         tz_identifier = "Europe/London" # Added London for example
    # Add more cities and their ZoneInfo identifiers here
    # e.g., elif city.lower().replace(" ", "") == "tokyo": tz_identifier = "Asia/Tokyo"
    else:
        return {
            "status": "error",
            "error_message": f"Sorry, I don't have the current time for '{city}'."
        }

    try:
        tz= ZoneInfo(tz_identifier)
        now = datetime.datetime.now(tz)
        report = (
            f"The current time in {city} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}."
        )
        return {
            "status": "success",
            "report": report
        }
    except Exception as e: # Catch potential ZoneInfo errors
        return {
            "status": "error",
            "error_message": f"Could not determine time for '{city}': {e}"
        }


######################################## 2. Define the Agent  ########################################
AGENT_MODEL = os.getenv("MODEL_GEMINI_2_0_FLASH", "gemini-1.5-flash-latest")
if not AGENT_MODEL:
    print("Warning: MODEL_GEMINI_2_0_FLASH not found in .env, using default 'gemini-1.5-flash-latest'")
    AGENT_MODEL = "gemini-1.5-flash-latest"

# Rename your agent instance to 'root_agent'
root_agent = Agent(
    name="weather_agent_v1", # You can keep the original name as well
    model=AGENT_MODEL,
    description="Provides weather and time information for a given city.",
    instruction="You are a helpful weather assistant. Your primary goal is to provide current weather reports. "
                "When the user asks for the weather in a specific city, "
                "you MUST use the 'get_weather' tool to find the information. "
                "Analyze the tool's response: if the status is 'error', inform the user politely about the error message. "
                "If the status is 'success', present the weather 'report' clearly and concisely to the user. "
                "Only use the tool when a city is mentioned for a weather request.",
    tools=[get_weather],
)

print(f"Agent '{root_agent.name}' created using model '{AGENT_MODEL}' in agent.py.")

####################################### 3. Setup Runner and Session Service  ######################################

session_service = InMemorySessionService()
APP_NAME = "weather_tutorial_app"
USER_ID = "user_1"
SESSION_ID = "session_001"

# Create the specific session where the conversation will happen
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
)
print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}' in agent.py.")

runner = Runner(
    agent=root_agent, # Use the renamed 'root_agent' here
    app_name=APP_NAME,
    session_service=session_service,
)
print(f"Runner created for agent '{runner.agent.name}' in agent.py.")

######################################## 4. Interact with the Agent  ########################################
async def call_agent_async(query: str):
    """Asynchronously calls the agent with a user query and returns the response."""
    print(f"\n--- Calling agent with query: '{query}' from agent.py ---")
    content = types.Content(
        role='user',
        parts=[types.Part(text=query)]
    )

    final_response_text = "Agent did not produce a final response."
    event_count = 0

    async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
        print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")
        # Key Concept: is_final_response() marks the concluding message for the turn.
        if event.is_final_response():
            if event.content and event.content.parts:
                # Assuming text response in the first part
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate: # Handle potential errors/escalations
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            # Add more checks here if needed (e.g., specific error codes)
            break # Stop processing events once the final response is found

    print(f"<<< Agent Response: {final_response_text}")
    
######################################## 5. Run the Conversation  ########################################

async def run_conversation():
    await call_agent_async("What is the weather like in London?")
    await call_agent_async("How about Paris?") # Expecting the tool's error message
    await call_agent_async("Tell me the weather in New York")


# --- EXECUTION ---
if __name__ == "__main__":
    try:
        asyncio.run(run_conversation())
    except Exception as e:
        print(f"\nAn error occurred during the async execution in agent.py: {e}")