from alembic import context
from app.core.config import Settings
from app.db.base import Base
from app.db.session import build_engine
from app.models import GitHubConnection, GitHubOAuthState, LoginThrottle, RefreshSession, User  # noqa: F401

config = context.config
settings = Settings()
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=settings.database_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(settings)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
