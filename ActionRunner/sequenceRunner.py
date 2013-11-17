from Data.Model import Sequence, Robot
from base import Runner
from actionRunner import ActionRunner


class SequenceRunner(Runner):

    class SequenceHandle(Runner.ExecutionHandle):

        def __init__(self, sequence, robot):
            super(SequenceRunner.SequenceHandle, self).__init__(sequence)
            self._robot = robot

        def _runInternal(self, action, session):
            robot = session.query(Robot).get(self._robotId)
            ar = ActionRunner(robot)
            result = True
            for orderedAction in sorted(action.actions, key=lambda a: a.order):
                actionResult = ar.execute(orderedAction.action)
                if self._cancel:
                    result = False
                    break
                else:
                    result = result and actionResult

            return result

    supportedClass = Sequence

    def __init__(self, robot):
        super(SequenceRunner, self).__init__(robot)

    def isValid(self, sequence):
        valid = True
        for action in sequence.actions:
            valid = valid & ActionRunner(self.robot).isValid(action)
            if not valid:
                break

    def _getHandle(self, action):
        return SequenceRunner.SequenceHandle(action, self._robot)
