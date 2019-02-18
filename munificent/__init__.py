import os

from .__version__ import __version__, VERSION


class Config(object):
    def __init__(self):
        pass

    @property
    def SQLALCHEMY_DBURI(self):
        return os.getenv('SQLALCHEMY_DBURI', 'sqlite:///nextbus.db')


config = Config()

__all__ = [
    '__version__',
    'VERSION',
    'config',
]
