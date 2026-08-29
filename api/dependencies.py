from database.db import db_session

def get_db():
    yield from db_session()
