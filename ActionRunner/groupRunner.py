from Data.Model import Group, Robot
from actionRunner import ActionRunner
from base import Runner


class GroupRunner(Runner):

    class GroupHandle(Runner.ExecutionHandle):

        def __init__(self, group, robot):
            super(GroupRunner.GroupHandle, self).__init__(group)
            self._robotId = robot.id

        def _runInternal(self, action, session):
            robot = session.query(Robot).get(self._robotId)
            self._handles = [ActionRunner(robot).executeAsync(a) for a in action.actions]
            return self.waitForComplete()

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
        return GroupRunner.GroupHandle(action, self._robot)
