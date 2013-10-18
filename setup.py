#!/usr/bin/env python

from distutils.core import setup

setup(name='vtab-utils',
      version='1.9.0',
      description='A collection of programs to work with vertical tab',
      author='Daniel Thompson',
      url='http://redfelineninja.org.uk/daniel/',
      packages=['vtab'],
      scripts=['vtab2ascii', 'vtab2dummy', 'vtab2ly', 'vtab2pdf'],
     )
