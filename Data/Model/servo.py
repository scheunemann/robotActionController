from base import StandardMixin, Base
from sqlalchemy import Column, Index, Integer, ForeignKey, Float, String, PickleType, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import case
from sqlalchemy.ext.hybrid import hybrid_property


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

    _minSpeed = Column('minSpeed', Integer)
    _maxSpeed = Column('maxSpeed', Integer)
    _minPosition = Column('minPosition', Integer)
    _maxPosition = Column('maxPosition', Integer)
    _defaultPosition = Column('defaultPosition', Integer)
    _defaultPositions = Column('defaultPositions', String(500))
    _defaultSpeed = Column('defaultSpeed', Integer)
    _positionOffset = Column('positionOffset', Float)
    _poseable = Column('poseable', Boolean)
    _readable = Column('readable', Boolean)
    extraData = Column(PickleType)

    @hybrid_property
    def minSpeed(self):
        if self._minSpeed != None:
            return self._minSpeed
        elif self.model != None:
            return self.model.minSpeed
        else:
            return None

    @minSpeed.setter
    def minSpeed(self, value):
        self._minSpeed = value

    @minSpeed.expression
    def minSpeed(cls):
        return case([
                     (cls._minSpeed != None, cls._minSpeed),
                     (cls.model != None, cls.model.minSpeed)],
                    else_=None)

    @hybrid_property
    def maxSpeed(self):
        if self._maxSpeed != None:
            return self._maxSpeed
        elif self.model != None:
            return self.model.maxSpeed
        else:
            return None

    @maxSpeed.setter
    def maxSpeed(self, value):
        self._maxSpeed = value

    @maxSpeed.expression
    def maxSpeed(cls):
        return case([
                     (cls._maxSpeed != None, cls._maxSpeed),
                     (cls.model != None, cls.model.maxSpeed)],
                    else_=None)

    @hybrid_property
    def minPosition(self):
        if self._minPosition != None:
            return self._minPosition
        elif self.model != None:
            return self.model.minPosition
        else:
            return None

    @minPosition.setter
    def minPosition(self, value):
        self._minPosition = value

    @minPosition.expression
    def minPosition(cls):
        return case([
                     (cls._minPosition != None, cls._minPosition),
                     (cls.model != None, cls.model.minPosition)],
                    else_=None)

    @hybrid_property
    def maxPosition(self):
        if self._maxPosition != None:
            return self._maxPosition
        elif self.model != None:
            return self.model.maxPosition
        else:
            return None

    @maxPosition.setter
    def maxPosition(self, value):
        self._maxPosition = value

    @maxPosition.expression
    def maxPosition(cls):
        return case([
                     (cls._maxPosition != None, cls._maxPosition),
                     (cls.model != None, cls.model.maxPosition)],
                    else_=None)

    @hybrid_property
    def defaultPositions(self):
        if self._defaultPositions != None:
            return self._defaultPositions
        elif self.model != None:
            return self.model.defaultPositions
        else:
            return None

    @defaultPositions.setter
    def defaultPositions(self, value):
        self._defaultPositions = value

    @defaultPositions.expression
    def defaultPositions(cls):
        return case([
                     (cls._defaultPositions != None, cls._defaultPositions),
                     (cls.model != None, cls.model.defaultPositions)],
                    else_=None)

    @hybrid_property
    def defaultPosition(self):
        if self._defaultPosition != None:
            return self._defaultPosition
        elif self.model != None:
            return self.model.defaultPosition
        else:
            return None

    @defaultPosition.setter
    def defaultPosition(self, value):
        self._defaultPosition = value

    @defaultPosition.expression
    def defaultPosition(cls):
        return case([
                     (cls._defaultPosition != None, cls._defaultPosition),
                     (cls.model != None, cls.model.defaultPosition)],
                    else_=None)

    @hybrid_property
    def defaultSpeed(self):
        if self._defaultSpeed != None:
            return self._defaultSpeed
        elif self.model != None:
            return self.model.defaultSpeed
        else:
            return None

    @defaultSpeed.setter
    def defaultSpeed(self, value):
        self._defaultSpeed = value

    @defaultSpeed.expression
    def defaultSpeed(cls):
        return case([
                     (cls._defaultSpeed != None, cls._defaultSpeed),
                     (cls.model != None, cls.model.defaultSpeed)],
                    else_=None)

    @hybrid_property
    def positionOffset(self):
        if self._positionOffset != None:
            return self._positionOffset
        elif self.model != None:
            return self.model.positionOffset
        else:
            return None

    @positionOffset.setter
    def positionOffset(self, value):
        self._positionOffset = value

    @positionOffset.expression
    def positionOffset(cls):
        return case([
                     (cls._positionOffset != None, cls._positionOffset),
                     (cls.model != None, cls.model.positionOffset)],
                    else_=None)

    @hybrid_property
    def poseable(self):
        if self._poseable != None:
            return self._poseable
        elif self.model != None:
            return self.model.poseable
        else:
            return None

    @poseable.setter
    def poseable(self, value):
        self._poseable = value

    @poseable.expression
    def poseable(cls):
        return case([
                     (cls._poseable != None, cls._poseable),
                     (cls.model != None, cls.model.poseable)],
                    else_=None)

    @hybrid_property
    def readable(self):
        if self._readable != None:
            return self._readable
        elif self.model != None:
            return self.model.readable
        else:
            return None

    @readable.setter
    def readable(self, value):
        self._readable = value

    @readable.expression
    def readable(cls):
        return case([
                     (cls._readable != None, cls._readable),
                     (cls.model != None, cls.model.readable)],
                    else_=None)

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
    defaultPositions = Column(String(500))
    defaultSpeed = Column(Integer)
    positionScale = Column(Float)
    speedScale = Column(Float)
    positionOffset = Column(Float)
    poseable = Column(Boolean)
    readable = Column(Boolean)
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
