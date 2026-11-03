"""0005_procurement_optimization

Revision ID: e39f51a89b4d
Revises: d28e75e8933c
Create Date: 2026-11-03 20:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e39f51a89b4d'
down_revision: Union[str, None] = 'd28e75e8933c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'procurement_plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('plan_number', sa.String(length=100), nullable=False),
        sa.Column('production_job_id', sa.String(), nullable=True),
        sa.Column('strategy', sa.String(length=50), nullable=False, server_default='LOWEST_LANDED_COST'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('budget_limit', sa.Float(), nullable=True),
        sa.Column('max_suppliers_per_material', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('allow_split_purchasing', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('max_overbuy_pct', sa.Float(), nullable=False, server_default='10.0'),
        sa.Column('min_quality_rating', sa.Float(), nullable=False, server_default='3.5'),
        sa.Column('required_by_date', sa.DateTime(), nullable=True),
        sa.Column('solver_status', sa.String(length=50), nullable=False, server_default='OPTIMAL'),
        sa.Column('total_landed_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('budget_utilized_pct', sa.Float(), nullable=True),
        sa.Column('total_units_required', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_units_allocated', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('excess_units', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('baseline_comparison_json', sa.JSON(), nullable=True),
        sa.Column('explanation_headline', sa.String(length=500), nullable=True),
        sa.Column('explanation_detail', sa.Text(), nullable=True),
        sa.Column('input_snapshot_json', sa.JSON(), nullable=True),
        sa.Column('approval_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id'], ),
        sa.ForeignKeyConstraint(['production_job_id'], ['production_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_procurement_plans_organization_id'), 'procurement_plans', ['organization_id'], unique=False)
    op.create_index(op.f('ix_procurement_plans_plan_number'), 'procurement_plans', ['plan_number'], unique=True)
    op.create_index(op.f('ix_procurement_plans_production_job_id'), 'procurement_plans', ['production_job_id'], unique=False)

    op.create_table(
        'procurement_plan_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('procurement_plan_id', sa.String(), nullable=False),
        sa.Column('material_id', sa.String(), nullable=False),
        sa.Column('required_quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False, server_default='kg'),
        sa.Column('delivery_deadline', sa.DateTime(), nullable=True),
        sa.Column('allocated_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('allocated_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('shortage_quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['procurement_plan_id'], ['procurement_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_procurement_plan_items_material_id'), 'procurement_plan_items', ['material_id'], unique=False)
    op.create_index(op.f('ix_procurement_plan_items_procurement_plan_id'), 'procurement_plan_items', ['procurement_plan_id'], unique=False)

    op.create_table(
        'procurement_plan_allocations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('procurement_plan_id', sa.String(), nullable=False),
        sa.Column('material_id', sa.String(), nullable=False),
        sa.Column('supplier_id', sa.String(), nullable=False),
        sa.Column('quotation_id', sa.String(), nullable=True),
        sa.Column('allocated_quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False, server_default='kg'),
        sa.Column('unit_landed_cost', sa.Float(), nullable=False),
        sa.Column('subtotal_cost', sa.Float(), nullable=False),
        sa.Column('fixed_freight_allocated', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('moq', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('moq_satisfied', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('package_count', sa.Integer(), nullable=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('delivery_date', sa.DateTime(), nullable=True),
        sa.Column('supplier_risk_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('quality_rating', sa.Float(), nullable=False, server_default='4.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['procurement_plan_id'], ['procurement_plans.id'], ),
        sa.ForeignKeyConstraint(['quotation_id'], ['supplier_quotations.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_procurement_plan_allocations_material_id'), 'procurement_plan_allocations', ['material_id'], unique=False)
    op.create_index(op.f('ix_procurement_plan_allocations_procurement_plan_id'), 'procurement_plan_allocations', ['procurement_plan_id'], unique=False)
    op.create_index(op.f('ix_procurement_plan_allocations_supplier_id'), 'procurement_plan_allocations', ['supplier_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_procurement_plan_allocations_supplier_id'), table_name='procurement_plan_allocations')
    op.drop_index(op.f('ix_procurement_plan_allocations_procurement_plan_id'), table_name='procurement_plan_allocations')
    op.drop_index(op.f('ix_procurement_plan_allocations_material_id'), table_name='procurement_plan_allocations')
    op.drop_table('procurement_plan_allocations')

    op.drop_index(op.f('ix_procurement_plan_items_procurement_plan_id'), table_name='procurement_plan_items')
    op.drop_index(op.f('ix_procurement_plan_items_material_id'), table_name='procurement_plan_items')
    op.drop_table('procurement_plan_items')

    op.drop_index(op.f('ix_procurement_plans_production_job_id'), table_name='procurement_plans')
    op.drop_index(op.f('ix_procurement_plans_plan_number'), table_name='procurement_plans')
    op.drop_index(op.f('ix_procurement_plans_organization_id'), table_name='procurement_plans')
    op.drop_table('procurement_plans')

