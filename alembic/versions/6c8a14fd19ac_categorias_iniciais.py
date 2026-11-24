"""categorias iniciais

Revision ID: 6c8a14fd19ac
Revises: 6e07179c52f0
Create Date: 2026-11-24 09:12:33.599453

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '6c8a14fd19ac'
down_revision: Union[str, Sequence[str], None] = '6e07179c52f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIAS = [
    ("calcada_quebrada", "Calçada Quebrada ou Irregular"),
    ("piso_tatil", "Piso Tátil Ausente ou Danificado"),
    ("rampa_ausente", "Ausência de Rampa de Acesso"),
    ("rampa_inadequada", "Rampa Inadequada ou Danificada"),
    ("degrau_elevado", "Degrau Elevado"),
    ("obstaculo_fixo", "Obstáculo Fixo na Passagem"),
    ("bloqueio_temporario", "Bloqueio Temporário"),
    ("semaforo_sonoro", "Semáforo Sonoro Inoperante/Ausente"),
    ("boca_de_lobo", "Boca de Lobo / Grelha Perigosa"),
    ("obra_sem_rota", "Obra Sem Rota Alternativa"),
    ("outra_barreira", "Outra Barreira Física"),
]

categoria = sa.table(
    "categoria_obstaculo",
    sa.column("slug", sa.String),
    sa.column("nome", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(categoria, [{"slug": s, "nome": n} for s, n in CATEGORIAS])


def downgrade() -> None:
    op.execute(categoria.delete().where(categoria.c.slug.in_([s for s, _ in CATEGORIAS])))