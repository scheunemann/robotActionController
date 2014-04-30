from base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey, Float, PickleType
from sqlalchemy.orm import relationship


__all__ = ['ContinuousValueType', 'DiscreteSensorValue', 'DiscreteValueType', 'ExternalSensor', 'RobotSensor', 'Sensor', 'SensorGroup', 'SensorConfig', 'SensorModel', 'SensorValueType']


class Sensor(StandardMixin, Base):

    name = Column(String(50))
    type = Column(String(50))

    model_id = Column(Integer, ForeignKey("SensorModel.id"))
    model = relationship("SensorModel")

    group_id = Column(Integer, ForeignKey("SensorGroup.id"))
    group = relationship("SensorGroup", back_populates="sensors")

    value_type_id = Column(Integer, ForeignKey("SensorValueType.id"))
    value_type = relationship("SensorValueType")

    onStateComparison = Column(String(2))
    onStateValue = Column(String(500))

    extraData = Column(PickleType)

    __mapper_args__ = {
            'polymorphic_identity': 'Sensor',
            'polymorphic_on': type
        }

    def normalize(self, value):
        if self.value_type != None:
            return self.value_type.normalize(value)
        else:
            return value

    def isValid(self, value):
        if self.value_type != None:
            return self.value_type.isValid(value)
        else:
            return value != None

    def __init__(self, name=None, model_id=None, model=None, group_id=None, group=None, value_type_id=None, value_type=None, onStateComparison=None, onStateValue=None, extraData=None, **kwargs):
        super(Sensor, self).__init__(**kwargs)
        self.name = name
        self.model_id = model_id
        self.model = model
        self.group_id = group_id
        self.group = group
        self.value_type_id = value_type_id
        self.value_type = value_type
        self.onStateComparison = onStateComparison
        self.onStateValue = onStateValue
        self.extraData = extraData


class RobotSensor(Sensor):

    id = Column(Integer, ForeignKey('%s.id' % 'Sensor'), primary_key=True)

    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", back_populates="sensors")

    __mapper_args__ = {
            'polymorphic_identity': 'RobotSensor',
            'inherit_condition': (id == Sensor.id),
    }

    def __init__(self, robot=None, robot_id=None, **kwargs):
        super(RobotSensor, self).__init__(**kwargs)
        self.robot_id = robot_id
        self.robot = robot


class ExternalSensor(Sensor):

    id = Column(Integer, ForeignKey('%s.id' % 'Sensor'), primary_key=True)

    __mapper_args__ = {
            'polymorphic_identity': 'ExternalSensor',
            'inherit_condition': (id == Sensor.id),
    }

    def __init__(self, **kwargs):
        super(ExternalSensor, self).__init__(**kwargs)


class DiscreteSensorValue(StandardMixin, Base):

    value = Column(String(500))
    value_type_id = Column(Integer, ForeignKey("DiscreteValueType.id"))
    value_type = relationship("DiscreteValueType", back_populates="values")

    def __init__(self, value=None, value_type_id=None, value_type=None, **kwargs):
        super(DiscreteSensorValue, self).__init__(**kwargs)
        self.value = value
        self.value_type = value_type
        self.value_type_id = value_type_id


class SensorValueType(StandardMixin, Base):

    type = Column(String(50))

    __mapper_args__ = {
            'polymorphic_identity': 'SensorValueType',
            'polymorphic_on': type,
    }

    def __init__(self, **kwargs):
        super(SensorValueType, self).__init__(**kwargs)


class DiscreteValueType(SensorValueType):

    id = Column(Integer, ForeignKey('SensorValueType.id'), primary_key=True)

    values = relationship("DiscreteSensorValue", back_populates="value_type")

    __mapper_args__ = {
            'polymorphic_identity': 'DiscreteValueType',
            'inherit_condition': (id == SensorValueType.id),
    }

    def normalize(self, value):
        return value

    def isValid(self, value):
        return value in self.values or not self.values

    def __init__(self, values=None, **kwargs):
        super(DiscreteValueType, self).__init__(**kwargs)
        self.values = values


class ContinuousValueType(SensorValueType):
    id = Column(Integer, ForeignKey('SensorValueType.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'ContinuousValueType',
            'inherit_condition': (id == SensorValueType.id),
    }

    minValue = Column(Float, nullable=False)
    maxValue = Column(Float, nullable=False)
    precision = Column(Integer, nullable=False)

    def normalize(self, value):
        if not self.isValid(value):
            raise ValueError("Given value is not valid")

        return round((value - float(self.minValue)) / (self.maxValue - float(self.minValue)), self.precision)

    def isValid(self, value):
        return value <= self.maxValue and value >= self.minValue

    def __init__(self, minValue=None, maxValue=None, precision=None, **kwargs):
        super(ContinuousValueType, self).__init__(**kwargs)
        self.minValue = minValue
        self.maxValue = maxValue
        self.precision = precision


class SensorGroup(StandardMixin, Base):
    name = Column(String(50))
    sensors = relationship("Sensor", back_populates="group")

    def __init__(self, name=None, sensors=None, **kwargs):
        super(SensorGroup, self).__init__(**kwargs)
        self.name = name
        self.sensors = sensors


class SensorModel(StandardMixin, Base):
    name = Column(String(50))

    def __init__(self, name=None, **kwargs):
        super(SensorModel, self).__init__(**kwargs)
        self.name = name


class SensorConfig(StandardMixin, Base):

    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", back_populates="sensorConfigs")

    model_id = Column(Integer, ForeignKey("SensorModel.id"))
    model = relationship("SensorModel")

    port = Column(String(50))
    portSpeed = Column(Integer)
    extraData = Column(PickleType)

    type = Column(String(50))

    def __init__(self, robot_id=None, robot=None, model_id=None, model=None, port=None, portSpeed=None, extraData=None, **kwargs):
        super(SensorConfig, self).__init__(**kwargs)
        self.robot_id = robot_id
        self.robot = robot
        self.model_id = model_id
        self.model = model
        self.port = port
        self.portSpeed = portSpeed
        self.extraData = extraData
