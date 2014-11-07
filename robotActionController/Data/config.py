import os

modelBase = object

database_config = {
                   'engine': {
                              'type': 'Sqlite',
                              'file': ':memory:',
                              },
                   'debug': False,
                   'autocommit': False,
                   'dataFolder': os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Files')),
                   }
