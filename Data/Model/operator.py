from base import StandardMixin, Base
from sqlalchemy import Column, String, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship

operatorUsers_table = Table('operatorUsers', Base.metadata,
    Column('Operator_id', Integer, ForeignKey('Operator.id')),
    Column('User_id', Integer, ForeignKey('User.id'))
)


class Operator(StandardMixin, Base):
    name = Column(String(50))
    fullname = Column(String(50))
    password = Column(String(500))
    users = relationship("User", secondary=operatorUsers_table)

    def __init__(self, name=None, fullname=None):
        super(Operator, self).__init__()
        self.name = name
        self.fullname = fullname
