'''
Created on 24 Jun 2013

@author: drt
'''

import unittest
from vtab.note import Note
from vtab.tunings import *

class ChordTest(unittest.TestCase):
	def testChordBigE(self):
		expected = (
			Note('E2'),
			Note('B2'),
			Note('E3'),
			Note('G#3'),
			Note('B3'),
			Note('E4'))
		actual = chord((0,2,2,1,0,0))
		self.assertTupleEqual(expected, actual)

	def testChordD(self):
		expected = (
			None,
			None,
			Note('D3'),
			Note('A3'),
			Note('D4'),
			Note('F#4'))
		actual = chord((None,None,0,2,3,2))
		self.assertTupleEqual(expected, actual)

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()