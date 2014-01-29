import os
import uuid
from base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey, Table, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.orderinglist import ordering_list


__all__ = ['Action', 'Expression', 'Group', 'JointPosition', 'OrderedAction', 'Pose', 'Sequence', 'Sound', ]


nextActions_table = Table('nextActions', Base.metadata,
    Column('Action_id', Integer, ForeignKey('Action.id')),
    Column('Action_id', Integer, ForeignKey('Action.id'))
)


class Action(StandardMixin, Base):

    name = Column(String(50))
    type = Column(String(50))

    # minimum action length, in seconds
    minLength = Column(Float)
    next_actions = relationship("Action", secondary=nextActions_table)
    triggers = relationship("Trigger", back_populates="action")
    overrides = relationship("CustomAction", back_populates="overridden", foreign_keys="CustomAction.overridden_id")

    __mapper_args__ = {
            'polymorphic_identity': 'Action',
            'polymorphic_on': type
        }

    def __init__(self, name=None):
        super(Action, self).__init__()
        self.name = name


class Sound(Action):

    id = Column(Integer, ForeignKey('%s.id' % 'Action'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'Sound',
    }

    uuid = Column(String(36))

    @property
    def data(self):
        if not self.uuid:
            return None

        fileName = self._fileName
        if os.path.isfile(fileName):
            with open(fileName, 'rb') as f:
                b = f.read()
            return b
        else:
            return None

    @property
    def _fileName(self):
        self._basePath = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundFiles'))
        if not os.path.isdir(self._basePath):
            os.makedirs(self._basePath)

        if self.uuid == None:
            self.uuid = str(uuid.uuid1())

        return os.path.join(self._basePath, self.uuid)

    @data.setter
    def data(self, value):
        if value:
            with open(self._fileName, 'wb') as f:
                f.write(value)
        elif self.uuid != None:
            os.remove(self._fileName)
            self.uuid = None

    def __init__(self, name=None):
        super(Sound, self).__init__()
        self.name = name


class JointPosition(StandardMixin, Base):

    jointName = Column(String(50))
    position = Column(Float)
    speed = Column(Integer)

    pose_id = Column(Integer, ForeignKey('Pose.id'))
    pose = relationship("Pose", back_populates="jointPositions")

    def __init__(self, jointName=None, position=None, speed=None):
        super(JointPosition, self).__init__()
        self.jointName = jointName
        self.position = position
        self.speed = speed

    def __repr__(self):
        return "<%s('%s':%s)>" % (
                                  self.__class__.__name__,
                                  self.jointName,
                                  self.position)


class Pose(Action):

    id = Column(Integer, ForeignKey('%s.id' % 'Action'), primary_key=True)
    speedModifier = Column(Integer)

    __mapper_args__ = {
            'polymorphic_identity': 'Pose',
    }

    jointPositions = relationship("JointPosition", back_populates="pose", lazy=False)

    def __init__(self, name=None, jointPositions=[], minLength=None, speedModifier=None):
        super(Pose, self).__init__(name)
        self.jointPositions = jointPositions
        self.minLength = minLength
        self.speedModifier = speedModifier


class Expression(Action):

    id = Column(Integer, ForeignKey('%s.id' % 'Action'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'Expression',
    }


class Sequence(Action):

    id = Column(Integer, ForeignKey('%s.id' % 'Action'), primary_key=True)

    __mapper_args__ = {
            'polymorphic_identity': 'Sequence',
    }

    ordered_actions = relationship("OrderedAction", order_by="OrderedAction.order", collection_class=ordering_list("order"), lazy=False)
    actions = association_proxy('ordered_actions', 'action')


class OrderedAction(StandardMixin, Base):

    order = Column(Integer)

    action_id = Column(Integer, ForeignKey('Action.id'))
    action = relationship("Action", foreign_keys=action_id)

    sequence_id = Column(Integer, ForeignKey('Sequence.id'))
    sequence = relationship("Sequence", back_populates="ordered_actions", foreign_keys=sequence_id)

    def __init__(self, action):
        self.action = action

groupActions_table = Table('groupActions', Base.metadata,
    Column('Group_id', Integer, ForeignKey('Group.id')),
    Column('Action_id', Integer, ForeignKey('Action.id'))
)


class Group(Action):

    id = Column(Integer, ForeignKey('%s.id' % 'Action'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'Group',
    }

    actions = relationship("Action", secondary=groupActions_table)
