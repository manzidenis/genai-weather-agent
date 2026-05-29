import os
import warnings
import json
import logging
from typing import Literal

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="langchain_google_genai.chat_models",
)

import googlemaps
import requests
from google.api_core.exceptions import ResourceExhausted
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

logging.getLogger("langchain_google_genai.chat_models").setLevel(logging.ERROR)

google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=google_maps_api_key) if google_maps_api_key else None

# ===============================================================
# Define the tool to convert a location to latitude and longitude
# ===============================================================
@tool
def latlon_geocoder(location: str) -> tuple[float, float]:
    """
    Converts a place name to latitude and longitude coordinates

    Args:
        location (str): The name of a place or location
    
    Returns:
        (float, float): A tuple of latitude and longitude coordinates
    
    Note: The NWS API doesn’t support more than four decimal places of precision in coordinates.
    Please round the coordinates to four decimal places.
    """
    if not location or not location.strip():
        raise ValueError("Location must be a non-empty string.")

    if gmaps is None:
        raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable is not set.")

    geocode_results = gmaps.geocode(location.strip())
    if not geocode_results:
        raise ValueError(f"No coordinates found for location: {location}")

    coordinates = geocode_results[0]["geometry"]["location"]
    latitude = round(coordinates["lat"], 4)
    longitude = round(coordinates["lng"], 4)

    return latitude, longitude

# ================================================
# Define the tool to fetch weather data
# ================================================
@tool
def get_weather_forecast(latitude: float, longitude: float) -> str:
    """Fetches worldwide weather data from Open-Meteo for a specific geographic location."""
    forecast_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,precipitation,rain,showers,snowfall,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "forecast_days": 7,
    }

    try:
        response = requests.get(forecast_url, params=params, timeout=20)
        response.raise_for_status()
        weather_data = response.json()
        return json.dumps(
            {
                "timezone": weather_data.get("timezone"),
                "current": weather_data.get("current"),
                "daily": weather_data.get("daily"),
            }
        )
    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data: {e}"

# Define the tools that the agent can use
tools = [latlon_geocoder, get_weather_forecast]

# Define the model using the `ChatGoogleGenerativeAI` class with the `gemini-1.5-flash` model and a temperature of 0
gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
model = ChatGoogleGenerativeAI(model=gemini_model, temperature=0)

# Bind the tools to the model
model = model.bind_tools(tools)


# ========================================================
# Define the function that determines the state transition
# ========================================================
def assistant_next_node(state: MessagesState) -> Literal["tools", END]:
    # Determine the state transition
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# ========================================
# Define the function that calls the model
# ========================================
def call_model(state: MessagesState):
    # Invoke the LLM with the state and return the result
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}

def run_query(agent, question: str) -> str:
    """
    Run a query using the agent and return the response
    
    Args:
        agent (ChatGoogleGenerativeAI): The agent to use
        question (str): The question to ask the agent

    Returns:
        str: The response from the agent
    """

    system_message = """
    Follow the steps in the example below to retrieve the weather information requested.

    Example:
      Question: What's the weather in Philadelphia, PA?
      Step 1: Extract the location from the question: Philadelphia, PA.
      Step 2: Invoke the latlon_geocoder tool with the extracted location.
      Step 3: Use the returned latitude and longitude coordinates.
      Step 4: Invoke the get_weather_forecast tool with the latitude and longitude.
      Step 5: Review the returned forecast periods for rain, precipitation, temperature, and conditions.
      Answer: Provide a concise answer based on the forecast data.

    Always use latlon_geocoder first when the question contains a place name.
    Then use get_weather_forecast with the returned coordinates.
    If the user asks whether it is raining, answer directly and mention the relevant forecast period.
    After using the tools, always produce a final plain-language answer for the user.
    Do not leave the final response empty.

    Question:
    """
    content = f"{system_message} {question}"

    # Invoke the agent with the question
    final_state = agent.invoke({"messages": [HumanMessage(content=content)]})

    # Return the last non-empty text response, not the intermediate tool messages.
    for message in reversed(final_state["messages"]):
        content = getattr(message, "content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()

    return "No text response was generated. Try asking the question again or use a different Gemini model."

if __name__ == '__main__':
    # ================================================
    # Create the workflow
    # ================================================

    # Create a StateGraph object called `workflow` with the `MessagesState` class
    workflow = StateGraph(MessagesState)
    
    # Add a node called "assistant" to the workflow that calls the `call_model` function
    workflow.add_node("assistant", call_model)
    
    # Set the entry point of the workflow to "assistant"
    workflow.set_entry_point("assistant")

    # Add a node called "tools" to the workflow that uses the `ToolNode` class with the `tools` list
    workflow.add_node("tools", ToolNode(tools))
    
    # Add conditional edges to the workflow using the `add_conditional_edges` method with the `assistant_next_node` function
    workflow.add_conditional_edges("assistant", assistant_next_node)
    
    # Add an edge from "tools" to "assistant" using the `add_edge` method
    workflow.add_edge("tools", "assistant")

    # ================================================
    # Compile the workflow
    # ================================================
    # Compile the workflow using the `compile` method
    agent = workflow.compile(checkpointer=None)

    # ================================================
    # Execute the query
    # ================================================
    # Execute the query using the `run_query` function and print the result
    query = input("Ask a weather question: ").strip()
    if not query:
        raise ValueError("Please enter a weather question.")

    try:
        result = run_query(agent, query)
        print(result)
    except ResourceExhausted:
        print(
            "Gemini quota is exhausted for the selected model. "
            "Wait for the quota window to reset, switch models with GEMINI_MODEL, "
            "or enable billing/quota for your Google AI project."
        )
