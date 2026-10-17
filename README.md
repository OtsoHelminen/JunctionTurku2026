# HomeGuard

Your personal safety buddy to minimize damage to your home from adverse weather events and other risks.

The solution is a combination of a mobile app, a backend server and an AI agent workflow.

## Getting Started

Server hosting on a computer:
1. Clone the repository.
2. install `uv`
3. Run the application using the instructions below.

Mobile application:


## Usage

The two backend repositories data_consolidator and logical-unit are run as uvicorn fastapi servers. Starting from the root repository:

```
uv sync
```

To start the data api:

```
cd data_consolidator
uv run uvicorn fastapi main:app --reload --host 0.0.0.0 --port 8008
```

To start the logical unit:

```
cd logical-unit
set -a && . ./.env && set +a          # Qwen settings
uv run uvicorn app.main:app --port 8001
```

## Data flow architecture

data_consolidator acts as the main backend api handling information flow form data sources to consolidated events.

logical-unit consumes these consolidated events and processes them through an agentic AI workflow into actionable alerts which are then routed back to the data_consolidator api and sent to the frontend mobile app.
