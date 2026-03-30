import os
from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.task_agent import build_task_agent
from app.models import AgentSession
from app.config import settings
from datetime import datetime, timezone

APP_NAME = "intel_hub"

async def run_coordinator(
    message: str,
    session_id: str,
    db: AsyncSession,
) -> str:

    result = await db.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )
    agent_session = result.scalar_one_or_none()

    if not agent_session:
        agent_session = AgentSession(id=session_id, history=[])
        db.add(agent_session)
        await db.commit()

    task_agent = build_task_agent(db)

    coordinator = Agent(
        name="coordinator",
        model=settings.gemini_model,
        description="Primary coordinator that routes user requests to the right sub-agent.",
        instruction="""You are a personal intelligence hub coordinator.
You help users manage their tasks and productivity.
When the user wants to create, list, update, or delete tasks, delegate to task_agent.
Always respond in a friendly, concise manner.""",
        sub_agents=[task_agent],
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=coordinator,
        app_name=APP_NAME,
        session_service=session_service,
    )

    await session_service.create_session(
        app_name=APP_NAME,
        user_id="user",
        session_id=session_id,
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=message)],
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="user",
        session_id=session_id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    history_entry = {
        "user": message,
        "assistant": response_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    agent_session.history = (agent_session.history or []) + [history_entry]
    agent_session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return response_text or "I wasn't able to process that. Please try again."