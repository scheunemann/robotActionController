from collections import namedtuple
import logging
from base import ActionRunner, ActionExecutionHandle


class GroupExecutionHandle(ActionExecutionHandle):

    def __init__(self, group, robot):
        super(GroupRunner.GroupHandle, self).__init__(group)
        self._robot = robot

    def _runInternal(self, action):
        self._handles = [ActionRunner(self._robot).executeAsync(a) for a in action.actions]
        return self.waitForComplete()


class GroupRunner(ActionRunner):
    supportedClass = 'GroupAction'
    Runable = namedtuple(GroupRunner.supportedClass, ActionRunner.Runable._fields + ('actions', ))

    @staticmethod
    def getRunable(action):
        if action.type == GroupRunner.supportedClass:
            actions = []
            for a in action.actions:
                actions.append(ActionRunner.getRunable(a))

            return GroupRunner.Runable(action.name, action.id, action.type, action.minLength, actions)
        else:
            logger = logging.getLogger(GroupRunner.__name__)
            logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
            return None

    def __init__(self, robot):
        super(GroupRunner, self).__init__(robot)

    def isValid(self, group):
        valid = True
        for action in group.actions:
            valid = valid & ActionRunner(self._robot).isValid(action)
            if not valid:
                break

    def _getHandle(self, action):
        return GroupExecutionHandle(action, self._robot)
