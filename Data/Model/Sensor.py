from Base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

class Sensor(StandardMixin, Base):
    
    name = Column(String(50))
    type = Column(String(50))
    
    model_id = Column(Integer, ForeignKey("SensorModel.id")) 
    model = relationship("SensorModel")
    
    robot_id = Column(Integer, ForeignKey("Robot.id"))
    robot = relationship("Robot", backref="sensors")
    
    group_id = Column(Integer, ForeignKey("SensorGroup.id"))
    group = relationship("SensorGroup", backref="sensors")
    
    __mapper_args__ = {
            'polymorphic_identity':'Sensor',
            'polymorphic_on': type
        }

    def normalize(self, value):
        return value
    
    def isValid(self, value):
        return value != None

class DiscreteSensorValues(StandardMixin, Base):
    
    value = Column(String(500))
    sensor_id = Column(Integer, ForeignKey("DiscreteSensor.id"))
    sensor = relationship("DiscreteSensor", backref="values")

class DiscreteSensor(Sensor):
    
    id = Column(Integer, ForeignKey('Sensor.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity':'Discrete',
    }
    
    def isValid(self, value):
        try:
            self.values.index(value)
            return True
        except:
            return False

class ContinuousSensor(Sensor):
    id = Column(Integer, ForeignKey('Sensor.id'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity':'Continuous',
    }
    
    minValue = Column(Integer)
    maxValue = Column(Integer)
    
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
