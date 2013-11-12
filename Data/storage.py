from sqlalchemy import create_engine
from config import database_config
from sqlalchemy.orm.session import sessionmaker


class StorageFactory(object):

    _dataStore = None
    _sessionMaker = None
    config = database_config

    @staticmethod
    def getNewSession():
        if StorageFactory._sessionMaker == None:
            StorageFactory._sessionMaker = sessionmaker(bind=StorageFactory.getDefaultDataStore().engine)

        return StorageFactory._sessionMaker()

    @staticmethod
    def getDefaultDataStore():
        if StorageFactory._dataStore == None:
            StorageFactory._dataStore = StorageFactory._buildDataStore(StorageFactory.config['engine']['type'])

        return StorageFactory._dataStore

    @staticmethod
    def _buildDataStore(dbtype):
        if dbtype == 'MySql':
            return MySQLDataStore(
                                  StorageFactory.config['engine']['host'],
                                  StorageFactory.config['engine']['user'],
                                  StorageFactory.config['engine']['pass'],
                                  StorageFactory.config['engine']['db'])
        elif dbtype == 'Sqlite':
            return SqliteDataStore(
                                   StorageFactory.config['engine']['file'])


class DataStore(object):

    def __init__(self, uri, debug=False):
        self._engine = create_engine(uri, echo=debug)

    @property
    def engine(self):
        return self._engine


class SqliteDataStore(DataStore):

    def __init__(self, fileName):
        uri = "sqlite:///%(file)s" % {
                                     'file': fileName,
                                     }

        super(SqliteDataStore, self).__init__(uri, StorageFactory.config['debug'])


class MySQLDataStore(DataStore):

    def __init__(self, host, user, pw, db):
        # uri = "mysql://anonymous@%(host)s/%(db)s"
        uri = "mysql://%(user)s:%(pass)s@%(host)s/%(db)s" % {
                                                             'user': user,
                                                             'pass': pw,
                                                             'host': host,
                                                             'db': db }

        super(MySQLDataStore, self).__init__(uri, StorageFactory.config['debug'])
