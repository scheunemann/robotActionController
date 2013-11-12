import sys
import io
import math
import time

_states = {
        0: 'PENDING',
        1: 'ACTIVE',
        2: 'PREEMPTED',
        3: 'SUCCEEDED',
        4: 'ABORTED',
        5: 'REJECTED',
        6: 'PREEMPTING',
        7: 'RECALLING',
        8: 'RECALLED',
        9: 'LOST'}


class Robot(object):
    _imageFormats = ['BMP', 'EPS', 'GIF', 'IM', 'JPEG', 'PCD', 'PCX', 'PDF', 'PNG', 'PPM', 'TIFF', 'XBM', 'XPM']

    def __init__(self, name, robotInterface):
        self._name = name
        self._robIntClass = robotInterface
        self._robIntInstance = None

    @property
    def _robInt(self):
        if self._robIntInstance == None:
            self._robIntInstance = self._robIntClass()

        return self._robIntInstance

    @property
    def name(self):
        return self._name

    @property
    def _transform(self):
        return None

    def getImage(self, retFormat='PNG'):
        return None

    def play(self, fileName, blocking=True):
        print "Play: %s" % fileName

    def say(self, text, languageCode="en-gb", blocking=True):
        print "Say (%s): %s" % (languageCode, text)

    def sleep(self, milliseconds):
        time.sleep(milliseconds / 1000.0)

    def executeFunction(self, funcName, kwargs):
        return self._robInt.runFunction(funcName, kwargs)

    def getLocation(self, dontResolveName=False):
        return ('', (None, None, None))

    def setLight(self, colour):
        self._robInt.runComponent('light', colour)

    def setComponentState(self, name, value, blocking=True):
        status = self._robInt.runComponent(name, value, None, blocking)
        return _states[status]

    def getComponentPositions(self, componentName):
        return {}

    def getComponents(self):
        return []

    def getComponentState(self, componentName, dontResolveName=False):
        ret = {'name': '', 'positions': [], 'goals': [], 'joints': []}
        return ('', ret)

    def resolveComponentState(self, componentName, state, tolerance=0.5):
        if state == None:
            return (None, None)

        curPos = state['positions']

        positions = self.getComponentPositions(componentName)

        if len(positions) == 0:
            return ('', state)

        name = None
        diff = None
        for positionName in positions:
            positionValue = self._getValue(positions[positionName])
            if type(positionValue) is not list:
                # we don't currently handle nested types
                continue

            if len(positionValue) != len(curPos):
                # raise Exception("Arguement lengths don't match")
                continue

            dist = 0
            for index in range(len(positionValue)):
                dist += math.pow(curPos[index] - positionValue[index], 2)
            dist = math.sqrt(dist)
            if name == None or dist < diff:
                name = positionName
                diff = dist

        if diff <= tolerance:
            return (name, state)
        else:
            return ('', state)

    def _getValue(self, val):
        if type(val) is list:
            ret = val[0]
        else:
            ret = val

        return ret


