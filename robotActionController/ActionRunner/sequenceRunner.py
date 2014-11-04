from base import ActionRunner, ActionManager
from collections import namedtuple
import logging
from datetime import datetime
from gevent import sleep

class SequenceRunner(ActionRunner):
    supportedClass = 'SequenceAction'
    Runable = namedtuple('SequenceAction', ActionRunner.Runable._fields + ('actions', ))
    OrderedAction = namedtuple('OrderedAction', ('forcedLength', 'action'))

    def __init__(self, sequence, robot, *args, **kwargs):
        super(SequenceRunner, self).__init__(sequence)
        self._robot = robot

    def _runInternal(self, action):
        result = True
        manager = ActionManager.getManager(self._robot)
        
        for orderedAction in action.actions:
            handle = manager.executeActionAsync(orderedAction.action)
            if orderedAction.forcedLength:
                starttime = datetime.utcnow()
                while True:
                    elapsed = datetime.utcnow() - starttime
                    if elapsed.total_seconds() < 0:
                        break  # system clock rolled back
                    if elapsed.total_seconds() >= orderedAction.forcedLength:
                        break
                    sleep(0.01)
            else:
                handle.waitForComplete()

            actionResult = handle.value
            self._output.extend(handle.output)

            if not actionResult:
                result = False
                break
            else:
                result = result and actionResult
            #Allow other greenlets to run
            sleep(0)

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
