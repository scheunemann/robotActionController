from Data.Model import Sequence
from base import Runner
from actionRunner import ActionRunner

class SequenceRunner(Runner):

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

    def execute(self, sequence):
        ar = ActionRunner(self._robot)
        for orderedAction in sorted(sequence.actions, key=lambda a: a.order):
            ar.execute(orderedAction.action)
