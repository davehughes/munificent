import os


class Config(object):
    def __init__(self):
        pass

    @property
    def SQLALCHEMY_DBURI(self):
        return os.getenv('SQLALCHEMY_DBURI', 'sqlite:///nextbus.db')


config = Config()

__all__ = [
    'config',
]
