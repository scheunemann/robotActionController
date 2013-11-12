from base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship


class User(StandardMixin, Base):
    name = Column(String(50))
    fullname = Column(String(50))
    speedmodifier = Column(Integer)
    customTriggers = relationship("CustomTrigger", backref="user")
    customActions = relationship("CustomAction", backref="user")

    def __init__(self, name=None, fullname=None):
        super(User, self).__init__()
        self.name = name
        self.fullname = fullname
        self.speedmodifier = 100


class CustomTrigger(StandardMixin, Base):
    name = Column(String(50))

    user_id = Column(Integer, ForeignKey('User.id'))
    overridden_id = Column(Integer, ForeignKey('Trigger.id'))
    redirect_id = Column(Integer, ForeignKey('Trigger.id'))

    overridden = relationship("Trigger", backref="overrides", foreign_keys=overridden_id)
    redirect = relationship("Trigger", foreign_keys=redirect_id)

    def __init__(self, name=None):
        super(CustomTrigger, self).__init__()
        self.name = name


class CustomAction(StandardMixin, Base):
    name = Column(String(50))

    user_id = Column(Integer, ForeignKey('User.id'))
    overridden_id = Column(Integer, ForeignKey('Action.id'))
    redirect_id = Column(Integer, ForeignKey('Action.id'))

    overridden = relationship("Action", backref="overrides", foreign_keys=overridden_id)
    redirect = relationship("Action", foreign_keys=redirect_id)

    def __init__(self, name=None):
        super(CustomAction, self).__init__()
        self.name = name
