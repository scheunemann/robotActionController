from base import StandardMixin, Base
from sqlalchemy import Column, Integer, ForeignKey, String, PickleType
from sqlalchemy.orm import relationship


class Robot(StandardMixin, Base):
    name = Column(String(50))
    version = Column(String(50))

    model_id = Column(Integer, ForeignKey("RobotModel.id"))
    model = relationship("RobotModel")

    sensors = relationship("RobotSensor", back_populates="robot")
    servos = relationship("Servo", back_populates="robot", lazy=False)
    servoGroups = relationship("ServoGroup", back_populates="robot")
    sensorConfigs = relationship("SensorConfig", back_populates="robot")
    servoConfigs = relationship("ServoConfig", back_populates="robot", lazy=False)

    def __init__(self, name=None, version=None, model=None):
        super(Robot, self).__init__()
        self.name = name
        self.version = version
        self.model = model


class RobotModel(StandardMixin, Base):
    extraData = Column(PickleType)
    name = Column(String(50))

    def __init__(self, name=None, extraData=None):
        super(RobotModel, self).__init__()
        self.name = name
        self.extraData = extraData
