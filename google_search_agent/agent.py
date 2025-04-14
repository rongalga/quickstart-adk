from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="basic_search_agent",
    model="gemini-2.0-flash-exp",
    description="Agent that can search the web using Google Search.",
    instruction="You are an expert researcher. You alway stick to the facts.",
    tools=[google_search],   
)