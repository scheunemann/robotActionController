from Data.Model import SequenceAction
from base import Runner
from actionRunner import ActionRunner


class SequenceRunner(Runner):

    class SequenceHandle(Runner.ExecutionHandle):

        def __init__(self, sequence, robot):
            super(SequenceRunner.SequenceHandle, self).__init__(sequence)
            self._robot = robot
            self._cancel = False

        def _runInternal(self, action, session):
            robot = session.merge(self._robot, load=False)
            ar = ActionRunner(robot)
            result = True
            for action in action.actions:
                actionResult = ar.execute(action)
                if self._cancel or not actionResult:
                    result = False
                    break
                else:
                    result = result and actionResult

            return result

        def stop(self):
            self._cancel = True
            self.waitForComplete()

    supportedClass = SequenceAction

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
