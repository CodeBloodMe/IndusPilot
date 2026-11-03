"""0004_manufacturing_intelligence

Revision ID: d28e75e8933c
Revises: c19d45e7832a
Create Date: 2026-11-03 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd28e75e8933c'
down_revision: Union[str, Sequence[str], None] = 'c19d45e7832a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update products
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('manufacturing_process', sa.String(length=100), nullable=True, server_default='CNC Machining & Sheet Fabrication'))
        batch_op.add_column(sa.Column('base_unit', sa.String(length=50), nullable=True, server_default='units'))
        batch_op.add_column(sa.Column('default_batch_size', sa.Float(), nullable=True, server_default='500.0'))
        batch_op.add_column(sa.Column('estimated_duration_hours', sa.Float(), nullable=True, server_default='24.0'))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))

    # 2. Update bills_of_materials
    with op.batch_alter_table('bills_of_materials', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(length=255), nullable=True, server_default='Primary Production BOM'))
        batch_op.add_column(sa.Column('effective_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('revision_status', sa.String(length=50), nullable=True, server_default='ACTIVE'))
        batch_op.add_column(sa.Column('scrap_allowance_method', sa.String(length=50), nullable=True, server_default='ADDITIVE_SCRAP'))
        batch_op.add_column(sa.Column('expected_yield_pct', sa.Float(), nullable=True, server_default='95.0'))
        batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))

    # 3. Update bom_items
    with op.batch_alter_table('bom_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('scrap_allowance_method', sa.String(length=50), nullable=True, server_default='ADDITIVE_SCRAP'))
        batch_op.add_column(sa.Column('expected_yield_pct', sa.Float(), nullable=True, server_default='95.0'))

    # 4. Update inventory
    with op.batch_alter_table('inventory', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reorder_quantity', sa.Float(), nullable=True, server_default='200.0'))
        batch_op.add_column(sa.Column('unit_cost_valuation', sa.Float(), nullable=True, server_default='0.0'))

    # 5. Update inventory_movements
    with op.batch_alter_table('inventory_movements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit', sa.String(length=50), nullable=True, server_default='kg'))
        batch_op.add_column(sa.Column('source', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('destination', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('user_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('unit_cost', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('production_job_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_inventory_movements_idempotency_key'), ['idempotency_key'], unique=False)

    # 6. Create stock_reservations
    op.create_table(
        'stock_reservations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('material_id', sa.String(), nullable=False),
        sa.Column('production_job_id', sa.String(), nullable=True),
        sa.Column('reserved_quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='ACTIVE'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('released_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('stock_reservations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_stock_reservations_material_id'), ['material_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_stock_reservations_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_stock_reservations_production_job_id'), ['production_job_id'], unique=False)

    # 7. Create production_jobs
    op.create_table(
        'production_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('job_number', sa.String(length=100), nullable=False),
        sa.Column('customer_order_ref', sa.String(length=100), nullable=True),
        sa.Column('product_id', sa.String(), nullable=False),
        sa.Column('bom_id', sa.String(), nullable=False),
        sa.Column('production_quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True, server_default='units'),
        sa.Column('planned_start_date', sa.DateTime(), nullable=True),
        sa.Column('target_completion_date', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=True, server_default='MEDIUM'),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='PLANNED'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['bom_id'], ['bills_of_materials.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('production_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_production_jobs_job_number'), ['job_number'], unique=True)
        batch_op.create_index(batch_op.f('ix_production_jobs_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_production_jobs_product_id'), ['product_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_production_jobs_bom_id'), ['bom_id'], unique=False)

    # 8. Create production_job_materials
    op.create_table(
        'production_job_materials',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('production_job_id', sa.String(), nullable=False),
        sa.Column('material_id', sa.String(), nullable=False),
        sa.Column('net_quantity_required', sa.Float(), nullable=False),
        sa.Column('gross_quantity_required', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True, server_default='kg'),
        sa.Column('scrap_quantity', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('available_stock', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('shortage_quantity', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('is_covered', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('requisition_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['production_job_id'], ['production_jobs.id'], ),
        sa.ForeignKeyConstraint(['requisition_id'], ['purchase_requisitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('production_job_materials', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_production_job_materials_material_id'), ['material_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_production_job_materials_production_job_id'), ['production_job_id'], unique=False)

    # 9. Update production_cost_estimates
    with op.batch_alter_table('production_cost_estimates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('estimate_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('calculation_version', sa.String(length=50), nullable=True, server_default='v1.0'))
        batch_op.add_column(sa.Column('data_quality_status', sa.String(length=50), nullable=True, server_default='COMPLETE'))
        batch_op.add_column(sa.Column('currency', sa.String(length=10), nullable=True, server_default='INR'))
        batch_op.add_column(sa.Column('break_even_price', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('effective_selling_price', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('effective_margin_pct', sa.Float(), nullable=True, server_default='25.0'))
        batch_op.add_column(sa.Column('markup_pct', sa.Float(), nullable=True, server_default='33.33'))
        batch_op.add_column(sa.Column('overhead_allocation_method', sa.String(length=50), nullable=True, server_default='PERCENTAGE_PRIME_COST'))
        batch_op.add_column(sa.Column('is_loss_making', sa.Boolean(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('assumptions_snapshot_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('items_breakdown_json', sa.JSON(), nullable=True))
        batch_op.create_index(batch_op.f('ix_production_cost_estimates_estimate_number'), ['estimate_number'], unique=False)

    # 10. Create costing_scenarios
    op.create_table(
        'costing_scenarios',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('cost_estimate_id', sa.String(), nullable=False),
        sa.Column('scenario_name', sa.String(length=255), nullable=False),
        sa.Column('scenario_description', sa.Text(), nullable=True),
        sa.Column('input_parameters_json', sa.JSON(), nullable=False),
        sa.Column('simulated_results_json', sa.JSON(), nullable=False),
        sa.Column('delta_total_cost', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('delta_unit_cost', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('delta_margin_pct', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cost_estimate_id'], ['production_cost_estimates.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('costing_scenarios', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_costing_scenarios_cost_estimate_id'), ['cost_estimate_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_costing_scenarios_organization_id'), ['organization_id'], unique=False)


def downgrade() -> None:
    op.drop_table('costing_scenarios')
    with op.batch_alter_table('production_cost_estimates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_production_cost_estimates_estimate_number'))
        batch_op.drop_column('items_breakdown_json')
        batch_op.drop_column('assumptions_snapshot_json')
        batch_op.drop_column('is_loss_making')
        batch_op.drop_column('overhead_allocation_method')
        batch_op.drop_column('markup_pct')
        batch_op.drop_column('effective_margin_pct')
        batch_op.drop_column('effective_selling_price')
        batch_op.drop_column('break_even_price')
        batch_op.drop_column('currency')
        batch_op.drop_column('data_quality_status')
        batch_op.drop_column('calculation_version')
        batch_op.drop_column('estimate_number')

    op.drop_table('production_job_materials')
    op.drop_table('production_jobs')
    op.drop_table('stock_reservations')

    with op.batch_alter_table('inventory_movements', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_inventory_movements_idempotency_key'))
        batch_op.drop_column('idempotency_key')
        batch_op.drop_column('production_job_id')
        batch_op.drop_column('unit_cost')
        batch_op.drop_column('user_id')
        batch_op.drop_column('destination')
        batch_op.drop_column('source')
        batch_op.drop_column('unit')

    with op.batch_alter_table('inventory', schema=None) as batch_op:
        batch_op.drop_column('unit_cost_valuation')
        batch_op.drop_column('reorder_quantity')

    with op.batch_alter_table('bom_items', schema=None) as batch_op:
        batch_op.drop_column('expected_yield_pct')
        batch_op.drop_column('scrap_allowance_method')

    with op.batch_alter_table('bills_of_materials', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('notes')
        batch_op.drop_column('expected_yield_pct')
        batch_op.drop_column('scrap_allowance_method')
        batch_op.drop_column('revision_status')
        batch_op.drop_column('effective_date')
        batch_op.drop_column('name')

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('is_active')
        batch_op.drop_column('estimated_duration_hours')
        batch_op.drop_column('default_batch_size')
        batch_op.drop_column('base_unit')
        batch_op.drop_column('manufacturing_process')

