from base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship

__all__ = ['User', 'CustomTrigger', 'CustomAction', ]


class User(StandardMixin, Base):
    name = Column(String(50))
    fullname = Column(String(50))
    speedmodifier = Column(Integer)
    customTriggers = relationship("CustomTrigger")
    customActions = relationship("CustomAction")

    # Temporary? Used for humanDistance psudeo-sensor
    locX = Column(Float)
    locY = Column(Float)
    locTheta = Column(Float)

    def __init__(self, name=None, fullname=None):
        super(User, self).__init__()
        self.name = name
        self.fullname = fullname
        self.speedmodifier = 100


class CustomTrigger(StandardMixin, Base):
    name = Column(String(50))

    user_id = Column(Integer, ForeignKey('User.id'))
    user = relationship("User", back_populates="customTriggers")

    overridden_id = Column(Integer, ForeignKey('Trigger.id'))
    overridden = relationship("Trigger", back_populates="overrides", foreign_keys=[overridden_id])

    redirect_id = Column(Integer, ForeignKey('Trigger.id'))
    redirect = relationship("Trigger", foreign_keys=[redirect_id])

    def __init__(self, name=None):
        super(CustomTrigger, self).__init__()
        self.name = name


class CustomAction(StandardMixin, Base):
    name = Column(String(50))

    user_id = Column(Integer, ForeignKey('User.id'))
    user = relationship("User", back_populates="customActions")

    overridden_id = Column(Integer, ForeignKey('Action.id'))
    overridden = relationship("Action", back_populates="overrides", foreign_keys=overridden_id)

    redirect_id = Column(Integer, ForeignKey('Action.id'))
    redirect = relationship("Action", foreign_keys=redirect_id)

    def __init__(self, name=None):
        super(CustomAction, self).__init__()
        self.name = name
