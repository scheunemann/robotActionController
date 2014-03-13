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
    value_type = relationship("SensorValueType", back_populates="sensor")

    onState = Column(String(500))

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

    def __init__(self, name=None):
        self.name = name


class RobotSensor(Sensor):

    id = Column(Integer, ForeignKey('%s.id' % 'Sensor'), primary_key=True)

    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", back_populates="sensors")

    __mapper_args__ = {
            'polymorphic_identity': 'RobotSensor',
            'inherit_condition': (id == Sensor.id),
    }

    def __init__(self, name=None):
        super(RobotSensor, self).__init__(name)


class ExternalSensor(Sensor):

    id = Column(Integer, ForeignKey('%s.id' % 'Sensor'), primary_key=True)

    __mapper_args__ = {
            'polymorphic_identity': 'ExternalSensor',
            'inherit_condition': (id == Sensor.id),
    }

    def __init__(self, name):
        super(ExternalSensor, self).__init__(name)


class DiscreteSensorValue(StandardMixin, Base):

    value = Column(String(500))
    value_type_id = Column(Integer, ForeignKey("DiscreteValueType.id"))
    value_type = relationship("DiscreteValueType", back_populates="values")


class SensorValueType(StandardMixin, Base):

    type = Column(String(50))
    sensor = relationship("Sensor", back_populates="value_type")

    __mapper_args__ = {
            'polymorphic_identity': '',
            'polymorphic_on': type,
    }


class DiscreteValueType(SensorValueType):

    id = Column(Integer, ForeignKey('SensorValueType.id'), primary_key=True)

    values = relationship("DiscreteSensorValue", back_populates="value_type")

    __mapper_args__ = {
            'polymorphic_identity': 'Discrete',
            'inherit_condition': (id == SensorValueType.id),
    }

    def normalize(self, value):
        return value

    def isValid(self, value):
        return value in self.values or not self.values


class ContinuousValueType(SensorValueType):
    id = Column(Integer, ForeignKey('SensorValueType.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'Continuous',
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


class SensorGroup(StandardMixin, Base):
    name = Column(String(50))
    sensors = relationship("Sensor", back_populates="group")

    def __init__(self, name=None):
        super(SensorGroup, self).__init__()
        self.name = name


class SensorModel(StandardMixin, Base):
    name = Column(String(50))

    def __init__(self, name=None, version=None):
        super(SensorModel, self).__init__()
        self.name = name
        self.version = version


class SensorConfig(StandardMixin, Base):

    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", back_populates="sensorConfigs")

    model_id = Column(Integer, ForeignKey("SensorModel.id"))
    model = relationship("SensorModel")

    extraData = Column(PickleType)

    type = Column(String(50))
