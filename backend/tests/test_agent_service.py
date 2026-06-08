"""Tests for AgentService — seed_defaults, create, and provider handling."""

import pytest

from app.services.agent_service import AgentService


# ═════════════════════════════════════════════════════════════════════════════
# seed_defaults
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_seed_defaults_saves_provider(db_session):
    """seed_defaults creates agents with provider='claude' (from DEFAULT_AGENTS)."""
    svc = AgentService(db_session)
    agents = await svc.seed_defaults()
    assert len(agents) > 0
    for agent in agents:
        assert agent.provider == "claude"


@pytest.mark.asyncio
async def test_seed_defaults_is_idempotent(db_session):
    """seed_defaults returns existing agents on second call."""
    svc = AgentService(db_session)
    first = await svc.seed_defaults()
    second = await svc.seed_defaults()
    assert len(second) == len(first)
    # Same instances returned (no duplicates created)
    for a in second:
        assert a.id is not None


# ═════════════════════════════════════════════════════════════════════════════
# create
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_agent_with_custom_provider(db_session):
    """create() accepts an explicit provider='hermes'."""
    svc = AgentService(db_session)
    agent = await svc.create(
        name="TestHermes",
        provider="hermes",
        intent="Test agent with hermes provider",
    )
    try:
        assert agent.provider == "hermes"
        assert agent.name == "TestHermes"
        assert agent.intent == "Test agent with hermes provider"
    finally:
        await db_session.delete(agent)
        await db_session.flush()


@pytest.mark.asyncio
async def test_create_agent_default_provider(db_session):
    """create() defaults provider to 'claude'."""
    svc = AgentService(db_session)
    agent = await svc.create(name="DefaultProviderAgent", intent="Test")
    try:
        assert agent.provider == "claude"
    finally:
        await db_session.delete(agent)
        await db_session.flush()


@pytest.mark.asyncio
async def test_create_agent_with_model_and_tools(db_session):
    """create() accepts model and allowed_tools parameters."""
    svc = AgentService(db_session)
    agent = await svc.create(
        name="ModelAgent",
        model="claude-sonnet-4-20250514",
        allowed_tools=["read", "write", "bash"],
        intent="Test with model",
        provider="claude",
    )
    try:
        assert agent.model == "claude-sonnet-4-20250514"
        assert agent.allowed_tools == ["read", "write", "bash"]
        assert agent.provider == "claude"
    finally:
        await db_session.delete(agent)
        await db_session.flush()
