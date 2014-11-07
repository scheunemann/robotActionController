from collections import namedtuple
from robotActionController.Robot.ServoInterface import ServoInterface
from robotActionController.Processor.SensorInterface import SensorInterface


class Robot(object):
    Robot = namedtuple('Robot', ['name', 'id', 'servos', 'sensors'])
    _robots = {}

    @staticmethod
    def getRunableRobot(robot):
        if robot.id not in Robot._robots:
            interfaces = []
            sensors = []
            for servo in robot.servos:
                interfaces.append(ServoInterface.getServoInterface(servo))
            for sensor in robot.sensors:
                sensors.append(SensorInterface.getSensorInterface(sensor))

            Robot._robots[robot.id] = Robot.Robot(robot.name, robot.id, interfaces, sensors)
        return Robot._robots[robot.id]
