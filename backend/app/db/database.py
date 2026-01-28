from sqlmodel import SQLModel, Session, create_engine

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

def create_db_and_tables() -> None:
    from app.models.transaction import Transaction  # noqa: F401
    from app.models.summary import Summary  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
