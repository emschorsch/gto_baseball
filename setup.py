#!/usr/bin/env python
from setuptools import find_packages, setup


setup(name="baseball",
      version="0.1",
      description="The optimizer modules for gto",
      author="Emanuel Schorsch",
      author_email='emanuel@gtoanalyticsllc.com',
      platforms=["any"],  # or more specific, e.g. "win32", "cygwin", "osx"
      url="http://github.com/emschorsch/baseball",
      packages=find_packages(),
      )
