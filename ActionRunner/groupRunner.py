from multiprocessing.pool import ThreadPool

from Data.Model import Group
from actionRunner import ActionRunner
from base import Runner

class GroupRunner(Runner):
    @property
    @staticmethod
    def supportedClass():
        return Group
    
    def __init__(self, robot):
        super(GroupRunner, self).__init__(robot)
        self._threadPool = ThreadPool()

    def isValid(self, group):
        valid = True
        for action in group.actions:
            valid = valid & ActionRunner(self.robot).isValid(action)
            if not valid:
                break

    def execute(self, group):
        self._threadPool.map(lambda a: ActionRunner(self._robot).execute(a), group.actions)
