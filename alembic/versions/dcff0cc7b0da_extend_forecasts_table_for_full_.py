"""extend forecasts table for full forecast payload

Revision ID: dcff0cc7b0da
Revises: cbdf80780206
Create Date: 2026-03-22
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "dcff0cc7b0da"
down_revision = "cbdf80780206"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS raw_probability DOUBLE PRECISION NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS calibrated_probability DOUBLE PRECISION NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS summary TEXT NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS direct_answer TEXT NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS answer_label TEXT NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS answer_confidence_band TEXT NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS answer_rationale_short TEXT NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS runtime_calibration_meta JSONB NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS calibration_signals JSONB NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS diagnostics JSONB NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS sources JSONB NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS claims JSONB NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS top_pro_claims JSONB NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS top_contra_claims JSONB NULL")
    op.execute("ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS top_uncertainties JSONB NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS top_uncertainties")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS top_contra_claims")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS top_pro_claims")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS claims")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS sources")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS diagnostics")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS calibration_signals")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS runtime_calibration_meta")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS answer_rationale_short")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS answer_confidence_band")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS answer_label")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS direct_answer")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS summary")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS calibrated_probability")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS raw_probability")
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS updated_at")
