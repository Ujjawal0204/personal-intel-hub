"""
Coordinator Agent - routes user queries to the appropriate sub-agent.
Multi-agent A2A architecture with retry logic for rate limits.
"""

import logging
import asyncio
import random
from datetime import date
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from app.agents.task_agent import task_agent
from app.agents.schedule_agent import schedule_agent
from app.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 10


async def _run_agent_with_retry(agent, message):
    """Run a sub-agent with retry logic for rate limits."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part

    for attempt in range(MAX_RETRIES):
        try:
            session_service = InMemorySessionService()
            runner = Runner(agent=agent, app_name="intel_hub", session_service=session_service)
            session = await session_service.create_session(app_name="intel_hub", user_id="coordinator")
            user_content = Content(parts=[Part(text=message)], role="user")

            response_text = ""
            async for event in runner.run_async(user_id="coordinator", session_id=session.id, new_message=user_content):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        response_text = event.content.parts[0].text
                    break

            return response_text or "Request processed."
        except Exception as e:
            error_str = str(e).lower()
            if any(k in error_str for k in ["429", "rate", "quota", "resource_exhausted"]):
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (2 ** attempt) + random.uniform(0, 3)
                    logger.warning(f"Rate limited, retrying in {delay:.1f}s (attempt {attempt+1}/{MAX_RETRIES})")
                    await asyncio.sleep(delay)
                    continue
            raise
    return "Rate limit reached after retries. Please wait a moment."


async def delegate_to_task_agent(user_message: str) -> dict:
    """
    Route a task-management query to the Task Agent via A2A protocol.

    Args:
        user_message: The user's natural language request about tasks.

    Returns:
        dict with the Task Agent's response.
    """
    try:
        response = await _run_agent_with_retry(task_agent, user_message)
        return {"agent": "task_agent", "response": response}
    except Exception as e:
        logger.error(f"Task Agent A2A error: {e}")
        return {"agent": "task_agent", "error": str(e)}


async def delegate_to_schedule_agent(user_message: str) -> dict:
    """
    Route a schedule/calendar query to the Schedule Agent via A2A protocol.

    Args:
        user_message: The user's natural language request about schedules, events, or calendar.

    Returns:
        dict with the Schedule Agent's response.
    """
    try:
        response = await _run_agent_with_retry(schedule_agent, user_message)
        return {"agent": "schedule_agent", "response": response}
    except Exception as e:
        logger.error(f"Schedule Agent A2A error: {e}")
        return {"agent": "schedule_agent", "error": str(e)}


TODAY = date.today().isoformat()

coordinator_agent = Agent(
    name="coordinator_agent",
    model=settings.gemini_model,
    description="Routes user queries to the correct specialist agent.",
    instruction=f"""You are the Coordinator Agent for the Personal Intelligence Hub.
Your job is to understand the user's intent and delegate to the correct specialist agent.
Today's date is {TODAY}.

You have TWO sub-agents available:

1. Task Agent - handles task management: creating, listing, updating, deleting tasks,
   and anything related to to-dos, work items, or task priorities.
   Use delegate_to_task_agent for these queries.

2. Schedule Agent - handles calendar and scheduling: creating events, listing events,
   checking daily schedules, detecting conflicts, and managing appointments/meetings.
   Use delegate_to_schedule_agent for these queries.

IMPORTANT: When the user says relative dates like "tomorrow", "next Monday", "in 2 hours",
YOU must convert them to actual dates/times before delegating. Today is {TODAY}.

Routing rules:
- Keywords like task, todo, to-do, work item, priority, assign -> Task Agent
- Keywords like schedule, event, meeting, appointment, calendar, book, slot,
  free time, conflict, daily summary, agenda -> Schedule Agent
- If unclear, ask the user to clarify.
- For general greetings or questions, respond directly without delegating.

Always relay the sub-agent's response back to the user clearly and in a friendly way.
Never ask the user for date formats - figure it out yourself.
Never make up data - always delegate to the appropriate agent.""",
    tools=[
        FunctionTool(func=delegate_to_task_agent),
        FunctionTool(func=delegate_to_schedule_agent),
    ],
)

