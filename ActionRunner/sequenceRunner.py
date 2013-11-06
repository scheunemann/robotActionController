from Data.Model import Sequence
from base import Runner
from actionRunner import ActionRunner

class SequenceRunner(Runner):

    class SequenceHandle(Runner.ExecutionHandle):
        
        def __init__(self, sequence, robot):
            super(SequenceRunner.SequenceHandle, self).__init__(sequence)
            self._sequence = sequence
            self._robot = robot
        
        def run(self):
            ar = ActionRunner(self._robot)
            for orderedAction in sorted(self._sequence.actions, key=lambda a: a.order):
                self._handle = ar.executeAsync(orderedAction.action)
                self._handle.waitForComplete()
                if self._cancel:
                    self._result = False
                else:
                    self._result = self._result and self._handle.result
                
    @property
    @staticmethod
    def supportedClass():
        return Sequence

    def __init__(self, robot):
        super(SequenceRunner, self).__init__(robot)
        
    def isValid(self, sequence):
        valid = True
        for action in sequence.actions:
            valid = valid & ActionRunner(self.robot).isValid(action)
            if not valid:
                break

    def _getHandle(self, action):
        handle = SequenceRunner.SequenceHandle(action, self._robot)
        return handle
