import platform
if platform.system() == 'Linux':
    from linux import KeyEvents
elif platform.system() == 'Windows':
    from windows import KeyEvents
else:
    raise Exception("Sorry: no implementation for your platform ('%s') available" % platform.system())
