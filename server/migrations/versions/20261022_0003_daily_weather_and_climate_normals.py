"""daily weather and climate normals

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22 18:06:40.362189
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    op.create_table('climate_normals',
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('day_of_year', sa.SmallInteger(), nullable=False),
    sa.Column('normal_tmean', sa.Float(), nullable=True),
    sa.Column('normal_tmin', sa.Float(), nullable=True),
    sa.Column('normal_tmax', sa.Float(), nullable=True),
    sa.Column('normal_p10', sa.Float(), nullable=True),
    sa.Column('normal_p90', sa.Float(), nullable=True),
    sa.Column('normal_precip', sa.Float(), nullable=True),
    sa.Column('normal_humidity', sa.Float(), nullable=True),
    sa.Column('normal_wind_max', sa.Float(), nullable=True),
    sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], name=op.f('fk_climate_normals_city_id_cities'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('city_id', 'day_of_year', name=op.f('pk_climate_normals'))
    )
    op.create_table('daily_weather',
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('tmin', sa.Float(), nullable=True),
    sa.Column('tmax', sa.Float(), nullable=True),
    sa.Column('tmean', sa.Float(), nullable=True),
    sa.Column('humidity', sa.Float(), nullable=True),
    sa.Column('precip', sa.Float(), nullable=True),
    sa.Column('wind_max', sa.Float(), nullable=True),
    sa.Column('is_final', sa.Boolean(), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], name=op.f('fk_daily_weather_city_id_cities'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('city_id', 'date', name=op.f('pk_daily_weather'))
    )
    op.add_column('cities', sa.Column('utc_offset_s', sa.Integer(), nullable=True))



def downgrade() -> None:

    op.drop_column('cities', 'utc_offset_s')
    op.drop_table('daily_weather')
    op.drop_table('climate_normals')

