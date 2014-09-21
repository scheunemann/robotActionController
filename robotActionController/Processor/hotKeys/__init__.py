import platform
if platform.system() == 'Windows':
    from windows import KeyEvents
elif platform.system() == 'Linux':
    from linux import KeyEvents
else:
    raise Exception("Sorry: no implementation for your platform ('%s') available" % platform.system())
