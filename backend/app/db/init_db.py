from app.db.base import Base
from app.db.session import engine
from app.models import Category, Item, Option  # noqa: F401


# Development convenience only. Alembic is the official way to create or change
# database schema. Do not mix this with Alembic-managed databases except for
# short-lived local experiments.
def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("database tables created")