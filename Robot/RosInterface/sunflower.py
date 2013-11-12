from robot import ROSRobot, ActionLib as RosActionLib


class Sunflower(ROSRobot):
    _imageFormats = ['BMP', 'EPS', 'GIF', 'IM', 'JPEG', 'PCD', 'PCX', 'PDF', 'PNG', 'PPM', 'TIFF', 'XBM', 'XPM']

    def __init__(self, name, rosMaster):
        from rosHelper import ROS
        ROS.configureROS(rosMaster='http://sf1-1-pc1:11311')
        super(Sunflower, self).__init__(name, ActionLib, 'sf_controller')

    def setComponentState(self, name, value):
        # check if the component has been initialised, and init if it hasn't
        if name == 'base' or 'base_direct':
            self._robInt.initComponent(name)

        return super(Sunflower, self).setComponentState(name, value)


class ActionLib(RosActionLib):

    def __init__(self):
        super(ActionLib, self).__init__('sf_controller', 'SunflowerAction', 'SunflowerGoal')
