from base import StandardMixin, Base
from sqlalchemy import Column, Index, Integer, ForeignKey, Float, String, PickleType, Boolean, Table
from sqlalchemy.orm import relationship


__all__ = ['Servo', 'ServoConfig', 'ServoGroup', 'ServoModel', ]


servoGroups_table = Table('servoGroups', Base.metadata,
    Column('Servo_id', Integer, ForeignKey('Servo.id')),
    Column('ServoGroup_id', Integer, ForeignKey('ServoGroup.id'))
)


class Servo(StandardMixin, Base):
    jointName = Column(String(50))

    model_id = Column(Integer, ForeignKey("ServoModel.id"))
    model = relationship("ServoModel")

    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", back_populates="servos")

    groups = relationship("ServoGroup", secondary=servoGroups_table, back_populates="servos")

    minSpeed = Column('minSpeed', Integer)
    maxSpeed = Column('maxSpeed', Integer)
    minPosition = Column('minPosition', Integer)
    maxPosition = Column('maxPosition', Integer)
    defaultPosition = Column('defaultPosition', Integer)
    defaultPositions = Column('defaultPositions', String(500))
    defaultSpeed = Column('defaultSpeed', Integer)
    positionOffset = Column('positionOffset', Float)
    poseable = Column('poseable', Boolean)
    readable = Column('readable', Boolean)
    extraData = Column(PickleType)

    def __init__(self, jointName=None, model_id=None, model=None, robot_id=None, robot=None, groups=[], minSpeed=None, maxSpeed=None, minPosition=None, maxPosition=None, defaultPosition=None, defaultPositions=None, defaultSpeed=None, positionOffset=None, poseable=None, readable=None, extraData=None, **kwargs):
        super(Servo, self).__init__(**kwargs)
        self.jointName = jointName
        self.model_id = model_id
        self.model = model
        self.robot_id = robot_id
        self.robot = robot
        self.groups = groups
        self.minSpeed = minSpeed
        self.maxSpeed = maxSpeed
        self.minPosition = minPosition
        self.maxPosition = maxPosition
        self.defaultPosition = defaultPosition
        self.defaultPositions = defaultPositions
        self.defaultSpeed = defaultSpeed
        self.positionOffset = positionOffset
        self.readable = readable
        self.extraData = extraData

    def __repr__(self):
        if self.robot != None:
            return "%s('%s' on '%s', id: %s)" % (self.__class__.__name__, self.jointName, self.robot.name, self.id)
        else:
            return "%s('%s', id: %s)" % (self.__class__.__name__, self.jointName, self.id)


Index('robot_joints', Servo.jointName, Servo.robot_id, unique=True)


class ServoGroup(StandardMixin, Base):
    name = Column(String(50))

    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", back_populates="servoGroups")

    servos = relationship("Servo", secondary=servoGroups_table, back_populates="groups")

    def __init__(self, name=None, robot_id=None, robot=None, servos=[], **kwargs):
        super(ServoGroup, self).__init__(**kwargs)
        self.name = name
        self.robot_id = robot_id
        self.robot = robot
        self.servos = servos


class ServoModel(StandardMixin, Base):
    name = Column(String(50))
    minSpeed = Column(Integer)
    maxSpeed = Column(Integer)
    minPosition = Column(Integer)
    maxPosition = Column(Integer)
    defaultPosition = Column(Integer)
    defaultPositions = Column(String(500))
    defaultSpeed = Column(Integer)
    positionScale = Column(Float)
    speedScale = Column(Float)
    positionOffset = Column(Float)
    poseable = Column(Boolean)
    readable = Column(Boolean)
    extraData = Column(PickleType)

    def __init__(self, name=None, minSpeed=1, maxSpeed=300, minPosition=-180, maxPosition=180, defaultPosition=0, defaultPositions=None, defaultSpeed=100, positionOffset=0, positionScale=1, speedScale=1, poseable=False, readable=False, extraData=None, **kwargs):
        super(ServoModel, self).__init__(**kwargs)
        self.name = name
        self.minSpeed = minSpeed
        self.maxSpeed = maxSpeed
        self.minPosition = minPosition
        self.maxPosition = maxPosition
        self.defaultPosition = defaultPosition
        self.defaultPositions = defaultPositions
        self.defaultSpeed = defaultSpeed
        self.positionOffset = positionOffset
        self.positionScale = positionScale
        self.speedScale = speedScale
        self.poseable = poseable
        self.readable = readable
        self.extraData = extraData


class ServoConfig(StandardMixin, Base):
    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", back_populates="servoConfigs")

    model_id = Column(Integer, ForeignKey("ServoModel.id"))
    model = relationship("ServoModel")

    port = Column(String(50))
    portSpeed = Column(Integer)
    extraData = Column(PickleType)

    def __init__(self, robot_id=None, robot=None, model_id=None, model=None, port=None, portSpeed=None, extraData=None, **kwargs):
        super(ServoConfig, self).__init__(**kwargs)
        self.robot = robot
        self.robot_id = robot_id
        self.model_id = model_id
        self.model = model
        self.port = port
        self.portSpeed = portSpeed
        self.extraData = extraData
