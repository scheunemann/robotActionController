from Data.Model import Trigger
from Data.Storage import StorageFactory


class TriggerProcessor(object):

    def __init__(self, robot, user):
        self._robot = robot
        self._ds = StorageFactory.getNewSession()

    def isActive(self, trigger, user=None):
        return False

    def getTriggers(self, user=None):
        return self._ds.query(Trigger).all()
