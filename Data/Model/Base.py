from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy import inspect, Column, Integer, Sequence, DateTime, func
from sqlalchemy.orm.properties import RelationshipProperty, ColumnProperty
from dateutil.tz import tzutc
import Data.config
import datetime

class Base(Data.config.modelBase):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__
    
    __table_args__ = {'mysql_engine': 'InnoDB'}
    
    id = Column(Integer, Sequence('%s_id_seq' % __tablename__), primary_key=True)
    created = Column(DateTime, nullable=False, default=func.now()) 
    modified = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    @staticmethod
    def getDesc(cls):
        desc = {}
        mapper = inspect(cls)
        for attr in mapper.attrs:
            if isinstance(attr, RelationshipProperty):
                if attr.uselist == True:
                    try:
                        desc[attr.key] = "[%s]" % attr.mapper.class_.__name__
                    except:
                        print type(attr.target)
                        print dir(attr.target)
                else:
                    desc[attr.key] = attr.mapper.class_.__name__
            elif isinstance(attr, ColumnProperty):
                desc[attr.key] = attr.columns[0].type.python_type
        
        return desc
    
    @staticmethod
    def _utcDateTime(dt):
        if dt.tzinfo:
            dt = dt.astimezone(tzutc()).replace(tzinfo=None)
        return dt.isoformat() + 'Z'
    
    @staticmethod
    def deserialize(cls, dictObj, session):
        mapper = inspect(cls)
        if dictObj.has_key('id'):
            newObj = session.query(cls).get(dictObj['id'])
        else:
            newObj = cls()
        for attr in mapper.attrs:
            if not dictObj.has_key(attr.key):
                continue;
            
            if isinstance(attr, RelationshipProperty):
                itemType = attr.mapper.class_
                #newData can be [{objectDict}, ...], {objectDict}, {'proxyObject':true, 'ids':[oid, ...], ... }
                newData = dictObj[attr.key]
                if isinstance(newData, dict) and newData.has_key('proxyObject'):
                    #newData = {'proxyList':true, 'ids':[oid, ...], 'type', 'ObjType', 'url': 'objUrl/:id' }
                    if attr.uselist == True:
                        attrList = getattr(newObj, attr.key)
                        curIds = map(lambda x: x.id, attrList)
                        newIds = newData['ids']
                        
                        adds = filter(lambda x: x not in curIds, newIds)
                        dels = filter(lambda x: x not in newIds, curIds)
    
                        for o in adds:
                            attrList.append(session.query(itemType).get(o))
                        for o in dels:
                            attrList.remove(session.query(itemType).get(o))
                    else:
                        if getattr(newObj, attr.key).id != newData:
                            setattr(newObj, attr.key, session.query(itemType).get(o))
                else:
                    #newData can be [{objectDict}, ...], {objectDict}
                    if attr.uselist == True:
                        attrList = getattr(newObj, attr.key)
                        map(attrList.remove, attrList)
                        
                        for o in newData:
                            attrList.append(Base.deserialize(itemType, o, session))
                    else:
                        setattr(newObj, attr.key, Base.deserialize(itemType, newData, session))
            elif isinstance(attr, ColumnProperty):
                if attr.columns[0].type.python_type == datetime.datetime:
                    item = datetime.datetime.strptime(dictObj[attr.key], '%Y-%m-%dT%H:%M:%SZ')
                else:
                    item = dictObj[attr.key]
                
                if not getattr(newObj, attr.key) == item:
                    setattr(newObj, attr.key, item)

        return newObj
    
    def serialize(self, useProxies=True, urlResolver=None):
        mapper = inspect(self.__class__)
        obj = {}
        for attr in mapper.attrs:
            if isinstance(attr, RelationshipProperty):
                if useProxies:
                    proxy = {
                             'proxyObject':True, 
                             'ids':[], 
                             'type': attr.mapper.class_.__name__, 
                             'isList':attr.uselist,
                             'uri': '' 
                    }
                    if urlResolver != None:
                        proxy['uri'] = urlResolver(attr.mapper.class_)

                    if attr.uselist == True:
                        for item in getattr(self, attr.key):
                            proxy['ids'].append(item.id)
                    else:
                        att = getattr(self, attr.key)
                        if att != None:
                            proxy['ids'].append(att.id)
                        
                    obj[attr.key] = proxy
                else:
                    #This has potential circular reference issues
                    if attr.uselist == True:
                        items = []
                        for item in getattr(self, attr.key):
                            items.append(item.serialize(useProxies, urlResolver))                        
                        obj[attr.key] = items
                    else:
                        obj[attr.key] = getattr(self, attr.key).serialize()
            elif isinstance(attr, ColumnProperty):
                item = getattr(self, attr.key)
                if type(item) == datetime.datetime:
                    item = Base._utcDateTime(item)
                    
                obj[attr.key] = item                

        return obj

Base = declarative_base(cls=Base)

class SettingMixin(object):

    __mapper_args__= {'always_refresh': True}

class DisplayMixin(object):
    
    def __repr__(self):
        if hasattr(self, 'name'):
            return "<%s('%s')>" % (self.__class__.__name__, self.name)
        else:
            return "<%s('%s')>" % (self.__class__.__name__, self.id)

class StandardMixin(DisplayMixin, SettingMixin):
    pass
