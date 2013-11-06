import time
from Robot.servoInteface.servoInterface import ServoInterface
from base import Runner

class PoseRunner(Runner):
    
    class PoseHandle(Runner.ExecutionHandle):
        
        def __init__(self, pose):
            super(PoseRunner.PoseHandle, self).__init__(pose)
            self._pose = pose
        
        def run(self):
            interfaces = {}
            for jointPosition in self._pose.jointPositions:
                servos = filter(lambda s: s.jointName == jointPosition.jointName, self._robot.servos)
                if len(servos) != 1:
                    self._logger.critical("Could not determine appropriate servo on Robot(%s).  Expected 1 match, got %s", self._robot.name, len(servos))
                    raise ValueError
                    
                servoInterface = ServoInterface.getServoInterface(servos[0])
                servoInterface.setPosition(jointPosition.angle, jointPosition.speed)
                interfaces[jointPosition] = servoInterface
            
            for (jointPosition, interface) in interfaces:
                # TODO: better tolerance calculation
                while abs(interface.getPosition() - jointPosition.angle) > 10 and interface.isMoving() and not self._cancel:
                    time.sleep(0.001)
            
            if self._cancel:
                self._result = False
            else:
                self._result = all(lambda (j, i):abs(i.getPosition() - j.angle) <= 10, interfaces)
        
        def stop(self):
            self._cancel = True
            self.waitForComplete()
        
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
