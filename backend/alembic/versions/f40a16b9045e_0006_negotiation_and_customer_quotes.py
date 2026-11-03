"""0006_negotiation_and_customer_quotes

Revision ID: f40a16b9045e
Revises: e39f51a89b4d
Create Date: 2026-11-03 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f40a16b9045e'
down_revision: Union[str, None] = 'e39f51a89b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create customers table
    op.create_table(
        'customers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('customer_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('billing_address', sa.Text(), nullable=True),
        sa.Column('shipping_address', sa.Text(), nullable=True),
        sa.Column('gst_number', sa.String(length=50), nullable=True),
        sa.Column('credit_limit', sa.Float(), nullable=True, server_default='500000.0'),
        sa.Column('payment_terms', sa.String(length=100), nullable=True, server_default='30 Days Net'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organisations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_customer_code'), 'customers', ['customer_code'], unique=True)
    op.create_index(op.f('ix_customers_organization_id'), 'customers', ['organization_id'], unique=False)

    # 2. Add columns to customer_quotations
    with op.batch_alter_table('customer_quotations') as batch_op:
        batch_op.add_column(sa.Column('customer_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('cost_estimate_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('markup_pct', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('min_margin_pct', sa.Float(), nullable=True, server_default='15.0'))
        batch_op.add_column(sa.Column('gross_profit', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('discount_pct', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('discount_amount', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('profitability_status', sa.String(length=50), nullable=True, server_default='PROFITABLE'))
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=True, server_default='1'))
        batch_op.add_column(sa.Column('pdf_path', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('approval_status', sa.String(length=50), nullable=True, server_default='DRAFT'))
        batch_op.add_column(sa.Column('approved_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('sent_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('customer_response', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('customer_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('items_json', sa.JSON(), nullable=True))
        batch_op.create_foreign_key('fk_customer_quotations_customer_id', 'customers', ['customer_id'], ['id'])
        batch_op.create_foreign_key('fk_customer_quotations_cost_estimate_id', 'production_cost_estimates', ['cost_estimate_id'], ['id'])

    # 3. Add columns to negotiation_sessions
    with op.batch_alter_table('negotiation_sessions') as batch_op:
        batch_op.add_column(sa.Column('session_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('material_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('material_specs', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('strategy', sa.String(length=50), nullable=True, server_default='BALANCED_COMMERCIAL'))
        batch_op.add_column(sa.Column('max_acceptable_price', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('original_landed_cost', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('current_landed_cost', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('final_agreed_price', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('final_landed_cost', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('net_savings_abs', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('net_savings_pct', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('delivery_deadline_days', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('payment_terms', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('competitor_quote_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('revised_quotation_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('approval_status', sa.String(length=50), nullable=True, server_default='DRAFT'))
        batch_op.add_column(sa.Column('approved_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('commercial_impact_json', sa.JSON(), nullable=True))
        batch_op.create_foreign_key('fk_negotiation_sessions_material_id', 'materials', ['material_id'], ['id'])
        batch_op.create_foreign_key('fk_negotiation_sessions_competitor_quote_id', 'supplier_quotations', ['competitor_quote_id'], ['id'])
        batch_op.create_foreign_key('fk_negotiation_sessions_revised_quotation_id', 'supplier_quotations', ['revised_quotation_id'], ['id'])

    # 4. Add columns to negotiation_messages
    with op.batch_alter_table('negotiation_messages') as batch_op:
        batch_op.add_column(sa.Column('language', sa.String(length=20), nullable=True, server_default='en'))
        batch_op.add_column(sa.Column('subject', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('extracted_terms_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('classification', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('email_dispatch_status', sa.String(length=50), nullable=True, server_default='SIMULATED'))
        batch_op.add_column(sa.Column('email_recipient', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('negotiation_messages') as batch_op:
        batch_op.drop_column('idempotency_key')
        batch_op.drop_column('email_recipient')
        batch_op.drop_column('email_dispatch_status')
        batch_op.drop_column('classification')
        batch_op.drop_column('extracted_terms_json')
        batch_op.drop_column('subject')
        batch_op.drop_column('language')

    with op.batch_alter_table('negotiation_sessions') as batch_op:
        batch_op.drop_constraint('fk_negotiation_sessions_revised_quotation_id', type_='foreignkey')
        batch_op.drop_constraint('fk_negotiation_sessions_competitor_quote_id', type_='foreignkey')
        batch_op.drop_constraint('fk_negotiation_sessions_material_id', type_='foreignkey')
        batch_op.drop_column('commercial_impact_json')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('approved_by')
        batch_op.drop_column('approval_status')
        batch_op.drop_column('revised_quotation_id')
        batch_op.drop_column('competitor_quote_id')
        batch_op.drop_column('payment_terms')
        batch_op.drop_column('delivery_deadline_days')
        batch_op.drop_column('net_savings_pct')
        batch_op.drop_column('net_savings_abs')
        batch_op.drop_column('final_landed_cost')
        batch_op.drop_column('final_agreed_price')
        batch_op.drop_column('current_landed_cost')
        batch_op.drop_column('original_landed_cost')
        batch_op.drop_column('max_acceptable_price')
        batch_op.drop_column('strategy')
        batch_op.drop_column('material_specs')
        batch_op.drop_column('material_id')
        batch_op.drop_column('session_number')

    with op.batch_alter_table('customer_quotations') as batch_op:
        batch_op.drop_constraint('fk_customer_quotations_cost_estimate_id', type_='foreignkey')
        batch_op.drop_constraint('fk_customer_quotations_customer_id', type_='foreignkey')
        batch_op.drop_column('items_json')
        batch_op.drop_column('customer_notes')
        batch_op.drop_column('customer_response')
        batch_op.drop_column('sent_at')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('approved_by')
        batch_op.drop_column('approval_status')
        batch_op.drop_column('pdf_path')
        batch_op.drop_column('version')
        batch_op.drop_column('profitability_status')
        batch_op.drop_column('discount_amount')
        batch_op.drop_column('discount_pct')
        batch_op.drop_column('gross_profit')
        batch_op.drop_column('min_margin_pct')
        batch_op.drop_column('markup_pct')
        batch_op.drop_column('cost_estimate_id')
        batch_op.drop_column('customer_id')

    op.drop_index(op.f('ix_customers_organization_id'), table_name='customers')
    op.drop_index(op.f('ix_customers_customer_code'), table_name='customers')
    op.drop_table('customers')

