"""0007_copilot_and_multiagent_orchestration

Revision ID: a75b28d01e4f
Revises: f40a16b9045e
Create Date: 2026-11-03 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a75b28d01e4f'
down_revision: Union[str, None] = 'f40a16b9045e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. copilot_conversations
    op.create_table(
        'copilot_conversations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('context_state_json', sa.JSON(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_copilot_conversations_organization_id'), 'copilot_conversations', ['organization_id'], unique=False)
    op.create_index(op.f('ix_copilot_conversations_user_id'), 'copilot_conversations', ['user_id'], unique=False)

    # 2. agent_runs
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('selected_agents_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('workflow_state_json', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['copilot_conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_runs_conversation_id'), 'agent_runs', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_agent_runs_organization_id'), 'agent_runs', ['organization_id'], unique=False)

    # 3. copilot_messages
    op.create_table(
        'copilot_messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('structured_data_json', sa.JSON(), nullable=True),
        sa.Column('tool_calls_json', sa.JSON(), nullable=True),
        sa.Column('run_id', sa.String(length=100), nullable=True),
        sa.Column('requires_human_approval', sa.Boolean(), nullable=True, default=False),
        sa.Column('pending_action_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['copilot_conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_copilot_messages_conversation_id'), 'copilot_messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_copilot_messages_organization_id'), 'copilot_messages', ['organization_id'], unique=False)
    op.create_index(op.f('ix_copilot_messages_run_id'), 'copilot_messages', ['run_id'], unique=False)

    # 4. agent_run_steps
    op.create_table(
        'agent_run_steps',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False),
        sa.Column('step_type', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('input_json', sa.JSON(), nullable=True),
        sa.Column('output_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_run_steps_run_id'), 'agent_run_steps', ['run_id'], unique=False)

    # 5. agent_tool_calls
    op.create_table(
        'agent_tool_calls',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=True),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False),
        sa.Column('tool_name', sa.String(length=100), nullable=False),
        sa.Column('permission_tier', sa.String(length=50), nullable=True),
        sa.Column('input_arguments_json', sa.JSON(), nullable=False),
        sa.Column('output_result_json', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('execution_duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id']),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_tool_calls_organization_id'), 'agent_tool_calls', ['organization_id'], unique=False)
    op.create_index(op.f('ix_agent_tool_calls_run_id'), 'agent_tool_calls', ['run_id'], unique=False)

    # 6. pending_agent_actions
    op.create_table(
        'pending_agent_actions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('proposed_payload_json', sa.JSON(), nullable=False),
        sa.Column('financial_impact_summary', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('decision_by', sa.String(length=100), nullable=True),
        sa.Column('decision_reason', sa.Text(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id']),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_agent_actions_conversation_id'), 'pending_agent_actions', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_pending_agent_actions_organization_id'), 'pending_agent_actions', ['organization_id'], unique=False)
    op.create_index(op.f('ix_pending_agent_actions_run_id'), 'pending_agent_actions', ['run_id'], unique=False)

    # 7. workflow_checkpoints
    op.create_table(
        'workflow_checkpoints',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('checkpoint_id', sa.String(length=100), nullable=False),
        sa.Column('thread_id', sa.String(length=100), nullable=False),
        sa.Column('state_dump_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_checkpoints_run_id'), 'workflow_checkpoints', ['run_id'], unique=False)
    op.create_index(op.f('ix_workflow_checkpoints_thread_id'), 'workflow_checkpoints', ['thread_id'], unique=False)


def downgrade() -> None:
    op.drop_table('workflow_checkpoints')
    op.drop_table('pending_agent_actions')
    op.drop_table('agent_tool_calls')
    op.drop_table('agent_run_steps')
    op.drop_table('copilot_messages')
    op.drop_table('agent_runs')
    op.drop_table('copilot_conversations')

