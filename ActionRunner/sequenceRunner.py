from base import ActionRunner, ActionExecutionHandle
from collections import namedtuple
import logging


class SequenceExecutionHandle(ActionExecutionHandle):

    def __init__(self, sequence, robot):
        super(SequenceExecutionHandle, self).__init__(sequence, ActionRunner(robot))
        self._robot = robot
        self._cancel = False

    def _runInternal(self, action):
        result = True
        for a in action.actions:
            actionResult = self._runner.execute(a)
            if self._cancel or not actionResult:
                result = False
                break
            else:
                result = result and actionResult

        return result

    def stop(self):
        self._cancel = True
        self.waitForComplete()


class SequenceRunner(ActionRunner):
    supportedClass = 'SequenceAction'
    Runable = namedtuple('SequenceAction', ActionRunner.Runable._fields + ('actions', ))

    @staticmethod
    def getRunable(action):
        if action.type == SequenceRunner.supportedClass:
            actions = []
            for a in action.actions:
                actions.append(ActionRunner.getRunable(a))

            return SequenceRunner.Runable(action.name, action.id, action.type, action.minLength, actions)
        else:
            logger = logging.getLogger(SequenceRunner.__name__)
            logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
            return None

    def __init__(self, robot):
        super(SequenceRunner, self).__init__(robot)

    def isValid(self, sequence):
        valid = True
        for action in sequence.actions:
            valid = valid & ActionRunner(self.robot).isValid(action)
            if not valid:
                break

    def _getHandle(self, action):
        return SequenceExecutionHandle(action, self._robot)
