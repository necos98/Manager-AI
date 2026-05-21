import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.agent import Agent
from app.models.agent_message import AgentMessage
from app.models.issue import Issue, IssueStatus
from app.models.pipeline import AgentStepRun, AgentStepStatus, Pipeline, PipelineRun, PipelineRunStatus
from app.services.issue_service import IssueService
from app.services.orchestrator_service import OrchestratorService
from app.services.project_service import ProjectService
import app.mcp.server as mcp_server


@pytest.mark.asyncio
async def test_ensure_default_agents(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    assert len(agents) == 5
    role_keys = {a.role_key for a in agents}
    assert role_keys == {"spec_writer", "architect", "developer", "reviewer", "qa"}

    # Idempotent: second call returns same count
    agents2 = await orch.ensure_default_agents(project.id)
    assert len(agents2) == 5


@pytest.mark.asyncio
async def test_ensure_default_pipeline(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    assert pipeline is not None
    assert pipeline.is_default is True
    assert pipeline.trigger_type == "issue_accepted"
    import json
    steps = json.loads(pipeline.steps)
    assert len(steps) == 5


@pytest.mark.asyncio
async def test_create_agent_via_model(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    agent = Agent(
        project_id=project.id,
        name="SecurityReview",
        role_key="security",
        system_prompt="You are a security reviewer.",
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    assert agent.id is not None
    assert agent.enabled is True
    assert agent.system_prompt == "You are a security reviewer."


@pytest.mark.asyncio
async def test_create_pipeline_run(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test issue", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    pipeline_run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        trigger_type="issue_accepted",
        status=PipelineRunStatus.RUNNING,
    )
    db_session.add(pipeline_run)
    await db_session.commit()
    await db_session.refresh(pipeline_run)

    assert pipeline_run.id is not None
    assert pipeline_run.status == PipelineRunStatus.RUNNING
    assert pipeline_run.issue_id == issue.id


@pytest.mark.asyncio
async def test_send_agent_message(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    msg = AgentMessage(
        issue_id=issue.id,
        agent_name="Architect",
        agent_role="architect",
        content="Architecture decision: use microservices.",
        message_type="decision",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)

    assert msg.id is not None
    assert msg.message_type == "decision"
    assert msg.agent_role == "architect"

    # Read back
    result = await db_session.execute(
        select(AgentMessage).where(AgentMessage.issue_id == issue.id).order_by(AgentMessage.created_at)
    )
    messages = result.scalars().all()
    assert len(messages) == 1
    assert messages[0].content == "Architecture decision: use microservices."


@pytest.mark.asyncio
async def test_agent_step_run_lifecycle(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    pipeline_run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        trigger_type="manual",
    )
    db_session.add(pipeline_run)
    await db_session.flush()

    step = AgentStepRun(
        pipeline_run_id=pipeline_run.id,
        agent_id=agents[0].id,
        agent_name=agents[0].name,
        agent_role=agents[0].role_key,
        step_order=0,
        status=AgentStepStatus.PENDING,
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    assert step.status == AgentStepStatus.PENDING

    step.status = AgentStepStatus.RUNNING
    step.started_at = step.started_at  # would be set by orchestrator
    await db_session.commit()

    step.status = AgentStepStatus.COMPLETED
    step.summary = "Architecture designed."
    await db_session.commit()
    await db_session.refresh(step)

    assert step.status == AgentStepStatus.COMPLETED
    assert step.summary == "Architecture designed."


@pytest.mark.asyncio
async def test_pipeline_completion(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    pipeline_run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        trigger_type="manual",
    )
    db_session.add(pipeline_run)
    await db_session.flush()

    for i, agent in enumerate(agents):
        step = AgentStepRun(
            pipeline_run_id=pipeline_run.id,
            agent_id=agent.id,
            agent_name=agent.name,
            agent_role=agent.role_key,
            step_order=i,
            status=AgentStepStatus.COMPLETED,
        )
        db_session.add(step)

    await db_session.commit()

    result = await db_session.execute(
        select(AgentStepRun).where(AgentStepRun.pipeline_run_id == pipeline_run.id)
    )
    steps = result.scalars().all()
    assert len(steps) == 5
    assert all(s.status == AgentStepStatus.COMPLETED for s in steps)


@pytest.mark.asyncio
async def test_complete_agent_step_transition(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    pipeline_run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        trigger_type="manual",
    )
    db_session.add(pipeline_run)
    await db_session.flush()

    step = AgentStepRun(
        pipeline_run_id=pipeline_run.id,
        agent_id=agents[0].id,
        agent_name=agents[0].name,
        agent_role=agents[0].role_key,
        step_order=0,
        status=AgentStepStatus.RUNNING,
    )
    db_session.add(step)
    await db_session.commit()

    result = await orch.complete_agent_step(pipeline_run.id, "Done with architecture")
    assert result["completed"] is True
    assert result["step_id"] == step.id

    await db_session.refresh(step)
    assert step.status == AgentStepStatus.COMPLETED
    assert step.summary == "Done with architecture"


@pytest.mark.asyncio
async def test_get_pipeline_status(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    pipeline_run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        trigger_type="manual",
    )
    db_session.add(pipeline_run)
    await db_session.flush()

    step = AgentStepRun(
        pipeline_run_id=pipeline_run.id,
        agent_id=agents[0].id,
        agent_name=agents[0].name,
        agent_role=agents[0].role_key,
        step_order=0,
        status=AgentStepStatus.PENDING,
    )
    db_session.add(step)
    await db_session.commit()

    status = await orch.get_pipeline_status(pipeline_run.id)
    assert "pipeline_run" in status
    assert status["pipeline_run"]["status"] == "running"
    assert len(status["steps"]) == 1
    assert status["steps"][0]["status"] == "pending"


# ── MCP-level Agent CRUD tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_create_agent(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.create_agent(
            project_id=project.id,
            name="CustomAgent",
            role_key="custom",
            system_prompt="You are a custom agent.",
        )

    assert "error" not in result
    assert result["name"] == "CustomAgent"
    assert result["role_key"] == "custom"
    assert result["project_id"] == project.id
    assert result["enabled"] is True


@pytest.mark.asyncio
async def test_mcp_list_agents(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.list_agents(project_id=project.id)

    assert "agents" in result
    assert len(result["agents"]) == 5  # default agents seeded
    role_keys = {a["role_key"] for a in result["agents"]}
    assert role_keys == {"spec_writer", "architect", "developer", "reviewer", "qa"}


@pytest.mark.asyncio
async def test_mcp_update_agent(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    agent = Agent(
        project_id=project.id, name="OldName", role_key="test", system_prompt="Old prompt"
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.update_agent(
            agent_id=agent.id,
            name="NewName",
            system_prompt="New prompt",
            enabled=False,
        )

    assert result["name"] == "NewName"
    assert result["system_prompt"] == "New prompt"
    assert result["enabled"] is False


@pytest.mark.asyncio
async def test_mcp_delete_agent(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    agent = Agent(
        project_id=project.id, name="ToDelete", role_key="temp", system_prompt=""
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.delete_agent(agent_id=agent.id)

    assert result == {"deleted": True}

    # Verify gone
    deleted = await db_session.get(Agent, agent.id)
    assert deleted is None


@pytest.mark.asyncio
async def test_mcp_delete_agent_not_found(db_session):
    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.delete_agent(agent_id=str(uuid.uuid4()))

    assert result == {"error": "Agent not found"}


@pytest.mark.asyncio
async def test_mcp_update_agent_not_found(db_session):
    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.update_agent(agent_id=str(uuid.uuid4()), name="X")

    assert result == {"error": "Agent not found"}


# ── MCP-level Pipeline CRUD tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_create_pipeline(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)

    steps = [
        {"agent_id": agents[0].id, "order": 0},
        {"agent_id": agents[1].id, "order": 1},
    ]

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.create_pipeline(
            project_id=project.id,
            name="Custom Pipeline",
            steps=steps,
        )

    assert "error" not in result
    assert result["name"] == "Custom Pipeline"
    assert result["trigger_type"] == "issue_accepted"
    parsed_steps = json.loads(result["steps"]) if isinstance(result["steps"], str) else result["steps"]
    assert len(parsed_steps) == 2


@pytest.mark.asyncio
async def test_mcp_create_pipeline_as_default(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)

    # Create first default
    steps1 = [{"agent_id": agents[0].id, "order": 0}]

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        r1 = await mcp_server.create_pipeline(
            project_id=project.id, name="First", steps=steps1, is_default=True
        )
        # Create second default — should unset first
        r2 = await mcp_server.create_pipeline(
            project_id=project.id, name="Second", steps=steps1, is_default=True
        )

    assert r1["is_default"] is True
    assert r2["is_default"] is True

    # Verify first is no longer default
    pipeline1 = await db_session.get(Pipeline, r1["id"])
    await db_session.refresh(pipeline1)
    assert pipeline1.is_default is False


@pytest.mark.asyncio
async def test_mcp_list_pipelines(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    await orch.ensure_default_pipeline(project.id)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.list_pipelines(project_id=project.id)

    assert "pipelines" in result
    assert len(result["pipelines"]) >= 1
    default = next(p for p in result["pipelines"] if p["is_default"])
    assert default["name"] == "Default"
    assert default["trigger_type"] == "issue_accepted"


@pytest.mark.asyncio
async def test_mcp_update_pipeline(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.update_pipeline(
            pipeline_id=pipeline.id,
            name="Updated Pipeline",
            trigger_type="manual",
        )

    assert result["name"] == "Updated Pipeline"
    assert result["trigger_type"] == "manual"


@pytest.mark.asyncio
async def test_mcp_delete_pipeline(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.delete_pipeline(pipeline_id=pipeline.id)

    assert result == {"deleted": True}

    deleted = await db_session.get(Pipeline, pipeline.id)
    assert deleted is None


# ── Pipeline Execution tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_pipeline_manual(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test issue", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    # Disable _run_pipeline to avoid background Claude Code spawn
    with patch.object(OrchestratorService, "_run_pipeline", return_value=None):
        pipeline_run = await orch.start_pipeline(
            trigger_type="manual", issue_id=issue.id
        )

    assert pipeline_run is not None
    assert pipeline_run.trigger_type == "manual"
    assert pipeline_run.issue_id == issue.id
    assert pipeline_run.status == PipelineRunStatus.RUNNING

    # Verify step runs created
    steps_result = await db_session.execute(
        select(AgentStepRun).where(
            AgentStepRun.pipeline_run_id == pipeline_run.id
        ).order_by(AgentStepRun.step_order)
    )
    steps = steps_result.scalars().all()
    assert len(steps) == 5
    assert all(s.status == AgentStepStatus.PENDING for s in steps)


@pytest.mark.asyncio
async def test_start_pipeline_no_default(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    # No agents, no pipeline
    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    orch = OrchestratorService(db_session)
    pipeline_run = await orch.start_pipeline(
        trigger_type="manual", issue_id=issue.id
    )

    assert pipeline_run is None


@pytest.mark.asyncio
async def test_start_pipeline_bad_issue(db_session):
    orch = OrchestratorService(db_session)
    pipeline_run = await orch.start_pipeline(
        trigger_type="manual", issue_id=str(uuid.uuid4())
    )

    assert pipeline_run is None


@pytest.mark.asyncio
async def test_mcp_start_pipeline(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        with patch.object(OrchestratorService, "_run_pipeline", return_value=None):
            result = await mcp_server.start_pipeline(issue_id=issue.id)

    assert "pipeline_run_id" in result
    assert result["status"] == "running"
    assert result["trigger_type"] == "manual"


@pytest.mark.asyncio
async def test_mcp_send_agent_message(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.send_agent_message(
            issue_id=issue.id,
            content="Testing the message flow.",
            message_type="status",
        )

    assert result["content"] == "Testing the message flow."
    assert result["message_type"] == "status"
    assert result["issue_id"] == issue.id


@pytest.mark.asyncio
async def test_mcp_send_agent_message_invalid_type(db_session):
    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.send_agent_message(
            issue_id=str(uuid.uuid4()),
            content="Bad type",
            message_type="invalid",
        )

    assert result == {"error": "message_type must be one of: context, decision, question, answer, status"}


@pytest.mark.asyncio
async def test_mcp_get_agent_messages(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    # Create two messages
    msg1 = AgentMessage(issue_id=issue.id, agent_name="A", agent_role="architect", content="First", message_type="context")
    msg2 = AgentMessage(issue_id=issue.id, agent_name="B", agent_role="developer", content="Second", message_type="decision")
    db_session.add_all([msg1, msg2])
    await db_session.commit()

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_agent_messages(issue_id=issue.id)

    assert "messages" in result
    assert len(result["messages"]) == 2
    assert result["messages"][0]["content"] == "First"
    assert result["messages"][1]["content"] == "Second"


@pytest.mark.asyncio
async def test_mcp_get_pipeline_status(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    pipeline_run = PipelineRun(
        pipeline_id=pipeline.id, issue_id=issue.id, trigger_type="manual"
    )
    db_session.add(pipeline_run)
    await db_session.flush()

    step = AgentStepRun(
        pipeline_run_id=pipeline_run.id, agent_id=agents[0].id,
        agent_name=agents[0].name, agent_role=agents[0].role_key,
        step_order=0, status=AgentStepStatus.PENDING,
    )
    db_session.add(step)
    await db_session.commit()

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_pipeline_status(pipeline_run_id=pipeline_run.id)

    assert "pipeline_run" in result
    assert result["pipeline_run"]["status"] == "running"
    assert len(result["steps"]) == 1


@pytest.mark.asyncio
async def test_mcp_get_pipeline_status_not_found(db_session):
    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_pipeline_status(pipeline_run_id=str(uuid.uuid4()))

    assert result == {"error": "Pipeline run not found"}


# ── accept_issue → auto-start pipeline test ────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_accept_issue_triggers_pipeline(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    # Seed default agents + pipeline
    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    await orch.ensure_default_pipeline(project.id)

    # Create issue in both YAML (IssueService) AND SQLAlchemy (Issue model)
    # IssueService handles YAML store, OrchestratorService reads from DB
    issue_service = IssueService(db_session)
    issue_record = await issue_service.create(project_id=project.id, description="Auto-trigger test", priority=2)
    await issue_service.create_spec(issue_record.id, project.id, "# Spec")
    await issue_service.create_plan(issue_record.id, project.id, "# Plan")
    await db_session.commit()

    # Also persist a SQLAlchemy Issue so OrchestratorService can find it
    issue = Issue(
        id=issue_record.id,
        project_id=project.id,
        description="Auto-trigger test",
        priority=2,
        status="Planned",
    )
    db_session.add(issue)
    await db_session.commit()

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        with patch.object(OrchestratorService, "_run_pipeline", return_value=None):
            result = await mcp_server.accept_issue(
                project_id=project.id, issue_id=issue.id
            )

    assert result["id"] == issue.id
    assert result["status"] == IssueStatus.ACCEPTED.value
    assert "pipeline_run_id" in result

    # Verify PipelineRun exists
    pipeline_run = await db_session.get(PipelineRun, result["pipeline_run_id"])
    assert pipeline_run is not None
    assert pipeline_run.trigger_type == "issue_accepted"
    assert pipeline_run.issue_id == issue.id

    # Verify AgentStepRuns created — issue is Planned/Accepted, so starts from developer (3 steps)
    steps_result = await db_session.execute(
        select(AgentStepRun).where(
            AgentStepRun.pipeline_run_id == pipeline_run.id
        ).order_by(AgentStepRun.step_order)
    )
    steps = steps_result.scalars().all()
    assert len(steps) == 3
    role_order = [s.agent_role for s in steps]
    assert role_order == ["developer", "reviewer", "qa"]


@pytest.mark.asyncio
async def test_mcp_complete_agent_step(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    pipeline_run = PipelineRun(
        pipeline_id=pipeline.id, issue_id=issue.id, trigger_type="manual"
    )
    db_session.add(pipeline_run)
    await db_session.flush()

    step = AgentStepRun(
        pipeline_run_id=pipeline_run.id, agent_id=agents[0].id,
        agent_name=agents[0].name, agent_role=agents[0].role_key,
        step_order=0, status=AgentStepStatus.RUNNING,
    )
    db_session.add(step)
    await db_session.commit()

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.complete_agent_step(
            pipeline_run_id=pipeline_run.id,
            summary="MCP-level completion test",
        )

    assert result["completed"] is True
    assert result["step_id"] == step.id

    await db_session.refresh(step)
    assert step.status == AgentStepStatus.COMPLETED
    assert step.summary == "MCP-level completion test"


@pytest.mark.asyncio
async def test_mcp_complete_agent_step_no_running_step(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    pipeline = await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    pipeline_run = PipelineRun(
        pipeline_id=pipeline.id, issue_id=issue.id, trigger_type="manual"
    )
    db_session.add(pipeline_run)
    await db_session.flush()

    # No steps — all pending, none running
    step = AgentStepRun(
        pipeline_run_id=pipeline_run.id, agent_id=agents[0].id,
        agent_name=agents[0].name, agent_role=agents[0].role_key,
        step_order=0, status=AgentStepStatus.PENDING,  # not RUNNING
    )
    db_session.add(step)
    await db_session.commit()

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.complete_agent_step(
            pipeline_run_id=pipeline_run.id,
            summary="Should not work",
        )

    assert result == {"error": "No running step found for this pipeline run"}


# ── Any-state pipeline start tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_pipeline_from_new_state(db_session, tmp_path):
    """Issue NEW → all 5 steps created (spec_writer through qa)."""
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="New issue", priority=3, status="New")
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    with patch.object(OrchestratorService, "_run_pipeline", return_value=None):
        pipeline_run = await orch.start_pipeline(trigger_type="manual", issue_id=issue.id)

    assert pipeline_run is not None

    steps_result = await db_session.execute(
        select(AgentStepRun).where(
            AgentStepRun.pipeline_run_id == pipeline_run.id
        ).order_by(AgentStepRun.step_order)
    )
    steps = steps_result.scalars().all()
    assert len(steps) == 5
    role_order = [s.agent_role for s in steps]
    assert role_order == ["spec_writer", "architect", "developer", "reviewer", "qa"]


@pytest.mark.asyncio
async def test_start_pipeline_from_reasoning_state(db_session, tmp_path):
    """Issue REASONING → skip spec_writer, 4 steps created."""
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Reasoning issue", priority=3, status="Reasoning")
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    with patch.object(OrchestratorService, "_run_pipeline", return_value=None):
        pipeline_run = await orch.start_pipeline(trigger_type="manual", issue_id=issue.id)

    assert pipeline_run is not None

    steps_result = await db_session.execute(
        select(AgentStepRun).where(
            AgentStepRun.pipeline_run_id == pipeline_run.id
        ).order_by(AgentStepRun.step_order)
    )
    steps = steps_result.scalars().all()
    assert len(steps) == 4
    role_order = [s.agent_role for s in steps]
    assert role_order == ["architect", "developer", "reviewer", "qa"]


@pytest.mark.asyncio
async def test_start_pipeline_from_planned_state(db_session, tmp_path):
    """Issue PLANNED → skip spec_writer + architect, 3 steps created."""
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Planned issue", priority=3, status="Planned")
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    with patch.object(OrchestratorService, "_run_pipeline", return_value=None):
        pipeline_run = await orch.start_pipeline(trigger_type="manual", issue_id=issue.id)

    assert pipeline_run is not None

    steps_result = await db_session.execute(
        select(AgentStepRun).where(
            AgentStepRun.pipeline_run_id == pipeline_run.id
        ).order_by(AgentStepRun.step_order)
    )
    steps = steps_result.scalars().all()
    assert len(steps) == 3
    role_order = [s.agent_role for s in steps]
    assert role_order == ["developer", "reviewer", "qa"]


@pytest.mark.asyncio
async def test_start_pipeline_duplicate_prevented(db_session, tmp_path):
    """Second start_pipeline returns None while one is RUNNING."""
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    await orch.ensure_default_agents(project.id)
    await orch.ensure_default_pipeline(project.id)

    issue = Issue(project_id=project.id, description="Dup test", priority=3)
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    with patch.object(OrchestratorService, "_run_pipeline", return_value=None):
        run1 = await orch.start_pipeline(trigger_type="manual", issue_id=issue.id)
        run2 = await orch.start_pipeline(trigger_type="manual", issue_id=issue.id)

    assert run1 is not None
    assert run2 is None  # duplicate prevented


@pytest.mark.asyncio
async def test_spec_writer_system_prompt(db_session, tmp_path):
    """SpecWriter agent has correct system prompt with create_issue_spec/plan instructions."""
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)

    spec_writer = next((a for a in agents if a.role_key == "spec_writer"), None)
    assert spec_writer is not None
    assert "create_issue_spec" in spec_writer.system_prompt
    assert "create_issue_plan" in spec_writer.system_prompt
    assert "create_plan_tasks" in spec_writer.system_prompt
    assert "complete_agent_step" in spec_writer.system_prompt
