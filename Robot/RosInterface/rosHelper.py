import time
import os
import sys
from subprocess import Popen, PIPE

ros_config = {}

from threading import RLock

_threadLock = RLock()


class ROS(object):
    _activeVersion = None
    _envVars = {}
    _userVars = None

    def __init__(self, *args, **kwargs):
        ROS.configureROS(packageName='rospy')
        import rospy
        self._rospy = rospy
        self._topicTypes = {}
        self._subscribers = {}
        self.initROS()

    def __del__(self):
        for sub in self._subscribers.values():
            sub.unregister()

    def initROS(self, name='rosHelper'):
        with _threadLock:
            if not self._rospy.core.is_initialized():
                self._rospy.init_node('rosHelper', anonymous=True, disable_signals=True)

    def getSingleMessage(self, topic, dataType=None, retryOnFailure=1, timeout=None):
        try:
            if dataType == None:
                if topic not in self._topicTypes:
                    self._topicTypes[topic] = self.getMessageType(topic)

                dataType = self._topicTypes[topic]

            if topic not in self._subscribers:
                self._subscribers[topic] = RosSubscriber(topic, dataType)

            subscriber = self._subscribers[topic]
            while not subscriber.hasNewMessage:
                if timeout != None:
                    if timeout < 0:
                        break
                    else:
                        timeout -= 0.01
                time.sleep(0.01)

            return subscriber.lastMessage
        except:
            if retryOnFailure > 0:
                return self.getSingleMessage(topic, dataType, retryOnFailure - 1, timeout)
            else:
                return None

    def getParam(self, paramName):
        try:
            ROS.configureROS(packageName='rospy')
            import rospy
            return rospy.get_param(paramName)
        except Exception as e:
            print >> sys.stderr, "Unable to connect to ros parameter server, Error: %s" % e
            return []

    def getTopics(self, baseFilter='', exactMatch=False, retry=10):
        # topics = self._rospy.get_published_topics(baseFilter)
        # if len(topics) == 0 and baseFilter.strip('/').find('/') == -1:

        # decided to do filtering a little different than ros
        # ros requires an exact match (of the parent namespace)
        # this can grab any partial matches

        # ros doesn't return topics when the full namespace is specified
        # i.e. head_controller works and brings back all nested topics
        # but head_controller/state does not
        # in this case, get all of them and loop through
        topics = []
        with _threadLock:
            try:
                allTopics = self._rospy.get_published_topics()
            except Exception as e:
                print "Error while retrieving topics, will retry %s more times. Error: %s" % (retry, e)
                if(retry > 0):
                    return self.getTopics(baseFilter, exactMatch, retry - 1)
                else:
                    return topics

        if baseFilter.startswith('/'):
            baseFilter = baseFilter[1:]
        for t in allTopics:
            name = t[0]
            if name.startswith('/'):
                name = name[1:]
            if name.strip('/') == baseFilter.strip('/') or (not exactMatch and name.startswith(baseFilter)):
                topics.append(t)

        return topics

    def getMessageType(self, topic):
        pubTopic = self.getTopics(topic, True)
        if len(pubTopic) != 0:
            controller_msgType = pubTopic[0][1]
        else:
            raise Exception('Could not determine ROS messageType for topic: %s' % (topic))

        (manifest, cls) = controller_msgType.split('/')

        try:
            import roslib
            roslib.load_manifest(manifest)

            ns = __import__(manifest + '.msg', globals(), locals(), [cls], -1)
            msgCls = getattr(ns, cls)
            return msgCls
        except Exception as e:
            raise Exception('Error occured while loading message class: %s' % (e))

    @staticmethod
    def _getUserVars():
        if ROS._userVars == None:
            # This is a bit more dangerous as it loads the users .bashrc file in a forced interactive shell
            # while not actually being in an interactive shell.  any prompts could cause lockups
            command = ['bash', '-i', '-c', ('%s; env' % ". %s/.bashrc" % os.getenv("HOME")).strip('; ')]
            pipe = Popen(command, stdout=PIPE, stderr=PIPE)
            (data, _) = pipe.communicate()
            env = dict((line.split("=", 1) for line in data.splitlines()))
            ROS._userVars = env

        return ROS._userVars

    @staticmethod
    def _locateRosOverlayPath():
        env = ROS._getUserVars()

        if 'ROS_PACKAGE_PATH' not in env:
            return env['ROS_PACKAGE_PATH']

        return None

    @staticmethod
    def _locateRosVersion():
        if ROS._activeVersion == None:
            env = ROS._getUserVars()
            if 'ROS_DISTRO' not in env:
                ROS._activeVersion = env['ROS_DISTRO']
            else:
                bash = open("%s/.bashrc" % os.getenv("HOME"), "r")
                bashlines = bash.readlines()
                # assume the source line is closest to the end
                for n in range(len(bashlines) - 1, 0, -1):
                    # strip lines of white spaces, look for source /opt/ros/.../setup.bash command,
                    # distribution name is between ros/ and next /
                    if bashlines[n].strip().find("source /opt/ros/") == 0:
                        line = bashlines[n].strip()
                        version = line[16:line.find("/", 16)]
                        print "Active ROS version found: ", version
                        ROS._activeVersion = version
                        break

        return ROS._activeVersion

    @staticmethod
    def _parseRosVersionSetupBash(version, onlyDifferent=True):
        if version not in ROS._envVars:
            # executes the bash script and exports env vars
            bashScript = '/opt/ros/%s/setup.bash' % version
            diffEnv = {}
            if os.path.exists(bashScript):
                rosEnv = ROS._parseBashEnviron('source ' + bashScript)
                baseEnv = ROS._parseBashEnviron()

                # find all the variables that ros added/changed
                for key, value in rosEnv.items():
                    if key not in baseEnv:
                        diffEnv[key] = value
                    elif baseEnv[key] != value:
                        # We really only want the bit that ros added
                        diffEnv[key] = value.replace(baseEnv[key], '').strip(':')

                # Add in any overrides from the config file
                if 'envVars' not in ros_config:
                    diffEnv.update(ros_config['envVars'])
                    rosEnv.update(ros_config['envVars'])
            else:
                print >> sys.stderr, "Unable to read ros bash script, file not found: %s" % bashScript

            ROS._envVars[version] = (diffEnv, rosEnv)

        if onlyDifferent:
            return ROS._envVars[version][0]
        else:
            return ROS._envVars[version][1]

    @staticmethod
    def _parseBashEnviron(preCommand=''):
        command = ['bash', '-c', ('%s; env' % preCommand).strip('; ')]
        pipe = Popen(command, stdout=PIPE)
        data = pipe.communicate()[0]
        env = dict((line.split("=", 1) for line in data.splitlines()))
        return env

    @staticmethod
    def configureROS(version=None, packagePath=None, packageName=None, rosMaster=None, overlayPath=None):
        """Any values not provided will be read from ros_config in config.py"""
        if version == None:
            if 'version' not in ros_config:
                version = ROS._locateRosVersion()
            else:
                version = ros_config['version']

        if overlayPath == None:
            if 'overlayPath' not in ros_config:
                overlayPath = ROS._locateRosOverlayPath()
            else:
                overlayPath = ros_config['overlayPath']

        if(rosMaster == None and 'rosMaster' in ros_config):
            rosMaster = ros_config['rosMaster']

        for k, v in ROS._parseRosVersionSetupBash(version).items():
            if k == 'PYTHONPATH' and sys.path.count(v) == 0:
                sys.path.append(v)
            elif k not in os.environ:
                os.environ[k] = v
            elif k.endswith('PATH') and os.environ[k].find(v) == -1:
                os.environ[k] = ':'.join((v, os.environ[k]))

        # if 'ROS_MASTER_URI' not in os.environ.keys():
        if rosMaster != None:
            os.environ['ROS_MASTER_URI'] = rosMaster

        path = '/opt/ros/%(version)s/ros' % {'version': version}
        if 'ROS_ROOT' not in os.environ.keys() or os.environ['ROS_ROOT'] != path:
            os.environ['ROS_ROOT'] = path

        path = '%(root)s/bin' % {'root': os.environ['ROS_ROOT']}
        if os.environ['PATH'].find(path) == -1:
            os.environ['PATH'] = ':'.join((path, os.environ['PATH']))

        path = '/opt/ros/%(version)s/stacks' % {'version': version}
        if 'ROS_PACKAGE_PATH' not in os.environ.keys():
            os.environ['ROS_PACKAGE_PATH'] = path
        elif os.environ['ROS_PACKAGE_PATH'].find(path) == -1:
            os.environ['ROS_PACKAGE_PATH'] = ':'.join((path, os.environ['ROS_PACKAGE_PATH']))

        if overlayPath != None:
            for path in overlayPath.split(':'):
                path = os.path.expanduser(path)
                if os.environ['ROS_PACKAGE_PATH'].find(path) == -1:
                    os.environ['ROS_PACKAGE_PATH'] = ':'.join((path, os.environ['ROS_PACKAGE_PATH']))

        path = packagePath or os.path.dirname(os.path.realpath(__file__)) + '/ROS_Packages'
        if os.environ['ROS_PACKAGE_PATH'].find(path) == -1:
            os.environ['ROS_PACKAGE_PATH'] = ':'.join((path, os.environ['ROS_PACKAGE_PATH']))

        path = '%(root)s/core/roslib/src' % {'root': os.environ['ROS_ROOT']}
        if sys.path.count(path) == 0:
            sys.path.append(path)

        if packageName != None:
            import roslib
            roslib.load_manifest(packageName)


