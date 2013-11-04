from Base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

class Trigger(StandardMixin, Base):
    
    name = Column(String(50))
    type = Column(String(50))
    
    __mapper_args__ = {
            'polymorphic_identity':'Trigger',
            'polymorphic_on': type
        }
    
    action_id = Column(Integer, ForeignKey('Action.id'))
    action = relationship("Action", backref="triggers")
    
    def __init__(self, name=None):
        super(Trigger, self).__init__()
        self.name = name
    
class SensorTrigger(Trigger):
        
    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity':'Sensor',
    }
    
    sensorName = Column(String(50))
    sensorValue = Column(String(50))
    
class TimeTrigger(Trigger):
    
    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity':'Time',
    }    
                    
class ButtonTrigger(Trigger):
    
    id = Column(Integer, ForeignKey('%s.id' % 'Trigger'), primary_key=True)
    __mapper_args__ = {
            'polymorphic_identity':'Button',
    }
    
class ButtonHotKey(StandardMixin, Base):
    
    keyName = Column(String(1))
    modifiers = Column(String(50))
    trigger_id = Column(Integer, ForeignKey('ButtonTrigger.id'))
    trigger = relationship("ButtonTrigger", backref="hotKeys")
