"""Sets up the object database tables."""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    """User object table."""

    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


class Category(Base):
    """Category table."""

    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(25), nullable=False)

    @property
    def serialize(self):
        """Return object data in easily serializeable format."""
        return {
            'id': self.id,
            'name': self.name,
        }


class Item(Base):
    """Item table."""

    __tablename__ = 'item'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Serialize function to send json objects."""
        return {
            'cat_id': self.category_id,
            'description': self.description,
            'id': self.id,
            'title': self.name,
            }


engine = create_engine('sqlite:///itemcatalog.db')

Base.metadata.create_all(engine)
