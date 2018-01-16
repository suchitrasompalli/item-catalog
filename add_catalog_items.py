"""Load database with initial data for testing."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Category, Base, Item, User

engine = create_engine('sqlite:///itemcatalog.db')

# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Start of with a user
user1 = User(name="test", email="emailtest", id="25")
session.add(user1)
session.commit()

# Items for Category Trees
category1 = Category(name="Trees")

session.add(category1)
session.commit()

item1 = Item(name="Peach", description="A decidious tree bearing sweet juicy \
stone fruit.", category=category1)

session.add(item1)
session.commit()

item2 = Item(name="Pear", description="The pear is any of several tree and \
shrubs in the family Rosaceae..", category=category1)

session.add(item2)
session.commit()

# Items for Category Herbs
category1 = Category(name="Herbs")

session.add(category1)
session.commit()

item1 = Item(name="Rosemary", description="A small evergreen shrub with \
leaves like pine needles", category=category1)

session.add(item1)
session.commit()

item2 = Item(name="Thyme", description="Is a aromatic evergreen perennial",
             category=category1)

session.add(item2)
session.commit()

print("added catalog items!")
