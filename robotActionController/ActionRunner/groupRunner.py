from collections import namedtuple
import logging
from base import ActionRunner, ActionManager
from gevent.pool import Group


class GroupRunner(ActionRunner):
    supportedClass = 'GroupAction'
    Runable = namedtuple('GroupAction', ActionRunner.Runable._fields + ('actions', ))

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
        if action.type == GroupRunner.supportedClass:
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

