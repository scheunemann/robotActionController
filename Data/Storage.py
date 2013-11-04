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

    @staticmethod
    def _flushAndFillTestData():
        StorageFactory.config['debug'] = True
        from Model import Base
        Base.metadata.drop_all(StorageFactory.getDefaultDataStore().engine)
        Base.metadata.create_all(StorageFactory.getDefaultDataStore().engine)
         
        from Data.Model import Operator, User, Sound, CustomAction, TimeTrigger, CustomTrigger, Pose, Sequence
        o = Operator('oNathan', 'oNathan Burke')
        o.password = '1234'
        u = User('uNathan', 'uNathan Burke')
        s = Sound('aSound')
        cs = Sound('cSound')
        ca = CustomAction()
        ca.overridden = s
        ca.redirect = cs
        u.customActions.append(ca)
        p = Pose('aPose')
        cp = Pose('cPose')
        ca = CustomAction('Custom_Pose')
        ca.overridden = p
        ca.redirect = cp
        u.customActions.append(ca)
        
        t = TimeTrigger('tTime')
        ct = TimeTrigger('cTime')
        ctr = CustomTrigger('Custom_Time')
        ctr.overridden = t
        ctr.redirect = ct
        u.customTriggers.append(ctr)
        
        o.users.append(u)
        
        sq = Sequence('aSequence')
        sq.actions.append(s)
        sq.actions.append(p)
         
        session = StorageFactory.getNewSession()
        session.add(sq)
        session.add(o)
        session.commit()
    
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
        #uri = "mysql://anonymous@%(host)s/%(db)s"
        uri = "mysql://%(user)s:%(pass)s@%(host)s/%(db)s" % {
                                                             'user': user,
                                                             'pass': pw,
                                                             'host': host,
                                                             'db': db }
        
        super(MySQLDataStore, self).__init__(uri, StorageFactory.config['debug'])
        
if __name__ == '__main__':
    StorageFactory.__flushAndFillTestData()
