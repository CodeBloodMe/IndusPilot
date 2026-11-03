"""0003_supplier_comparison_and_requisitions

Revision ID: c19d45e7832a
Revises: b9872ca86f1f
Create Date: 2026-11-03 17:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c19d45e7832a'
down_revision: Union[str, Sequence[str], None] = 'b9872ca86f1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update purchase_requisitions table with comparison references
    with op.batch_alter_table('purchase_requisitions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('selected_supplier_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('selected_quotation_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('estimated_total_cost', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('delivery_deadline', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('comparison_result_id', sa.String(), nullable=True))

    # 2. Create supplier_comparison_requests table
    op.create_table(
        'supplier_comparison_requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('material_id', sa.String(), nullable=True),
        sa.Column('material_name', sa.String(length=255), nullable=False),
        sa.Column('target_quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('delivery_deadline', sa.DateTime(), nullable=True),
        sa.Column('budget_limit', sa.Float(), nullable=True),
        sa.Column('weights_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('supplier_comparison_requests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_supplier_comparison_requests_material_id'), ['material_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_supplier_comparison_requests_organization_id'), ['organization_id'], unique=False)

    # 3. Create supplier_comparison_results table
    op.create_table(
        'supplier_comparison_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('request_id', sa.String(), nullable=False),
        sa.Column('recommended_supplier_id', sa.String(), nullable=True),
        sa.Column('recommended_quotation_id', sa.String(), nullable=True),
        sa.Column('lowest_cost_supplier_id', sa.String(), nullable=True),
        sa.Column('fastest_supplier_id', sa.String(), nullable=True),
        sa.Column('highest_quality_supplier_id', sa.String(), nullable=True),
        sa.Column('summary_headline', sa.String(length=500), nullable=True),
        sa.Column('concise_recommendation', sa.Text(), nullable=True),
        sa.Column('detailed_explanation', sa.Text(), nullable=True),
        sa.Column('evaluated_count', sa.Integer(), nullable=True),
        sa.Column('eligible_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id'], ),
        sa.ForeignKeyConstraint(['recommended_quotation_id'], ['supplier_quotations.id'], ),
        sa.ForeignKeyConstraint(['recommended_supplier_id'], ['suppliers.id'], ),
        sa.ForeignKeyConstraint(['request_id'], ['supplier_comparison_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('supplier_comparison_results', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_supplier_comparison_results_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_supplier_comparison_results_request_id'), ['request_id'], unique=False)

    # 4. Create supplier_comparison_candidates table
    op.create_table(
        'supplier_comparison_candidates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('comparison_result_id', sa.String(), nullable=False),
        sa.Column('quotation_id', sa.String(), nullable=False),
        sa.Column('supplier_id', sa.String(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('eligibility_status', sa.String(length=50), nullable=True),
        sa.Column('ineligibility_reasons_json', sa.JSON(), nullable=True),
        sa.Column('effective_unit_landed_cost', sa.Float(), nullable=False),
        sa.Column('total_landed_cost', sa.Float(), nullable=False),
        sa.Column('composite_score', sa.Float(), nullable=False),
        sa.Column('decision_band', sa.String(length=50), nullable=True),
        sa.Column('data_completeness_pct', sa.Float(), nullable=True),
        sa.Column('scorecard_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['comparison_result_id'], ['supplier_comparison_results.id'], ),
        sa.ForeignKeyConstraint(['quotation_id'], ['supplier_quotations.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('supplier_comparison_candidates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_supplier_comparison_candidates_comparison_result_id'), ['comparison_result_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_supplier_comparison_candidates_quotation_id'), ['quotation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_supplier_comparison_candidates_supplier_id'), ['supplier_id'], unique=False)


def downgrade() -> None:
    op.drop_table('supplier_comparison_candidates')
    op.drop_table('supplier_comparison_results')
    op.drop_table('supplier_comparison_requests')
    with op.batch_alter_table('purchase_requisitions', schema=None) as batch_op:
        batch_op.drop_column('comparison_result_id')
        batch_op.drop_column('delivery_deadline')
        batch_op.drop_column('estimated_total_cost')
        batch_op.drop_column('selected_quotation_id')
        batch_op.drop_column('selected_supplier_id')

