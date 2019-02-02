import os

from sqlalchemy import (
    create_engine,
    MetaData, Table, Column, ForeignKey, Integer, String, Float,
)
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy.dialects.sqlite

from munificent import config as app_config


def configured_engine(config=None):
    config = config or app_config
    return create_engine(config.SQLALCHEMY_DBURI)


def configured_session(config=None):
    config = config or app_config
    engine = configured_engine(config)
    return scoped_session(sessionmaker(bind=engine))


def search_routes(q):
    Session = configured_session()
    return (Session.query(Route)
        .filter(Route.tag.like('%{}%'.format(q))))


Base = declarative_base()

class Agency(Base):
    __tablename__ = 'agencies'

    id = Column(Integer, primary_key=True)
    tag = Column(String)
    title = Column(String)
    shortTitle = Column(String)
    regionTitle = Column(String)

    def __repr__(self):
        return 'Agency({}, regionTitle={})'.format(self.title, self.regionTitle)


class Stop(Base):
    __tablename__ = 'stops'

    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey('agencies.id'))
    lat = Column(Float)
    lon = Column(Float)
    stopID = Column(Integer)
    tag = Column(String)
    title = Column(String)
    # sqlite_autoincrement=True,

    agency = relationship('Agency')
    routes = relationship('RouteStop', back_populates='stop')

    def __repr__(self):
        return 'Stop({}, stopID={})'.format(self.title, self.stopID)


class Route(Base):
    __tablename__ = 'routes'

    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey('agencies.id'))
    tag = Column(String)
    title = Column(String)
    # sqlite_autoincrement=True,

    agency = relationship('Agency')
    stops = relationship('RouteStop', back_populates='route')

    def __repr__(self):
        return 'Route({}: {})'.format(self.id, self.title)


class RouteStop(Base):
    __tablename__ = 'route_stops'

    agency_id = Column(Integer, ForeignKey('agencies.id'))
    route_id = Column('route_id', Integer, ForeignKey('routes.id'), primary_key=True)
    stop_id = Column('stop_id', Integer, ForeignKey('stops.id'), primary_key=True)

    agency = relationship('Agency')
    route = relationship('Route', back_populates='stops')
    stop = relationship('Stop', back_populates='routes')

    @property
    def route_stop_code(self):
        return '{}|{}'.format(self.route.tag, self.stop.tag)

    def __repr__(self):
        return 'RouteStop({}: {})'.format(self.route.tag, self.stop.title)


def reload_db():
    from munificent.nextbus import populate_db
    drop_db()
    create_db()
    populate_db()


def drop_db():
    for entity in reversed(Base.metadata.sorted_tables):
        try:
            entity.drop(engine)
        except Exception as e:
            print e
            continue


def create_db():
    for entity in Base.metadata.sorted_tables:
        entity.create(engine)
