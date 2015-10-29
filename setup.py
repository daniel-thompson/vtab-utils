#!/usr/bin/env python3

import distutils.core
import unittest

class test(distutils.core.Command):
	description = "run the test suite"

	user_options = [
	]

	def initialize_options(self):
		pass

	def finalize_options(self):
		pass

	def run(self):
		suite = unittest.defaultTestLoader.discover('tests')
		runner = unittest.TextTestRunner()
		result = runner.run(suite)
		if not result.wasSuccessful():
			raise distutils.errors.DistutilsError('Test suite failed')

distutils.core.setup(name='vtab-utils',
      version='1.9.0',
      description='A collection of programs to work with vertical tab',
      author='Daniel Thompson',
      url='http://redfelineninja.org.uk/daniel/',
      license='GPLv3+',
      packages=['vtab'],
      scripts=['vtab2ascii', 'vtab2dummy', 'vtab2ly', 'vtab2pdf', 'vtab2svg'],
      cmdclass={'test': test}
     )
