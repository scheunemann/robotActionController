from Data.Model import Group
from actionRunner import ActionRunner
from base import Runner

class GroupRunner(Runner):

    class GroupHandle(Runner.ExecutionHandle):

        def __init__(self, group, robot):
            super(GroupRunner.GroupHandle, self).__init__(group)
            self._group = group
            self._robot = robot

        def run(self):
            self._handles = [ActionRunner(self._robot).executeAsync(a) for a in self._actions]
            self.waitForComplete()

    supportedClass = Group

    def __init__(self, robot):
        super(GroupRunner, self).__init__(robot)

    def isValid(self, group):
        valid = True
        for action in group.actions:
            valid = valid & ActionRunner(self._robot).isValid(action)
            if not valid:
                break

    def _getHandle(self, action):
        handle = GroupRunner.GroupHandle(action, self._robot)
        return handle
