"""scenes

Revision ID: 001_create_scenes
Revises:
Create Date: 2026-03-27

Alembic migration: creates the `scenes` table with JSONB content,
metadata, status, version (SemVer), and audit_log support.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "001_create_scenes"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── scenes table ───────────────────────────────────────────
    op.create_table(
        "scenes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),

        # Lifecycle
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT",
                  comment="DRAFT|REVIEW|LOCKED|QUEUED|GENERATING|COMPLETED|FAILED"),

        # JSONB content: dialogue, actions, visual descriptions
        sa.Column("content", JSONB, nullable=False, server_default="{}",
                  comment="Structured scene content: narrative, dialogue, visual, audio"),

        # JSONB metadata: duration, location, tags, genre
        sa.Column("metadata", JSONB, nullable=False, server_default="{}",
                  comment="Scene metadata: genre, tags, duration_estimate, complexity_score"),

        # Versioning (SemVer stored as integer, mapped in app layer)
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("branch", sa.String(100), nullable=False, server_default="main"),
        sa.Column("parent_version", sa.Integer, nullable=True),

        # Audit log: array of JSONB entries
        sa.Column("audit_log", JSONB, nullable=False, server_default="[]",
                  comment="Append-only audit trail of operations"),

        # Relationships (denormalized for fast lookups)
        sa.Column("character_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("prop_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("depends_on", JSONB, nullable=False, server_default="[]",
                  comment="UUIDs of scenes this scene depends on"),

        # Generated output
        sa.Column("generated_video_url", sa.Text, nullable=True),
        sa.Column("generated_preview_url", sa.Text, nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),

        # Soft delete
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

        schema="public",
    )

    # ── Indexes ────────────────────────────────────────────────
    op.create_index("ix_scenes_status", "scenes", ["status"])
    op.create_index("ix_scenes_branch", "scenes", ["branch"])
    op.create_index("ix_scenes_created_at", "scenes", ["created_at"])
    op.create_index("ix_scenes_updated_at", "scenes", ["updated_at"])

    # GIN indexes for JSONB queries
    op.execute("CREATE INDEX ix_scenes_content_gin ON scenes USING GIN (content)")
    op.execute("CREATE INDEX ix_scenes_metadata_gin ON scenes USING GIN (metadata)")
    op.execute("CREATE INDEX ix_scenes_character_ids_gin ON scenes USING GIN (character_ids)")
    op.execute("CREATE INDEX ix_scenes_depends_on_gin ON scenes USING GIN (depends_on)")

    # Composite index for branch + status queries
    op.create_index("ix_scenes_branch_status", "scenes", ["branch", "status"])

    # ── Updated at trigger ─────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    op.execute("""
        CREATE TRIGGER trg_scenes_updated_at
            BEFORE UPDATE ON scenes
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # ── Characters table ───────────────────────────────────────
    op.create_table(
        "characters",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("traits", JSONB, nullable=False, server_default="{}"),
        sa.Column("state", sa.String(20), nullable=False, server_default="alive",
                  comment="alive|dead|injured|missing|introduced"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        schema="public",
    )

    # ── Props table ────────────────────────────────────────────
    op.create_table(
        "props",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("state", sa.String(20), nullable=False, server_default="intact",
                  comment="intact|damaged|destroyed|lost"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        schema="public",
    )

    # ── Story arcs table ───────────────────────────────────────
    op.create_table(
        "story_arcs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("scene_order", JSONB, nullable=False, server_default="[]",
                  comment="Ordered list of scene UUIDs in this arc"),
        sa.Column("source_text", sa.Text, nullable=True),
        sa.Column("source_format", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        schema="public",
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_scenes_updated_at ON scenes")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.drop_table("story_arcs")
    op.drop_table("props")
    op.drop_table("characters")
    op.drop_table("scenes")
