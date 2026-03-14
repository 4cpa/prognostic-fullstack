"""add forecast sources and claims

Revision ID: cbdf80780206
Revises: 70c8941012ca
Create Date: 2026-03-14 10:54:39.020123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cbdf80780206"
down_revision: Union[str, None] = "70c8941012ca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    return index_name in existing


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "forecast_sources"):
        op.create_table(
            "forecast_sources",
            sa.Column("forecast_id", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("publisher", sa.String(), nullable=False),
            sa.Column("domain", sa.String(), nullable=True),
            sa.Column("source_type", sa.String(), nullable=False),
            sa.Column("published_at", sa.String(), nullable=True),
            sa.Column("query", sa.String(), nullable=True),
            sa.Column("retrieval_method", sa.String(), nullable=True),
            sa.Column("relevance_score", sa.Float(), nullable=False),
            sa.Column("credibility_score", sa.Float(), nullable=False),
            sa.Column("freshness_score", sa.Float(), nullable=False),
            sa.Column("overall_score", sa.Float(), nullable=False),
            sa.Column("stance", sa.String(), nullable=False),
            sa.Column("signal_strength", sa.Float(), nullable=False),
            sa.Column("summary", sa.String(), nullable=True),
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if _table_exists(bind, "forecast_sources"):
        if not _index_exists(bind, "forecast_sources", op.f("ix_forecast_sources_id")):
            op.create_index(op.f("ix_forecast_sources_id"), "forecast_sources", ["id"], unique=False)
        if not _index_exists(bind, "forecast_sources", op.f("ix_forecast_sources_forecast_id")):
            op.create_index(op.f("ix_forecast_sources_forecast_id"), "forecast_sources", ["forecast_id"], unique=False)
        if not _index_exists(bind, "forecast_sources", op.f("ix_forecast_sources_source_type")):
            op.create_index(op.f("ix_forecast_sources_source_type"), "forecast_sources", ["source_type"], unique=False)
        if not _index_exists(bind, "forecast_sources", op.f("ix_forecast_sources_stance")):
            op.create_index(op.f("ix_forecast_sources_stance"), "forecast_sources", ["stance"], unique=False)

    if not _table_exists(bind, "forecast_claims"):
        op.create_table(
            "forecast_claims",
            sa.Column("forecast_id", sa.String(), nullable=False),
            sa.Column("claim_text", sa.String(), nullable=False),
            sa.Column("claim_type", sa.String(), nullable=False),
            sa.Column("source_url", sa.String(), nullable=False),
            sa.Column("source_title", sa.String(), nullable=False),
            sa.Column("source_type", sa.String(), nullable=False),
            sa.Column("claim_confidence", sa.Float(), nullable=False),
            sa.Column("time_relevance", sa.Float(), nullable=False),
            sa.Column("source_quality_weight", sa.Float(), nullable=True),
            sa.Column("claim_confidence_weight", sa.Float(), nullable=True),
            sa.Column("time_relevance_weight", sa.Float(), nullable=True),
            sa.Column("relevance_weight", sa.Float(), nullable=True),
            sa.Column("freshness_weight", sa.Float(), nullable=True),
            sa.Column("independence_weight", sa.Float(), nullable=True),
            sa.Column("specificity_weight", sa.Float(), nullable=True),
            sa.Column("support_boost", sa.Float(), nullable=True),
            sa.Column("final_weight", sa.Float(), nullable=True),
            sa.Column("direction", sa.Integer(), nullable=True),
            sa.Column("signed_weight", sa.Float(), nullable=True),
            sa.Column("supporting_source_count", sa.Integer(), nullable=True),
            sa.Column("supporting_domain_count", sa.Integer(), nullable=True),
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if _table_exists(bind, "forecast_claims"):
        if not _index_exists(bind, "forecast_claims", op.f("ix_forecast_claims_id")):
            op.create_index(op.f("ix_forecast_claims_id"), "forecast_claims", ["id"], unique=False)
        if not _index_exists(bind, "forecast_claims", op.f("ix_forecast_claims_forecast_id")):
            op.create_index(op.f("ix_forecast_claims_forecast_id"), "forecast_claims", ["forecast_id"], unique=False)
        if not _index_exists(bind, "forecast_claims", op.f("ix_forecast_claims_claim_type")):
            op.create_index(op.f("ix_forecast_claims_claim_type"), "forecast_claims", ["claim_type"], unique=False)
        if not _index_exists(bind, "forecast_claims", op.f("ix_forecast_claims_source_type")):
            op.create_index(op.f("ix_forecast_claims_source_type"), "forecast_claims", ["source_type"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    if _table_exists(bind, "forecast_claims"):
        if _index_exists(bind, "forecast_claims", op.f("ix_forecast_claims_source_type")):
            op.drop_index(op.f("ix_forecast_claims_source_type"), table_name="forecast_claims")
        if _index_exists(bind, "forecast_claims", op.f("ix_forecast_claims_claim_type")):
            op.drop_index(op.f("ix_forecast_claims_claim_type"), table_name="forecast_claims")
        if _index_exists(bind, "forecast_claims", op.f("ix_forecast_claims_forecast_id")):
            op.drop_index(op.f("ix_forecast_claims_forecast_id"), table_name="forecast_claims")
        if _index_exists(bind, "forecast_claims", op.f("ix_forecast_claims_id")):
            op.drop_index(op.f("ix_forecast_claims_id"), table_name="forecast_claims")
        op.drop_table("forecast_claims")

    if _table_exists(bind, "forecast_sources"):
        if _index_exists(bind, "forecast_sources", op.f("ix_forecast_sources_stance")):
            op.drop_index(op.f("ix_forecast_sources_stance"), table_name="forecast_sources")
        if _index_exists(bind, "forecast_sources", op.f("ix_forecast_sources_source_type")):
            op.drop_index(op.f("ix_forecast_sources_source_type"), table_name="forecast_sources")
        if _index_exists(bind, "forecast_sources", op.f("ix_forecast_sources_forecast_id")):
            op.drop_index(op.f("ix_forecast_sources_forecast_id"), table_name="forecast_sources")
        if _index_exists(bind, "forecast_sources", op.f("ix_forecast_sources_id")):
            op.drop_index(op.f("ix_forecast_sources_id"), table_name="forecast_sources")
        op.drop_table("forecast_sources")
