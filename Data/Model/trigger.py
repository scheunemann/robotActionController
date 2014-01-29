from base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

__all__ = ['ButtonHotKey', 'ButtonTrigger', 'SensorTrigger', 'TimeTrigger', 'Trigger', ]


class Trigger(StandardMixin, Base):

    name = Column(String(50))
    type = Column(String(50))

    action_id = Column(Integer, ForeignKey('Action.id'))
    action = relationship("Action", back_populates="triggers")

    overrides = relationship("CustomTrigger", back_populates="overridden", foreign_keys="CustomTrigger.overridden_id")

    __mapper_args__ = {
            'polymorphic_identity': 'Trigger',
            'polymorphic_on': type
    }

    def __init__(self, name=None):
        super(Trigger, self).__init__()
        self.name = name


class SensorTrigger(Trigger):

    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)
    sensorName = Column(String(50))
    sensorValue = Column(String(50))

    __mapper_args__ = {
            'polymorphic_identity': 'Sensor',
    }


class TimeTrigger(Trigger):

    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)

    __mapper_args__ = {
            'polymorphic_identity': 'Time',
    }


class ButtonTrigger(Trigger):

    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)

    hotKeys = relationship("ButtonHotKey", back_populates="trigger")

    __mapper_args__ = {
            'polymorphic_identity': 'Button',
    }


class ButtonHotKey(StandardMixin, Base):

    keyCode = Column(Integer)
    modifiers = Column(String(50))

    trigger_id = Column(Integer, ForeignKey('ButtonTrigger.id'))
    trigger = relationship("ButtonTrigger", back_populates="hotKeys")
