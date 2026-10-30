"""Add class admins, per-subject teacher assignments, and assignment subjects."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_class_subjects"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE membership_role ADD VALUE IF NOT EXISTS 'class_admin'")

    op.execute(
        """UPDATE classroom_memberships AS m SET role = 'class_admin'
           FROM classrooms AS c
           WHERE m.classroom_id = c.id AND m.user_id = c.created_by AND m.role = 'teacher'"""
    )
    op.execute("UPDATE users SET role = 'student' WHERE role = 'teacher'")
    op.add_column("assignments", sa.Column("subject", sa.String(length=80), nullable=False, server_default="General"))
    op.create_table(
        "classroom_teacher_subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(length=80), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("classroom_id", "user_id", "subject", name="uq_class_teacher_subject"),
    )
    op.create_index("ix_classroom_teacher_subjects_classroom_id", "classroom_teacher_subjects", ["classroom_id"])
    op.create_index("ix_classroom_teacher_subjects_user_id", "classroom_teacher_subjects", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_classroom_teacher_subjects_user_id", table_name="classroom_teacher_subjects")
    op.drop_index("ix_classroom_teacher_subjects_classroom_id", table_name="classroom_teacher_subjects")
    op.drop_table("classroom_teacher_subjects")
    op.drop_column("assignments", "subject")
    op.execute("UPDATE classroom_memberships SET role = 'teacher' WHERE role = 'class_admin'")
