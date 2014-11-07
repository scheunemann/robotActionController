from setuptools import setup
import platform

requires = [
          'python-dateutil',
          'gevent',
          'pyserial',
          'pyaudio>=0.2.8',
          'sqlalchemy==0.9.8',
      ]

depend_links = [
          'git+http://people.csail.mit.edu/hubert/git/pyaudio.git#egg=pyaudio-0.2.8',
]

if platform.system() == 'Linux':
    requires.append('evdev')
elif platform.system() == 'Windows':
    requires.append('pyHook')
    requires.append('pywin32')


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
      dependency_links=depend_links,
      include_package_data=True,
      zip_safe=False)
