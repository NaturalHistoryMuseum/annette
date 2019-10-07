from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os


with open(f'{os.path.dirname(__file__)}/auth.txt', 'r') as f:
    PWD, USR, DB = f.read().splitlines()

SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{USR}:{PWD}@{DB}?charset=utf8"

# Create session
engine = create_engine(SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine, autocommit=True)
Base = declarative_base(engine)
