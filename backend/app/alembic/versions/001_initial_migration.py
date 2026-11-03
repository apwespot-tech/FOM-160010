"""Initial migration - создание таблиц users, books, book_requests
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('username', sa.String(50), unique=True, index=True, nullable=False),
        sa.Column('email', sa.String(100), unique=True, index=True, nullable=False),
        sa.Column('hashed_password', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now())
    )
    
    op.create_table(
        'books',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('title', sa.String(200), nullable=False, index=True),
        sa.Column('author', sa.String(100), nullable=False, index=True),
        sa.Column('genre', sa.String(50), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cover_url', sa.String(500), nullable=True),
        sa.Column('is_available', sa.Boolean(), default=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now())
    )
    
    op.create_table(
        'book_requests',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id'), nullable=False),
        sa.Column('requester_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now())
    )

def downgrade() -> None:
    op.drop_table('book_requests')
    op.drop_table('books')
    op.drop_table('users')