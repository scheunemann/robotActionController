import logging
from base import ActionRunner, ActionManager
from collections import namedtuple
from gevent.pool import Group
from robotActionController.Data.storage import StorageFactory
from robotActionController.Data.Model import Action


class GroupRunner(ActionRunner):
    supportedClass = 'GroupAction'
    Runable = namedtuple('GroupAction', ActionRunner.Runable._fields + ('actions',))

    def __init__(self, group, robot, *args, **kwargs):
        super(GroupRunner, self).__init__(group)
        self._robot = robot
        self._handle = None

    def _runInternal(self, action):
        manager = ActionManager.getManager(self._robot)
        self._handle = Group()
        [self._handle.add(manager.executeActionAsync(a)) for a in action.actions]
        self.waitForComplete()
        self._output.extend([o for h in self._handle.greenlets for o in h.output])
        return all([x.value for x in self._handle.greenlets])

    @staticmethod
    def getRunable(action):
        if type(action) == dict and action.get('type', None) == GroupRunner.supportedClass:
            actionCopy = dict(action)
            actions = actionCopy['actions']
            actionCopy['actions'] = []
            for groupAction in actions:
                action = None
                if 'action' not in groupAction:
                    id_ = groupAction.get('action_id', None) or groupAction.get('id', None)
                    if id_:
                        session = StorageFactory.getNewSession()
                        action = ActionRunner.getRunable(session.query(Action).get(id_))
                        session.close()
                else:
                    action = ActionRunner.getRunable(groupAction['action'])

                actionCopy['actions'].append(action)
            return GroupRunner.Runable(actionCopy['name'],
                                       actionCopy.get('id', None),
                                       actionCopy['type'],
                                       actionCopy['actions'])
        elif action.type == GroupRunner.supportedClass:
            actions = [ActionRunner.getRunable(a) for a in action.actions]
            return GroupRunner.Runable(action.name, action.id, action.type, actions)
        else:
            logger = logging.getLogger(GroupRunner.__name__)
            logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
            return None

    def isValid(self, group):
        valid = True
        for action in group.actions:
            valid = valid & ActionRunner(self._robot).isValid(action)
            if not valid:
                break

    def waitForComplete(self):
        if self._handle:
            self._handle.join()

