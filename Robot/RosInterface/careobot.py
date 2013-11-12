import math
import sys
import robot
import rosHelper
from collections import deque


class CareOBot(robot.ROSRobot):
    _imageFormats = ['BMP', 'EPS', 'GIF', 'IM', 'JPEG', 'PCD', 'PCX', 'PDF', 'PNG', 'PPM', 'TIFF', 'XBM', 'XPM']

    def __init__(self, name, rosMaster):
        rosHelper.ROS.configureROS(rosMaster=rosMaster)
        super(CareOBot, self).__init__(name, ActionLib, 'script_server')

    def getCameraAngle(self):
        state = self.getComponentState('head', True)
        if state == None:
            return None
        else:
            (_, cameraState) = state

        pos = cameraState['positions'][0]
        angle = round(math.degrees(pos), 2)
        angle = angle % 360

        return angle

    def setComponentState(self, name, value, blocking=True):
        # check if the component has been initialised, and init if it hasn't
        if len(self._ros.getTopics('/%(name)s_controller' % {'name': name})) == 0:
            self._robInt.initComponent(name)

        # Special handling of the unload_tray moveit code value='trayToTable:height'
        if name == 'arm' and str(value).startswith('trayToTable'):
            return self.unloadTray(str(value).split(':')[1], blocking)

        return super(CareOBot, self).setComponentState(name, value, blocking)

    def play(self, fileName, blocking=True):
        self.executeFunction("play", {
                                      'parameter_name': fileName,
                                      'blocking': blocking
                                      })

    def say(self, text, languageCode="en-gb", blocking=True):
        self.executeFunction("say", {
                                     'parameter_name': [text, ],
                                     'blocking': blocking
                                     })

    def sleep(self, milliseconds):
        self.executeFunction("sleep", {'duration': milliseconds / 1000.0})

    def unloadTray(self, height, blocking):

        try:
            h = float(height)
        except Exception as e:
            print >> sys.stderr, "Unable to cast height to float, received height: %s" % height

        try:
            client = UnloadTrayClient()
        except Exception as e:
            print >> sys.stderr, "Unable to initialise UnloadTrayClient. Error: %s" % repr(e)
            return self._ros._states[4]

        return client.unloadTray(h, blocking)


class UnloadTrayClient(object):

    def __init__(self):
        self._ros = rosHelper.ROS()
        self._ros.configureROS(packageName='accompany_user_tests_year2')
        import actionlib
        import accompany_user_tests_year2.msg
        self._ssMsgs = accompany_user_tests_year2.msg

        self._ros.initROS()
        self._client = actionlib.SimpleActionClient('/unload_tray', self._ssMsgs.UnloadTrayAction)
        print "Waiting for unload_tray"
        self._client.wait_for_server()
        print "Connected to unload_tray"

    def unloadTray(self, height, blocking):
        goal = self._ssMsgs.UnloadTrayGoal()
        goal.table_height = height

        if blocking:
            return self._ros._states[self._client.send_goal_and_wait(goal)]
        else:
            return self._ros._states[self._client.send_goal(goal)]


