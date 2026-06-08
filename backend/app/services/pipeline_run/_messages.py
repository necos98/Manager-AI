"""Pipeline message operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline_run import PipelineMessage


async def add_message(
    run_id: str,
    sender_agent_name: str,
    content: str,
    session: AsyncSession,
) -> dict:
    """Add a message to a pipeline run."""
    msg = PipelineMessage(
        pipeline_run_id=run_id,
        sender_agent_name=sender_agent_name,
        content=content,
    )
    session.add(msg)
    await session.flush()
    return {
        "id": msg.id,
        "pipeline_run_id": msg.pipeline_run_id,
        "sender_agent_name": msg.sender_agent_name,
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


async def get_messages(
    run_id: str,
    session: AsyncSession,
) -> list[dict]:
    """Get all messages for a pipeline run."""
    result = await session.execute(
        select(PipelineMessage)
        .where(PipelineMessage.pipeline_run_id == run_id)
        .order_by(PipelineMessage.created_at)
    )
    msgs = result.scalars().all()
    return [
        {
            "id": m.id,
            "pipeline_run_id": m.pipeline_run_id,
            "sender_agent_name": m.sender_agent_name,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]
