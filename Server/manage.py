#!/usr/bin/env python
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app, db
from Common.models import User, Role, Post, Task
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand
from Common.scheduler import *
import threading


app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Post=Post)

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


scheduler = threading.Thread(target=algorithm_one, args=(app,))
scheduler.start()

if __name__ == '__main__':
    manager.run()
