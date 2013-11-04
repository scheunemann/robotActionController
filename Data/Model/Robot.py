from Base import StandardMixin, Base
from sqlalchemy import Column, Integer, ForeignKey, String, PickleType
from sqlalchemy.orm import relationship

class Robot(StandardMixin, Base):
    name = Column(String(50))
    version = Column(String(50))
    type_id = Column(Integer, ForeignKey("RobotType.id")) 
    type = relationship("RobotType")

    def __init__(self, name=None, version=None, type_=None):
        super(Robot, self).__init__()
        self.name = name
        self.version = version
        self.type = type_

class RobotType(StandardMixin, Base):
    extraData = Column(PickleType)
    name = Column(String(50))
    
    def __init__(self, name=None, extraData=None):
        super(RobotType, self).__init__()
        self.name = name
        self.extraData = extraData