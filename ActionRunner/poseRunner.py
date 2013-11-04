import time
from Robot.servoInteface.servoInterface import ServoInterface

class PoseRunner(object):
    
    def __init__(self, robot):
        super(PoseRunner, self).__init__(robot)

    def execute(self, pose):
        interfaces = {}
        for jointPosition in pose.jointPositions:
            servos = filter(lambda s: s.jointName == jointPosition.jointName, self._robot.servos)
            if len(servos) != 1:
                self._logger.critical("Could not determine appropriate servo on Robot(%s).  Expected 1 match, got %s", self._robot.name, len(servos))
                raise ValueError
                
            servoInterface = ServoInterface.getServoInterface(servos[0])
            servoInterface.setPosition(jointPosition.angle, jointPosition.speed)
            interfaces[jointPosition] = servoInterface
            
        for (jointPosition, interface) in interfaces:
            # TODO: better tolerance
            while abs(interface.getPosition() - jointPosition.angle) > 10 and interface.isMoving():
                time.sleep(0.001)

    def isValid(self, pose):
        if len(pose.jointPositions) > 0:
            for jointPosition in pose.jointPositions:
                if len(filter(lambda s: s.jointName == jointPosition.jointName, self._robot.servos)) == 0:
                    return False
            return True
        else:
            return False
