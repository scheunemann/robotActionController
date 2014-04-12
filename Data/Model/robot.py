from base import StandardMixin, Base
from sqlalchemy import Column, Integer, ForeignKey, String, PickleType
from sqlalchemy.orm import relationship


__all__ = ['Robot', 'RobotModel', ]


class Robot(StandardMixin, Base):
    name = Column(String(50))
    version = Column(String(50))

    model_id = Column(Integer, ForeignKey("RobotModel.id"))
    model = relationship("RobotModel")

    defaultAction_id = Column(Integer, ForeignKey("Action.id"))
    defaultAction = relationship("Action")

    sensors = relationship("RobotSensor", back_populates="robot")
    servos = relationship("Servo", back_populates="robot", lazy=False)
    servoGroups = relationship("ServoGroup", back_populates="robot")
    sensorConfigs = relationship("SensorConfig", back_populates="robot")
    servoConfigs = relationship("ServoConfig", back_populates="robot", lazy=False)

    def __init__(self, name=None, version=None, model=None, model_id=None, defaultAction=None, defaultAction_id=None, sensors=[], servos=[], servoGroups=[], sensorConfigs=[], servoConfigs=[], **kwargs):
        super(Robot, self).__init__(**kwargs)
        self.name = name
        self.version = version
        self.model = model
        self.model_id = model_id
        self.defaultAction = defaultAction
        self.defaultAction_id = defaultAction_id
        self.sensors = sensors
        self.servos = servos
        self.servoGroups = servoGroups
        self.sensorConfigs = sensorConfigs
        self.servoConfigs = servoConfigs


class RobotModel(StandardMixin, Base):
    extraData = Column(PickleType)
    name = Column(String(50))

    def __init__(self, name=None, extraData=None, **kwargs):
        super(RobotModel, self).__init__(**kwargs)
        self.name = name
        self.extraData = extraData
