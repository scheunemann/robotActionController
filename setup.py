from setuptools import setup
import platform

requires = [
          'python-dateutil',
          'gevent',
          'pyserial',
          'pyaudio',
          'sqlalchemy',
      ]

if platform.system() == 'Linux':
    requires.append('evdev')
else:
    pass


def readme():
    with open('README.md') as f:
        return f.read()

setup(name='robotActionController',
      version='1.0',
      description='Generic action controller for various robots',
      long_description=readme(),
      classifiers=[
        'Development Status :: 1.0',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
      ],
      url='http://github.com/uh-nmb/robotActionController',
      author='Nathan Burke',
      author_email='n.burke@natbur.com',
      license='MIT',
      packages=['robotActionController'],
      install_requires=requires,
      include_package_data=True,
      zip_safe=False)