class RosSubscriber(object):

    def __init__(self, topic, dataType, idleTime=15):
        ROS.configureROS(packageName='rospy')
        import rospy
        self._rospy = rospy
        self._lastAccess = time.time()
        self._subscriber = None
        self._topic = topic
        self._dataType = dataType
        self._newMessage = False
        self._idleTimeout = idleTime

    @property
    def hasNewMessage(self):
        self._touch()
        return self._newMessage

    @property
    def lastMessage(self):
        self._touch()
        self._newMessage = False
        return self._data

    def _touch(self):
        self._lastAccess = time.time()
        if self._subscriber == None:
            with _threadLock:
                self._subscriber = self._rospy.Subscriber(self._topic, self._dataType, self._callback)

    def unregister(self):
        if self._subscriber != None:
            self._subscriber.unregister()
            self._subscriber = None

    def _callback(self, msg):
        self._data = msg
        self._newMessage = True
        if time.time() - self._lastAccess > self._idleTimeout:
            self.unregister()


class Transform(object):
    def __init__(self, rosHelper=None, fromTopic=None, toTopic=None):
        if(rosHelper == None):
            self._ros = ROS()
        else:
            self._ros = rosHelper
        self._ros.configureROS(packageName='core_transform')
        import tf, rospy
        self._rospy = rospy
        self._tf = tf
        self._ros.initROS()
        self._listener = None
        self._defaultFrom = fromTopic
        self._defaultTo = toTopic

    def getTransform(self, fromTopic=None, toTopic=None):
        if fromTopic == None:
            fromTopic = self._defaultFrom
        if toTopic == None:
            toTopic = self._defaultTo

        """
        Waits for the /fromTopic to /toTopic transform to be availalble and
        returns two tuples: (x, y, z) and a quaternion ( rx, ry, rz, rxy)
        Note: z values are 0 for 2D mapping and navigation.
        """
        if len(self._ros.getTopics('base_pose', exactMatch=True)) == 0:
            # this should work for all navigation systems, but at a performance cost
            if self._listener == None:
                self._listener = self._tf.TransformListener()

            # Wait for tf to get the frames
            with _threadLock:
                now = self._rospy.Time(0)
                try:
                    self._listener.waitForTransform(toTopic, fromTopic, now, self._rospy.Duration(1.0))
                except self._tf.Exception as e:
                    # if str(e) != 'Unable to lookup transform, cache is empty, when looking up transform from frame [' + baseTopic + '] to frame [' + mapTopic + ']':
                    print >> sys.stderr, "Error while waiting for transform: " + str(e)
                    return ((None, None, None), None)

            try:
                (xyPos, heading) = self._listener.lookupTransform(toTopic, fromTopic, now)
                (_, _, orientation) = self._tf.transformations.euler_from_quaternion(heading)
                return (xyPos, orientation)
            except (self._tf.LookupException, self._tf.ConnectivityException, self._tf.ExtrapolationException) as e:
                print >> sys.stderr, "Error while looking up transform: " + str(e)
                return ((None, None, None), None)
        else:
            # this takes significantly less processing time, but requires ipa_navigation
            poseMsg = self._ros.getSingleMessage('/base_pose')
            if poseMsg == None:
                print >> sys.stderr, "No message recieved from /base_pose"
                return ((None, None, None), None)
            pose = poseMsg.pose
            xyPos = (pose.position.x, pose.position.y, pose.position.z)
            (_, _, orientation) = self._tf.transformations.euler_from_quaternion((pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w))
            return (xyPos, orientation)

if __name__ == '__main__':
    pass
