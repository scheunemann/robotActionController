from base import ActionRunner
from collections import namedtuple
import logging
import time


class SequenceRunner(ActionRunner):
    supportedClass = 'SequenceAction'
    Runable = namedtuple('SequenceAction', ActionRunner.Runable._fields + ('actions', ))
    OrderedAction = namedtuple('OrderedAction', ('forcedLength', 'action'))

    def __init__(self, sequence, robot):
        super(SequenceRunner, self).__init__(sequence, ActionRunner(robot))
        self._robot = robot

    def _runInternal(self, action):
        result = True
        for orderedAction in action.actions:
            if orderedAction.forcedLength:
                start = time.time()
                handle = self._runner.executeAsync(orderedAction.action)
                while not self._cancel:
                    elapsed = time.time() - start
                    if elapsed < 0:
                        break  # system clock rolled back
                    if elapsed * 1000 >= orderedAction.forcedLength:
                        break
                    time.sleep(0.01)
                actionResult = handle.result
            else:
                actionResult = self._runner.execute(orderedAction.action)

            if self._cancel or not actionResult:
                result = False
                break
            else:
                result = result and actionResult
            #Release the GIL
            time.sleep(0.0001)

        return result

    @staticmethod
    def getRunable(action):
        if action.type == SequenceRunner.supportedClass:
            actions = []
            for orderedAction in action.actions:
                actions.append(SequenceRunner.OrderedAction(orderedAction.forcedLength, ActionRunner.getRunable(orderedAction.action)))

            return SequenceRunner.Runable(action.name, action.id, action.type, actions)
        else:
            logger = logging.getLogger(SequenceRunner.__name__)
            logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
            return None

    def isValid(self, sequence):
        valid = True
        for action in sequence.actions:
            valid = valid & ActionRunner(self.robot).isValid(action)
            if not valid:
                break
