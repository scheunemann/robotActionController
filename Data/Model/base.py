from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy import inspect, Column, Integer, Sequence, DateTime, func
from sqlalchemy.orm.properties import RelationshipProperty, ColumnProperty
from dateutil.tz import tzutc
import Data.config
import datetime


__all__ = ['IDBase', 'SerializeMixin', 'SettingMixin', 'StandardMixin', 'Base']


class IDBase(Data.config.modelBase):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__

    __table_args__ = (
                      {'mysql_engine': 'InnoDB'},
                      )

    id = Column(Integer, Sequence('%s_id_seq' % __tablename__), primary_key=True)
#     created = Column(DateTime, nullable=False, default=func.now())
#     modified = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class SerializeMixin(object):

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
                        print "Error reading attribute %s on class %s!" % (attr.key, cls.__name__)
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
    def deserialize(cls, dictObj, session, depth=3):
        if 'id' in dictObj:
            newObj = session.query(cls).get(dictObj['id'])
            if not newObj:
                raise ValueError("Invalid id specified: %s %s", (cls.__name__, dictObj['id']))
        else:
            newObj = cls()
        mapper = inspect(newObj.__class__)
        props = {}
        for attr in mapper.attrs:
            if attr.key not in dictObj:
                continue

            if isinstance(attr, RelationshipProperty):
                itemType = attr.mapper.class_
                # newData can be [{objectDict}, ...], {objectDict}, {'proxyObject':true, 'ids':[oid, ...], ... }
                newData = dictObj[attr.key]
                if isinstance(newData, dict) and 'proxyObject' in newData:
                    # newData = {'proxyList':true, 'ids':[oid, ...], 'type', 'ObjType', 'url': 'objUrl/:id' }
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
                        if len(newData['ids']) == 0:
                            setattr(newObj, attr.key, None)
                        elif getattr(newObj, attr.key) == None or getattr(newObj, attr.key).id != newData['ids'][0]:
                            setattr(newObj, attr.key, session.query(itemType).get(newData['ids'][0]))
                else:
                    # newData can be [{objectDict}, ...], {objectDict}
                    props[attr.key] = {}
                    if attr.uselist == True:
                        attrList = getattr(newObj, attr.key)
                        map(attrList.remove, attrList)

                        for o in newData:
                            if depth > 0:
                                item, subProps = itemType.deserialize(itemType, o, session, depth -1)
                                attrList.append(item)
                                props[attr.key].update(subProps)
                            else:
                                attrList.append(session.query(itemType).get(o['id']))
                    else:
                        if depth > 0:
                            item, subProps = itemType.deserialize(itemType, newData, session, depth - 1)
                            setattr(newObj, attr.key, item)
                            props[attr.key] = subProps
                        else:
                            setattr(newObj, attr.key, session.query(itemType).get(newData['id']))
            elif isinstance(attr, ColumnProperty):
                try:
                    if attr.columns[0].type.python_type == datetime.datetime:
                        try:
                            item = datetime.datetime.strptime(dictObj[attr.key], '%Y-%m-%dT%H:%M:%SZ')
                        except ValueError:
                            item = datetime.datetime.strptime(dictObj[attr.key], '%Y-%m-%dT%H:%M:%S.%fZ')
                    elif attr.columns[0].type.__visit_name__ == 'large_binary':
                        continue
                    elif attr.columns[0].type.python_type:
                        try:
                            if dictObj[attr.key] == None:
                                item = None
                            else:
                                item = attr.columns[0].type.python_type(dictObj[attr.key])
                        except Exception as e:
                            # TODO: Error logging
                            print e
                            item = None
                    else:
                        item = dictObj[attr.key]
                except Exception as e:
                    item = dictObj[attr.key]

                if not getattr(newObj, attr.key) == item:
                    setattr(newObj, attr.key, item)

        return (newObj, props)

    def serialize(self, useProxies=True, urlResolver=None, resolveProps={}):
        mapper = inspect(self.__class__)
        obj = {}
        for attr in mapper.attrs:
            if isinstance(attr, RelationshipProperty):
                if useProxies and attr.key not in resolveProps:
                    proxy = {
                             'proxyObject': True,
                             'ids': [],
                             'type': attr.mapper.class_.__name__,
                             'isList': attr.uselist,
                             'uri': ''
                    }
                    if urlResolver != None:
                        if type(urlResolver) == str:
                            proxy['uri'] = urlResolver
                            urlResolver = None
                        else:
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
                    # This has potential circular reference issues
                    if attr.uselist == True:
                        items = []
                        for item in getattr(self, attr.key):
                            items.append(item.serialize(useProxies, urlResolver, resolveProps=resolveProps[attr.key]))
                        obj[attr.key] = items
                    else:
                        obj[attr.key] = getattr(self, attr.key).serialize()
            elif isinstance(attr, ColumnProperty):
                item = getattr(self, attr.key)
                if attr.columns[0].type.__visit_name__ == 'large_binary':
                    continue
                if type(item) == datetime.datetime:
                    item = SerializeMixin._utcDateTime(item)

                obj[attr.key] = item

        return obj


class SettingMixin(object):
    __mapper_args__ = {'always_refresh': True}


class DisplayMixin(object):

    def __repr__(self):
        if hasattr(self, 'name'):
            return "%s('%s')" % (self.__class__.__name__, self.name)
        else:
            return "%s('%s')" % (self.__class__.__name__, self.id)


class StandardMixin(DisplayMixin, SettingMixin, SerializeMixin):
    pass

Base = declarative_base(cls=IDBase)
