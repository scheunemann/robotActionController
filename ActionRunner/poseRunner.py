import threading
from base import ActionRunner, ActionExecutionHandle
from collections import namedtuple
import logging


class PoseExecutionHandle(ActionExecutionHandle):

    def __init__(self, pose, robot):
        super(PoseExecutionHandle, self).__init__(pose)
        self._robot = robot

    def _runInternal(self, action):
        self._cancel = False

        l = []
        for jointPosition in action.jointPositions:
            servos = filter(lambda s: s.jointName == jointPosition.jointName, self._robot.servos)
            if len(servos) != 1:
                self._logger.critical("Could not determine appropriate servo(%s) on Robot(%s).  Expected 1 match, got %s" % (jointPosition.jointName, self._robot.name, len(servos)))
                raise ValueError("Could not determine appropriate servo(%s) on Robot(%s).  Expected 1 match, got %s" % (jointPosition.jointName, self._robot.name, len(servos)))
            servo = servos[0]
            speed = jointPosition.speed
            speed = speed * (action.speedModifier or 1)
            position = float(jointPosition.position) if jointPosition.position != None else eval(jointPosition.positions or 'None')
            l.append((position, speed, servo))

        results = [servoInterface.setPosition(position, speed) for (position, speed, servoInterface) in l]

        if self._cancel:
            result = False
        else:
            # TODO: Make all joints blocking?
            result = all(results)

        return result

    def waitForComplete(self):
        if not self is threading.current_thread():
            self.join()

        return self._result

    def stop(self):
        self._cancel = True
        self.waitForComplete()


class PoseRunner(ActionRunner):
    supportedClass = 'PoseAction'
    Runable = namedtuple('PoseAction', ActionRunner.Runable._fields + ('speedModifier', 'jointPositions'))
    JointPosition = namedtuple('JointPosition', ['jointName', 'speed', 'position', 'positions'])

    @staticmethod
    def getRunable(action):
        if action.type == PoseRunner.supportedClass:
            positions = []
            for position in action.jointPositions:
                positions.append(PoseRunner.JointPosition(position.jointName, position.speed, position.position, position.positions))

            return PoseRunner.Runable(action.name, action.id, action.type, action.minLength, action.speedModifier, positions)
        else:
            logger = logging.getLogger(PoseRunner.__name__)
            logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
            return None

    def __init__(self, robot):
        super(PoseRunner, self).__init__(robot)

    def isValid(self, pose):
        if len(pose.jointPositions) > 0:
            for jointPosition in pose.jointPositions:
                if len(filter(lambda s: s.jointName == jointPosition.jointName, self._robot.servos)) == 0:
                    return False
            return True
        else:
            return False

    def _getHandle(self, action):
        return PoseExecutionHandle(action, self._robot)
