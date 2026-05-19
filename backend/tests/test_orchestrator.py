import pytest
from sqlalchemy import select

from app.models.agent import Agent
from app.models.agent_message import AgentMessage
from app.models.issue import Issue
from app.models.pipeline import AgentStepRun, AgentStepStatus, Pipeline, PipelineRun, PipelineRunStatus
from app.services.orchestrator_service import OrchestratorService
from app.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_ensure_default_agents(db_session, tmp_path):
    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="", tech_stack=""
    )
    await db_session.commit()

    orch = OrchestratorService(db_session)
    agents = await orch.ensure_default_agents(project.id)
    assert len(agents) == 4
    role_keys = {a.role_key for a in agents}
    assert role_keys == {"architect", "developer", "reviewer", "qa"}

    # Idempotent: second call returns same count
    agents2 = await orch.ensure_default_agents(project.id)
    assert len(agents2) == 4


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
    assert len(steps) == 4


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
    assert len(steps) == 4
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
