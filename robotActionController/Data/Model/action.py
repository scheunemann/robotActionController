import os
import uuid
from base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey, Table, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.orderinglist import ordering_list


__all__ = ['Action', 'GroupAction', 'JointPosition', 'SequenceOrder', 'PoseAction', 'SequenceAction', 'SoundAction', ]


nextActions_table = Table('nextActions', Base.metadata,
    Column('Action_id', Integer, ForeignKey('Action.id')),
    Column('Action_id', Integer, ForeignKey('Action.id'))
)


class Action(StandardMixin, Base):

    name = Column(String(50))
    type = Column(String(50))

    next_actions = relationship("Action", secondary=nextActions_table)
    triggers = relationship("Trigger", back_populates="action")
    overrides = relationship("CustomAction", back_populates="overridden", foreign_keys="CustomAction.overridden_id")

    __mapper_args__ = {
            'polymorphic_identity': 'Action',
            'polymorphic_on': type
        }

    def __init__(self, name=None, next_actions=[], triggers=[], overrides=[], **kwargs):
        super(Action, self).__init__(**kwargs)
        self.name = name
        self.next_actions = next_actions
        self.triggers = triggers
        self.overrides = overrides

    @staticmethod
    def deserialize(cls, dictObj, session, depth=3):
        if cls == Action:
            if dictObj:
                if 'type' in dictObj:
                    actionType = dictObj.pop('type')
                    actionClass = None
                    if actionType.lower() == 'expressionaction':
                        actionClass = ExpressionAction
                    elif actionType.lower() == 'groupaction':
                        actionClass = GroupAction
                    elif actionType.lower() == 'poseaction':
                        actionClass = PoseAction
                    elif actionType.lower() == 'sequenceaction':
                        actionClass = SequenceAction
                    elif actionType.lower() == 'soundaction':
                        actionClass = SoundAction
                    else:
                        raise ValueError('Unknown action type: %s' % actionType)

                    return super(cls, cls).deserialize(actionClass, dictObj, session, depth)
                else:
                    raise ValueError('Action type not specified')
            else:
                return None, None
        else:
            return super(cls, cls).deserialize(cls, dictObj, session, depth)


class SoundAction(Action):

    id = Column(Integer, ForeignKey(Action.id), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'SoundAction',
            'inherit_condition': (id == Action.id),
    }

    uuid = Column(String(36))

    @property
    def data(self):
        return SoundAction.readData(self.uuid)

    @data.setter
    def data(self, value):
        self.uuid = SoundAction.saveData(value, self.uuid)

    @property
    def _fileName(self):
        self.uuid, path = SoundAction.__fileName(self.uuid)
        return path

    @staticmethod
    def saveData(value, uuid=None):
        if value:
            uuid, fileName = SoundAction.__fileName(uuid)
            with open(fileName, 'wb') as f:
                f.write(value)
        elif uuid != None:
            os.remove(fileName)
            uuid = None
        return uuid

    @staticmethod
    def readData(uuid=None):
        if not uuid:
            return None
        fileName = SoundAction.__fileName(uuid)[1]
        if os.path.isfile(fileName):
            with open(fileName, 'rb') as f:
                b = f.read()
            return b
        else:
            return None

    @staticmethod
    def __fileName(uuid_=None):
        basePath = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundFiles'))
        if not os.path.isdir(basePath):
            os.makedirs(basePath)

        if uuid_ == None:
            uuid_ = str(uuid.uuid1())

        return (uuid_, os.path.join(basePath, uuid_))

    def __init__(self, uuid=None, **kwargs):
        super(SoundAction, self).__init__(**kwargs)
        self.uuid = uuid


class JointPosition(StandardMixin, Base):

    jointName = Column(String(50))
    position = Column(Float)
    positions = Column(String(500))
    speed = Column(Integer)

    pose_id = Column(Integer, ForeignKey('PoseAction.id'))
    pose = relationship("PoseAction", back_populates="jointPositions")

    def __init__(self, jointName=None, position=None, positions=None, speed=None, pose=None, pose_id=None, **kwargs):
        super(JointPosition, self).__init__(**kwargs)
        self.jointName = jointName
        self.positions = positions
        self.position = position
        self.pose = pose
        self.pose_id = pose_id
        self.speed = speed

    def __repr__(self):
        return "<%s('%s':%s)>" % (
                                  self.__class__.__name__,
                                  self.jointName,
                                  self.position)


class PoseAction(Action):

    id = Column(Integer, ForeignKey(Action.id), primary_key=True)
    speedModifier = Column(Integer, default=100, nullable=False)

    __mapper_args__ = {
            'polymorphic_identity': 'PoseAction',
            'inherit_condition': (id == Action.id),
    }

    jointPositions = relationship("JointPosition", back_populates="pose", lazy=False)

    def __init__(self, jointPositions=[], speedModifier=None, **kwargs):
        super(PoseAction, self).__init__(**kwargs)
        self.jointPositions = jointPositions
        self.speedModifier = speedModifier


class SequenceOrder(StandardMixin, Base):

    order = Column(Integer)

    action_id = Column(Integer, ForeignKey('Action.id'))
    action = relationship("Action", foreign_keys=action_id)

    sequence_id = Column(Integer, ForeignKey('SequenceAction.id'))
    sequence = relationship("SequenceAction", back_populates="actions", foreign_keys=sequence_id)

    forcedLength = Column(Integer, nullable=True)

    def __init__(self, action=None, action_id=None, sequence=None, sequence_id=None, forcedLength=None, **kwargs):
        super(SequenceOrder, self).__init__(**kwargs)
        self.action = action
        self.action_id = action_id
        self.sequence = sequence
        self.sequence_id = sequence_id
        self.forcedLength = forcedLength


class SequenceAction(Action):

    id = Column(Integer, ForeignKey(Action.id), primary_key=True)

    __mapper_args__ = {
            'polymorphic_identity': 'SequenceAction',
    }

    actions = relationship("SequenceOrder", back_populates="sequence", lazy=False, order_by="SequenceOrder.order", collection_class=ordering_list("order"))

    def __init__(self, actions=[], **kwargs):
        super(SequenceAction, self).__init__(**kwargs)
        self.actions = actions


groupActions_table = Table('groupActions', Base.metadata,
    Column('Group_id', Integer, ForeignKey('GroupAction.id')),
    Column('Action_id', Integer, ForeignKey('Action.id'))
)


class GroupAction(Action):

    id = Column(Integer, ForeignKey(Action.id), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'GroupAction',
            'inherit_condition': (id == Action.id),
    }

    actions = relationship("Action", secondary=groupActions_table)

    def __init__(self, actions=[], **kwargs):
        super(GroupAction, self).__init__(**kwargs)
        self.actions = actions

