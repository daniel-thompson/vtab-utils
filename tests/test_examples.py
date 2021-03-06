"""Run each of the formatters over all the examples.

This test is based upon wildcards and will automatically process
all the examples.

The output is not checked for correctness but we do check that no
runtime errors occur (e.g. no exceptions are raised). Also if the
formatter output is the input for another tool then we run the
output through that tool and check the return code.

"""
import glob
import io
import subprocess
import unittest

import vtab

class ParametrizedTestCase(unittest.TestCase):
	""" TestCase classes that want to be parametrized should
	inherit from this class.

	ParametrizedTestCase comes from Eli Benderski's blog:
	http://eli.thegreenplace.net/2011/08/02/python-unit-testing-parametrized-test-cases/
	"""
	def __init__(self, methodName='runTest', param=None):
		super(ParametrizedTestCase, self).__init__(methodName)
		self.param = param

	@staticmethod
	def parametrize(testcase_klass, param=None):
		""" Create a suite containing all tests taken from the given
		    subclass, passing them the parameter 'param'.
		"""
		testloader = unittest.TestLoader()
		testnames = testloader.getTestCaseNames(testcase_klass)
		suite = unittest.TestSuite()
		for name in testnames:
			suite.addTest(testcase_klass(name, param=param))
		return suite

class ExampleTestCase(ParametrizedTestCase):
	def doParse(self, fmt):
		sio = io.StringIO()
		fmt.set_file(sio)
		p = vtab.VtabParser()
		p.add_formatter(fmt)
		f = open(self.param)
		num_errors = p.parse_file(f)
		f.close()
		self.assertEqual(0, num_errors, "%s did not parse cleanly" % self.param)
		return sio

	def testAsciiFormatter(self):
		unused_io = self.doParse(vtab.AsciiFormatter())

	def testDummyFormatter(self):
		unused_io = self.doParse(vtab.DummyFormatter())

	def testLyFormatter(self):
		msg = ('Lilypond %s whilst processing ' + self.param +
		       ' (try running vtab2pdf on this file)')

		lyio = self.doParse(vtab.LilypondFormatter())
		lysub = subprocess.Popen(('lilypond', '-'),
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE)
		(out, err) = lysub.communicate(lyio.getvalue().encode('UTF-8'))
		self.assertEqual(0, lysub.returncode)
		out = out.decode('UTF-8')
		err = err.decode('UTF-8')
		for s in ('error', 'warning'):
			self.assertNotIn(s, out+err, msg % s)

def load_tests(loader, tests, pattern):
	suite = unittest.TestSuite()
	pmtz = ParametrizedTestCase.parametrize
	for fname in glob.glob('*/*.vtab'):
		suite.addTest(pmtz(ExampleTestCase, param=fname))

	return suite
