from robot import ROSRobot, ActionLib as RosActionLib


class Sunflower(ROSRobot):
    _imageFormats = ['BMP', 'EPS', 'GIF', 'IM', 'JPEG', 'PCD', 'PCX', 'PDF', 'PNG', 'PPM', 'TIFF', 'XBM', 'XPM']

    def __init__(self, name, rosMaster='http://sf1-1-pc1:11311'):
        from rosHelper import ROS
        ROS.configureROS(rosMaster=rosMaster)
        super(Sunflower, self).__init__(name, ActionLib, 'sf_controller')

    def getComponentState(self, componentName, resolve_name=False):
        topic = '/%(name)s_controller/state' % {'name': componentName}
        state = self._ros.getSingleMessage(topic)

        try:
            ret = {'name': componentName, 'positions': [state.current_pos, ], 'goals': [state.goal_pos, ], 'joints': [state.name, ]}
        except Exception as e:
            self._logger.critical("Error retrieving joint state: %s" % e)
            ret = {'name': componentName, 'positions': (), 'goals': (), 'joints': ()}

        if resolve_name:
            return self.resolveComponentState(componentName, ret)
        else:
            return ('', ret)

    def setComponentState(self, name, value):
        # check if the component has been initialised, and init if it hasn't
        if name == 'base' or name == 'base_direct':
            self._robInt.initComponent(name)

        return super(Sunflower, self).setComponentState(name, value)


class ActionLib(RosActionLib):

    def __init__(self):
        super(ActionLib, self).__init__('sf_controller', 'SunflowerAction', 'SunflowerGoal')