class ROSRobot(Robot):
    _imageFormats = ['BMP', 'EPS', 'GIF', 'IM', 'JPEG', 'PCD', 'PCX', 'PDF', 'PNG', 'PPM', 'TIFF', 'XBM', 'XPM']

    def __init__(self, name, robotInterface, serverTopic):
        super(ROSRobot, self).__init__(name, robotInterface)
        self._rs = None
        self._tf = None
        self._serverTopic = serverTopic

    @property
    def _transform(self):
        if self._tf == None:
            try:
                import rosHelper
                self._tf = rosHelper.Transform(rosHelper=self._rs, toTopic='/map', fromTopic='/base_footprint')
            except Exception as e:
                print >> sys.stderr, "Error occured while calling transform: %s" % repr(e)
        return self._tf

    @property
    def _ros(self):
        if self._rs == None:
            import rosMulti
            # Wait to configure/initROS ROS till it's actually needed
            self._rs = rosMulti.ROS()
        return self._rs

    def getImage(self, imageTopic, retFormat='PNG'):
        img_msg = self._ros.getSingleMessage(imageTopic)
        if img_msg == None:
            return None

        from PIL import Image
        imgBytes = io.BytesIO()
        imgBytes.write(img_msg.data)

        imgBytes.seek(0)
        img = Image.open(imgBytes)

        retFormat = retFormat.upper()
        if retFormat == 'JPG':
            retFormat = 'JPEG'

        if retFormat not in Robot._imageFormats:
            retFormat = 'PNG'

        imgBytes.seek(0)
        img.save(imgBytes, retFormat)

        return imgBytes.getvalue()

    def getLocation(self, dontResolveName=False):
        tf = self._transform
        if tf == None:
            return ('', (None, None, None))

        ((x, y, _), rxy) = tf.getTransform()
        if x == None or y == None:
            return ('', (None, None, None))

        angle = round(math.degrees(rxy))
        pos = (round(x, 3), round(y, 3), angle)

        return ('', pos)

    def setComponentState(self, name, value, blocking=True):
        status = super(ROSRobot, self).setComponentState(name, value, blocking)
        # There is a bug in the Gazebo COB interface that prevents proper trajectory tracking
        # this causes most status messages to come back as aborted while the operation is still
        # commencing, time delay to attempt to compensate...
        if status != 3 and len(self._ros.getTopics('/gazebo')) > 0:
            time.sleep(1)
            print >> sys.stderr, 'Gazebo hack: state ' + self._rs._states[status] + ' changed to state ' + self._rs._states[3]
            return _states[3]

        return _states[status]

    def getComponentPositions(self, componentName):
        return self._ros.getParam('%s/%s' % (self._serverTopic, componentName))

    def getComponents(self):
        return self._ros.getParam(self._serverTopic).keys()

    def getComponentState(self, componentName, dontResolveName=False):
        topic = '/%(name)s_controller/state' % {'name': componentName}
        state = self._ros.getSingleMessage(topic)

        try:
            ret = {'name': componentName, 'positions': state.actual.positions, 'goals': state.desired.positions, 'joints': state.joint_names}
        except:
            print "Error retrieving joint state"
            ret = {'name': componentName, 'positions': (), 'goals': (), 'joints': ()}

        if dontResolveName:
            return ('', ret)
        else:
            return self.resolveComponentState(componentName, ret)


class ActionLib(object):

    def __init__(self, controllerName, actionName, goalName):
        import rosMulti
        ros = rosMulti.ROS()
        ros.configureROS(packageName='actionlib')
        ros.configureROS(packageName=controllerName)

        import actionlib
        self._controlMsgs = __import__(controllerName, globals(), locals())
        self._goalName = goalName

        self._controlClient = actionlib.SimpleActionClient('/%s' % controllerName, getattr(self._controlMsgs, actionName))
        print "Waiting for %s..." % controllerName
        self._controlClient.wait_for_server()
        print "Connected to %s!" % controllerName

    def runFunction(self, funcName, kwargs):
        return 5

    def initComponent(self, name):
        if name == 'base':
            goal = getattr(self._controlMsgs, self._goalName)(
                                                   action='init',
                                                   component=name)
            client = self._controlClient
            return client.send_goal_and_wait(goal)
        else:
            return 3

    def runComponent(self, name, value, mode=None, blocking=True):
        (namedPosition, joints) = (value, []) if str == type(value) else ('', value)

        goal = getattr(self._controlMsgs, self._goalName)(
                                               action='move',
                                               component=name,
                                               namedPosition=namedPosition,
                                               jointPositions=joints)
        client = self._controlClient

        if(blocking):
            status = client.send_goal_and_wait(goal)
        else:
            client.send_goal(goal)
            status = 1

        return status

if __name__ == "__main__":
    pass
