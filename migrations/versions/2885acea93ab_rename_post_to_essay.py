"""rename post to essay

Revision ID: 2885acea93ab
Revises: 4e615301708e
Create Date: 2026-08-08 17:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '2885acea93ab'
down_revision = '4e615301708e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_post_user_id'))
        batch_op.drop_index(batch_op.f('ix_post_created_at'))

    op.rename_table('post', 'essay')

    with op.batch_alter_table('essay', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_essay_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_essay_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('essay', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_essay_user_id'))
        batch_op.drop_index(batch_op.f('ix_essay_created_at'))

    op.rename_table('essay', 'post')

    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_post_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_post_user_id'), ['user_id'], unique=False)
