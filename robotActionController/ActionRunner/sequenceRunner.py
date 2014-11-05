from base import ActionRunner, ActionManager
from collections import namedtuple
import logging
from datetime import datetime
from gevent import sleep
from robotActionController.Data.storage import StorageFactory
from robotActionController.Data.Model import Action

class SequenceRunner(ActionRunner):
    supportedClass = 'SequenceAction'
    Runable = namedtuple('SequenceAction', ActionRunner.Runable._fields + ('actions', ))
    OrderedAction = namedtuple('OrderedAction', ('forcedLength', 'order', 'action'))

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
        if type(action) == dict and action.get('type', None) == SequenceRunner.supportedClass:
            actionCopy = dict(action)
            actions = actionCopy['actions']
            actionCopy['actions'] = []
            for orderedAction in actions:
                action = None
                if 'action' not in orderedAction:
                    if 'action_id' in orderedAction:
                        session = StorageFactory.getNewSession()
                        action = ActionRunner.getRunable(session.query(Action).get(orderedAction['action_id']))
                        session.close()
                else:
                    action = ActionRunner.getRunable(orderedAction['action'])

                actionCopy['actions'].append(SequenceRunner.OrderedAction(
                                                                          int(orderedAction['forcedLength'])
                                                                          int(orderedAction['order']),
                                                                          action))
            return SequenceRunner.Runable(actionCopy['name'], actionCopy.get('id'), actionCopy['type'], actionCopy['actions'])
        elif action.type == SequenceRunner.supportedClass:
            actions = []
            for orderedAction in action.actions:
                actions.append(SequenceRunner.OrderedAction(orderedAction.forcedLength, orderedAction.order, ActionRunner.getRunable(orderedAction.action)))

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
