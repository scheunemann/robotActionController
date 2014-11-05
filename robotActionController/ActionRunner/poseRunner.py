from base import ActionRunner
from collections import namedtuple
import logging
from gevent import sleep


class PoseRunner(ActionRunner):
    supportedClass = 'PoseAction'
    Runable = namedtuple('PoseAction', ActionRunner.Runable._fields + ('speedModifier', 'jointPositions'))
    JointPosition = namedtuple('JointPosition', ['jointName', 'speed', 'position', 'positions'])

    def __init__(self, pose, robot, *args, **kwargs):
        super(PoseRunner, self).__init__(pose)
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
            speed = speed * ((action.speedModifier / 100.0) or 1)
            position = float(jointPosition.position) if jointPosition.position != None else eval(jointPosition.positions or 'None')
            l.append((position, speed, servo))
            sleep(0)

        [servoInterface.setPosition(position, speed, False) for (position, speed, servoInterface) in l]
        moving = [si for _, _, si in l]

        # TODO: status messages now that it's non-blocking
        results = [True, ]
        while moving:
            for servoInterface in moving:
                if not servoInterface.isMoving():
                    moving.remove(servoInterface)
                # release the GIL
                sleep(0.01)

        if self._cancel:
            result = False
        else:
            result = all(results)

        return result

    @staticmethod
    def getRunable(action):
        if type(action) == dict and action.get('type', None) == PoseRunner.supportedClass:
            actionCopy = dict(action)
            positions = actionCopy['jointPositions']
            actionCopy['jointPositions'] = []
            for position in positions:
                actionCopy['jointPositions'].appen(PoseRunner.JointPosition(
                                                                            position['jointName'],
                                                                            int(position['speed']),
                                                                            float(position['position']),
                                                                            [float(p) for p in position['positions']]))

            return PoseRunner.Runable(
                                      actionCopy['name'],
                                      actionCopy.get('id'),
                                      actionCopy['type'],
                                      actionCopy['speedModifier'],
                                      actionCopy['jointPositions'])
        elif action.type == PoseRunner.supportedClass:
            positions = []
            for position in action.jointPositions:
                positions.append(PoseRunner.JointPosition(position.jointName, position.speed, position.position, position.positions))

            return PoseRunner.Runable(action.name, action.id, action.type, action.speedModifier, positions)
        else:
            logger = logging.getLogger(PoseRunner.__name__)
            logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
            return None

    def isValid(self, pose):
        if len(pose.jointPositions) > 0:
            for jointPosition in pose.jointPositions:
                if len(filter(lambda s: s.jointName == jointPosition.jointName, self._robot.servos)) == 0:
                    return False
            return True
        else:
            return False
