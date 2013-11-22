from base import StandardMixin, Base
from sqlalchemy import Column, Index, Integer, ForeignKey, Float, String, PickleType, Boolean, Table
from sqlalchemy.orm import relationship

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

    minSpeed = Column(Integer)
    maxSpeed = Column(Integer)
    minPosition = Column(Integer)
    maxPosition = Column(Integer)
    defaultPosition = Column(Integer)
    defaultSpeed = Column(Integer)
    positionOffset = Column(Float)
    poseable = Column(Boolean)
    extraData = Column(PickleType)

    def __init__(self, jointName=None):
        self.jointName = jointName

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

    def __init__(self, name=None):
        super(ServoGroup, self).__init__()
        self.name = name


class ServoModel(StandardMixin, Base):
    name = Column(String(50))
    minSpeed = Column(Integer)
    maxSpeed = Column(Integer)
    minPosition = Column(Integer)
    maxPosition = Column(Integer)
    defaultPosition = Column(Integer)
    defaultSpeed = Column(Integer)
    positionScale = Column(Float)
    speedScale = Column(Float)
    positionOffset = Column(Float)
    poseable = Column(Boolean)
    extraData = Column(PickleType)

    def __init__(self, name=None):
        super(ServoModel, self).__init__()
        self.name = name
        self.minSpeed = 1
        self.maxSpeed = 300
        self.minPosition = -180
        self.maxPosition = 180
        self.defaultPosition = 0
        self.defaultSpeed = 100
        self.positionOffset = 0
        self.positionScale = 1
        self.speedScale = 1
        self.poseable = False


class ServoConfig(StandardMixin, Base):
    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", back_populates="servoConfigs")

    model_id = Column(Integer, ForeignKey("ServoModel.id"))
    model = relationship("ServoModel")

    port = Column(String(50))
    portSpeed = Column(Integer)
    extraData = Column(PickleType)

    def __init__(self):
        super(ServoConfig, self).__init__()
