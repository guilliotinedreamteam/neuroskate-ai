import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ecom_dominator.models import Base
from ecom_dominator.service import ServiceLayer
from ecom_dominator.marketplaces.base import MarketplaceAdapter

# In-memory DB for tests
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def service(db_session):
    return ServiceLayer(db_session)
