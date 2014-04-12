from base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship

__all__ = ['ButtonHotkey', 'ButtonTrigger', 'SensorTrigger', 'TimeTrigger', 'Trigger', 'CompoundTrigger']


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

    def __init__(self, name=None, action_id=None, action=None, overrides=[], **kwargs):
        super(Trigger, self).__init__(**kwargs)
        self.name = name
        self.action_id = action_id
        self.action = action
        self.overrides = overrides


class SensorTrigger(Trigger):

    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)
    sensorName = Column(String(50))
    comparison = Column(String(2))  # >0, >=0, <0, <=0, ==0,=='abc'
    sensorValue = Column(String(50))

    __mapper_args__ = {
            'polymorphic_identity': 'SensorTrigger',
            'inherit_condition': (id == Trigger.id),
    }

    def __init__(self, sensorName=None, comparison=None, sensorValue=None, **kwargs):
        super(SensorTrigger, self).__init__(**kwargs)
        self.sensorName = sensorName
        self.comparison = comparison
        self.sensorValue = sensorValue


compoundTriggerTriggers_table = Table('compoundTriggerTriggers', Base.metadata,
    Column('CompoundTrigger_id', Integer, ForeignKey('CompoundTrigger.id', ondelete='cascade'), primary_key=True),
    Column('Trigger_id', Integer, ForeignKey('Trigger.id', ondelete='cascade'), primary_key=True)
)


class CompoundTrigger(Trigger):
    # All trigger
    # Any trigger
    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)
    requireAll = Column(Boolean, default=True)  # AND, OR
    triggers = relationship("Trigger", secondary=compoundTriggerTriggers_table)

    __mapper_args__ = {
            'polymorphic_identity': 'CompoundTrigger',
            'inherit_condition': (id == Trigger.id),
    }

    def __init__(self, requireAll, triggers, **kwargs):
        super(CompoundTrigger, self).__init__(**kwargs)
        self.requireAll = requireAll
        self.triggers = triggers


class TimeTrigger(Trigger):
    # Time (seconds)
    # Variance (seconds)
    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)
    time = Column(Integer)
    variance = Column(Integer, default=0)
    mustStayActive = Column(Boolean, default=False)
    trigger_id = Column(Integer, ForeignKey('Trigger.id'))
    trigger = relationship("Trigger", foreign_keys=trigger_id)

    __mapper_args__ = {
            'polymorphic_identity': 'TimeTrigger',
            'inherit_condition': (id == Trigger.id),
    }

    def __init__(self, time=None, variance=None, mustStayActive=None, trigger_id=None, trigger=None, **kwargs):
        super(TimeTrigger, self).__init__(**kwargs)
        self.time = time
        self.variance = variance
        self.mustStayActive = mustStayActive
        self.trigger_id = trigger_id
        self.trigger = trigger


class ButtonTrigger(Trigger):

    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)
    hotKeys = relationship("ButtonHotkey", back_populates="trigger")

    __mapper_args__ = {
            'polymorphic_identity': 'ButtonTrigger',
            'inherit_condition': (id == Trigger.id),
    }

    def __init__(self, hotKeys=[], **kwargs):
        super(ButtonTrigger, self).__init__(**kwargs)
        self.hotKeys = hotKeys


class ButtonHotkey(StandardMixin, Base):

    keyString = Column(String(50))

    trigger_id = Column(Integer, ForeignKey('ButtonTrigger.id'))
    trigger = relationship("ButtonTrigger", back_populates="hotKeys")

    def __init__(self, keyString=None, trigger_id=None, trigger=None, **kwargs):
        super(ButtonHotkey, self).__init__(**kwargs)
        self.keyString = keyString
        self.trigger_id = trigger_id
        self.trigger = trigger
