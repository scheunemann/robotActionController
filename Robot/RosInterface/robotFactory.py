import sys


class Factory(object):

    @staticmethod
    def getRobotInterface(robot):
        print "Building class for robot named: %s" % robot.name
        robotInt = None
        try:
            robotClass = __import__(robot.model.extraData['className'], globals(), locals())
            robotInt = robotClass(robot.name, **robot.model.extraData['classArgs'])
        except:
            print >> sys.stderr, "Unknown robot type %s" % robot.model.name
            return None

        print "Finished building class %s" % robotInt.__class__.__name__
        return robotInt
