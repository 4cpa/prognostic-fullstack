"""evidence_items.direction: integer -> string (pro/contra/uncertainty)

Revision ID: 274e9bc69424
Revises: dcff0cc7b0da
Create Date: 2026-07-06
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "274e9bc69424"
down_revision = "dcff0cc7b0da"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE evidence_items
        ALTER COLUMN direction TYPE VARCHAR
        USING (
            CASE direction
                WHEN 1 THEN 'pro'
                WHEN -1 THEN 'contra'
                ELSE 'uncertainty'
            END
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE evidence_items
        ALTER COLUMN direction TYPE INTEGER
        USING (
            CASE direction
                WHEN 'pro' THEN 1
                WHEN 'contra' THEN -1
                ELSE 0
            END
        )
        """
    )