class ActionLib(robot.ActionLib):
    _specialCases = {
                    'light': {'function': 'set_light', 'mode': ''},
                    'sound': {'function': 'say', 'mode': 'FEST_EN'}
                    }

    def __init__(self):
        super(ActionLib, self).__init__('script_server', 'ScriptAction', 'ScriptGoal')

    def runFunction(self, funcName, kwargs):
        name = None
        value = None
        mode = None
        blocking = True
        service_name = None
        duration = None

        if 'component_name' in kwargs:
            name = str(kwargs['component_name']).encode('ascii', 'ignore')

        if 'parameter_name' in kwargs:
            value = str(kwargs['parameter_name']).encode('ascii', 'ignore')

        if 'mode' in kwargs:
            mode = str(kwargs['mode']).encode('ascii', 'ignore')

        if 'blocking' in kwargs:
            blocking = bool(kwargs['blocking'])

        if 'service_name' in kwargs:
            service_name = str(kwargs['service_name']).encode('ascii', 'ignore')

        if 'duration' in kwargs:
            duration = float(kwargs['duration'])

        goal = self._ssMsgs.ScriptGoal(
                          function_name=str(funcName).encode('ascii', 'ignore'),
                          component_name=name,
                          parameter_name=value,
                          mode=mode,
                          # blocking=blocking,
                          service_name=service_name,
                          duration=duration
                          )

        if blocking:
            return self._client.send_goal_and_wait(goal)
        else:
            return self._client.send_goal(goal)

    def initComponent(self, name):
        if name not in ActionLib._specialCases.keys():
            func = 'init'
            goal = self._ssMsgs.ScriptGoal(
                              function_name=func.encode('ascii', 'ignore'),
                              component_name=name.encode('ascii', 'ignore'))
            return self._client.send_goal_and_wait(goal)
        return 3

    def runComponent(self, name, value, mode=None, blocking=True):
        if name not in ActionLib._specialCases.keys():
            func = "move"
        else:
            func = ActionLib._specialCases[name]['function']
            mode = ActionLib._specialCases[name]['mode']

        goal = self._ssMsgs.ScriptGoal(
                          function_name=str(func).encode('ascii', 'ignore'),
                          component_name=str(name).encode('ascii', 'ignore'),
                          parameter_name=str(value).encode('ascii', 'ignore'),
                          mode=str(mode).encode('ascii', 'ignore'),
                          # blocking=bool(blocking)
                          )

        if(blocking):
            status = self._client.send_goal_and_wait(goal)
        else:
            self._client.send_goal(goal)
            status = 1

        return status


class PoseUpdater(robot.PoseUpdater):
    def __init__(self, robot):
        super(PoseUpdater, self).__init__(robot)
        self._rangeSensors = robot_config[robot.name]['phidgets']['topics']
        self._rangeThreshold = robot_config[robot.name]['tray']['size'] / 100.0
        self._rangeWindow = robot_config[robot.name]['phidgets']['windowSize']
        self._rangeHistory = {}

    def checkUpdatePose(self, robot):
        states = {}
        states.update(self.getTrayStates(robot))
        states.update(self.getHeadStates(robot))
        self.updateStates(states)

    def getHeadStates(self, robot):
        return {
                   'eyePosition': self.getComponentPosition(robot, 'head'),
                   }

    def getPhidgetState(self):
        trayIsEmpty = None

        averages = []
        for topic in self._rangeSensors:
            if topic not in self._rangeHistory:
                self._rangeHistory[topic] = deque()

            rangeMsg = self._ros.getSingleMessage(topic=topic, timeout=0.25)
            if rangeMsg == None:
                if topic not in self._warned:
                    self._warned.append(topic)
                    print "Phidget sensor not ready before timeout for topic: %s" % topic

                return (None, None)
            else:
                if topic in self._warned:
                    self._warned.remove(topic)

            self._rangeHistory[topic].append(rangeMsg.range)
            if len(self._rangeHistory[topic]) > self._rangeWindow:
                self._rangeHistory[topic].popleft()

            averages.append(sum(self._rangeHistory[topic]) / len(self._rangeHistory[topic]))

        if any(map(lambda x: x <= self._rangeThreshold, averages)):
            trayIsEmpty = 'Full'
        else:
            trayIsEmpty = 'Empty'

        return (trayIsEmpty, trayIsEmpty)

    def getComponentPosition(self, robot, componentName):
        (state, _) = robot.getComponentState(componentName)
        if state == None or state == '':
            print "No named component state for: %s." % (componentName)
            state = 'Unknown'

        return (state, state)

    def getTrayStates(self, robot):
        return {
                   'trayStatus': self.getComponentPosition(robot, 'tray'),
                   'trayIs': self.getPhidgetState()
               }
