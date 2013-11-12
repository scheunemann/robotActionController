from base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship


class Sensor(StandardMixin, Base):

    name = Column(String(50))
    type = Column(String(50))

    model_id = Column(Integer, ForeignKey("SensorModel.id"))
    model = relationship("SensorModel")

    group_id = Column(Integer, ForeignKey("SensorGroup.id"))
    group = relationship("SensorGroup", backref="sensors")

    value_type_id = Column(Integer, ForeignKey("SensorValueType.id"))
    value_type = relationship("SensorValueType", backref="sensor")

    __mapper_args__ = {
            'polymorphic_identity': 'Sensor',
            'polymorphic_on': type
        }

    def normalize(self, value):
        return value

    def isValid(self, value):
        return value != None


class RobotSensor(Sensor):

    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", backref="sensors")
    __mapper_args__ = {
            'polymorphic_identity': 'Sensor',
            'polymorphic_on': type
    }


class ExternalSensor(Sensor):

    __mapper_args__ = {
            'polymorphic_identity': 'Sensor',
            'polymorphic_on': type
    }


class DiscreteSensorValues(StandardMixin, Base):

    value = Column(String(500))
    value_type_id = Column(Integer, ForeignKey("DiscreteValueType.id"))
    value_type = relationship("DiscreteValueType", backref="values")


class SensorValueType(StandardMixin, Base):
    pass


class DiscreteValueType(SensorValueType):

    id = Column(Integer, ForeignKey('Sensor.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'Discrete',
    }

    def isValid(self, value):
        return value in self.values or not self.values


class ContinuousValueType(SensorValueType):
    id = Column(Integer, ForeignKey('Sensor.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity': 'Continuous',
    }

    minValue = Column(Float)
    maxValue = Column(Float)

    def normalize(self, value):
        if not self.isValid(value):
            raise ValueError("Given value is not valid")

        return (value - float(self.minValue)) / (self.maxValue - float(self.minValue))

    def isValid(self, value):
        return value <= self.maxValue and value >= self.minValue


class SensorGroup(StandardMixin, Base):
    name = Column(String(50))

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
    robot = relationship("Robot", backref="sensorConfigs")

    model_id = Column(Integer, ForeignKey("SensorModel.id"))
    model = relationship("SensorModel")
