# GenAI Weather Agent

An agentic weather assistant built with LangGraph, Gemini tool calling, and Google Cloud Platform services. It converts user-provided place names into coordinates with the Google Maps Geocoding API, fetches global weather data from Open-Meteo, and returns a concise natural-language answer.

![Agentic weather workflow](docs/agentic-weather-workflow.png)

## How It Works

The assistant follows a simple tool-using workflow:

1. The user asks a weather question.
2. Gemini decides which tools are needed.
3. `latlon_geocoder` converts a location into latitude and longitude using Google Maps.
4. `get_weather_forecast` fetches current and forecast weather from Open-Meteo.
5. Gemini summarizes the tool results into a user-friendly answer.

## Project Structure

```text
agentic_workflow/
  lg_agent.py          # LangGraph weather agent
  requirements.txt     # Python dependencies
docs/
  agentic-weather-workflow.png
```

## GCP Setup

This project uses Google Cloud Platform for environment setup, API access, and credential management.

1. Create a GCP project, for example:

```text
genai-agentic-workflow
```

2. Create a Compute Engine VM:

```text
Region: us-east1
Zone: us-east1-b
Machine type: e2-medium
OS: Ubuntu 24.04 LTS
```

3. Install and initialize the Google Cloud CLI on the VM:

```bash
gcloud init
gcloud auth application-default login
```

4. Enable the Google Maps Geocoding API:

```bash
gcloud services enable geocoding-backend.googleapis.com
```

5. Create a Google Maps API key from the GCP Credentials page and export it:

```bash
export GOOGLE_MAPS_API_KEY="your_google_maps_api_key"
```

6. Create a Gemini API key and export it:

```bash
export GOOGLE_API_KEY="your_gemini_api_key"
```

## Requirements

- Python 3.11 or 3.12
- GCP project with the Google Maps Geocoding API enabled
- Google Maps API key from GCP
- Gemini API key for `ChatGoogleGenerativeAI`

Install dependencies:

```powershell
cd C:\Users\Manzi\Desktop\genai_weather_predictor
.\.venv\Scripts\Activate.ps1
cd agentic_workflow
python -m pip install -r requirements.txt
```

## Environment Variables

Set your keys in PowerShell before running:

```powershell
$env:GOOGLE_MAPS_API_KEY="your_google_maps_api_key"
$env:GOOGLE_API_KEY="your_gemini_api_key"
```

On Linux or a GCP VM, use:

```bash
export GOOGLE_MAPS_API_KEY="your_google_maps_api_key"
export GOOGLE_API_KEY="your_gemini_api_key"
```

Optional model override:

```powershell
$env:GEMINI_MODEL="gemini-2.5-flash"
```

## Run

From the `agentic_workflow` folder:

```powershell
python lg_agent.py
```

Example:

```text
Ask a weather question: Is it raining in Kigali?
```

Expected style of output:

```text
No, it is not currently raining in Kigali. The current conditions show no rain, with the forecast indicating a low chance of precipitation.
```

## Notes

- Google Cloud Platform is used for VM setup, Google Maps Geocoding API access, API key management, and application default credentials.
- Open-Meteo provides worldwide weather forecast data by latitude and longitude.
- Google Maps Geocoding is used to support flexible place-name input.
- Gemini API quota limits may affect execution. If quota is exhausted, wait for the quota window to reset, switch models, or enable billing/quota for the Google AI project.
- After testing, delete the GCP VM or shut down the GCP project to avoid unwanted charges.
