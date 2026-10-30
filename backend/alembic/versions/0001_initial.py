"""Create Orbit's initial PostgreSQL schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

user_role = sa.Enum("student", "teacher", "admin", name="user_role")
membership_role = sa.Enum("student", "teacher", name="membership_role")
assignment_type = sa.Enum("worksheet", "quiz", "lab_report", "coding", "project", name="assignment_type")


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    membership_role.create(bind, checkfirst=True)
    assignment_type.create(bind, checkfirst=True)
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("firebase_uid", sa.String(128), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("avatar_id", sa.String(32), nullable=False, server_default="orbit"),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("firebase_uid", name="uq_users_firebase_uid"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_table(
        "classrooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("course_code", sa.String(24), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("join_code", sa.String(12), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("join_code", name="uq_classrooms_join_code"),
    )
    op.create_index("ix_classrooms_created_by", "classrooms", ["created_by"])
    op.create_index("ix_classrooms_join_code", "classrooms", ["join_code"])
    op.create_table(
        "classroom_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", membership_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("classroom_id", "user_id", name="uq_classroom_user"),
    )
    op.create_index("ix_classroom_memberships_classroom_id", "classroom_memberships", ["classroom_id"])
    op.create_index("ix_classroom_memberships_user_id", "classroom_memberships", ["user_id"])
    op.create_table(
        "classroom_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_classroom_resources_classroom_id", "classroom_resources", ["classroom_id"])
    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_announcements_classroom_id", "announcements", ["classroom_id"])
    op.create_table(
        "assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(140), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("assignment_type", assignment_type, nullable=False),
        sa.Column("points", sa.Float(), nullable=False, server_default="100"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("auto_grade", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_assignments_classroom_id", "assignments", ["classroom_id"])
    op.create_index("ix_assignments_due_at", "assignments", ["due_at"])
    op.create_table(
        "assignment_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choices", postgresql.JSONB(), nullable=False),
        sa.Column("answer_key", sa.String(1), nullable=False),
    )
    op.create_index("ix_assignment_questions_assignment_id", "assignment_questions", ["assignment_id"])
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("text_response", sa.Text(), nullable=False, server_default=""),
        sa.Column("file_key", sa.String(512), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("suggested_score", sa.Float(), nullable=True),
        sa.Column("grade", sa.Float(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("graded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("assignment_id", "student_id", name="uq_submission_assignment_student"),
    )
    op.create_index("ix_submissions_assignment_id", "submissions", ["assignment_id"])
    op.create_index("ix_submissions_student_id", "submissions", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_submissions_student_id", table_name="submissions")
    op.drop_index("ix_submissions_assignment_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_assignment_questions_assignment_id", table_name="assignment_questions")
    op.drop_table("assignment_questions")
    op.drop_index("ix_assignments_due_at", table_name="assignments")
    op.drop_index("ix_assignments_classroom_id", table_name="assignments")
    op.drop_table("assignments")
    op.drop_index("ix_announcements_classroom_id", table_name="announcements")
    op.drop_table("announcements")
    op.drop_index("ix_classroom_resources_classroom_id", table_name="classroom_resources")
    op.drop_table("classroom_resources")
    op.drop_index("ix_classroom_memberships_user_id", table_name="classroom_memberships")
    op.drop_index("ix_classroom_memberships_classroom_id", table_name="classroom_memberships")
    op.drop_table("classroom_memberships")
    op.drop_index("ix_classrooms_join_code", table_name="classrooms")
    op.drop_index("ix_classrooms_created_by", table_name="classrooms")
    op.drop_table("classrooms")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_table("users")
    assignment_type.drop(op.get_bind(), checkfirst=True)
    membership_role.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
