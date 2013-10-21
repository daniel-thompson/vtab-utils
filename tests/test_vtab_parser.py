import unittest
from fractions import Fraction
from vtab.vtab_parser import VtabParser
from vtab.note import Note

class MockFormatter(object):
	def __init__(self):
		self.history = []

	def __getattr__(self, name):
		def mock(*args, **kwargs):
			if 0 == len(kwargs):
				self.history.append((name,) + args)
			else:
				self.history.append((name,) + args + (kwargs,))
		return mock

class VtabParserTest(unittest.TestCase):
	def setUp(self):
		self.parser = VtabParser()
		self.formatter = MockFormatter()
		self.parser.add_formatter(self.formatter)
		self.assertEqual(len(self.formatter.history), 0)
		self.history_counter = 0

	def tearDown(self):
		# Check for unexpected history
		self.assertEqual(len(self.formatter.history), self.history_counter)

		# Check that no state is held by the parser at the end of the test
		self.parser.flush()
		self.assertEqual(len(self.formatter.history), self.history_counter)

	def atomicParse(self, s):
		self.parser.parse(s)
		self.parser.flush()

	def expectHistory(self, t):
		self.assertTupleEqual(self.formatter.history[self.history_counter], t)
		self.history_counter += 1

	def expectBarline(self, barline_type='-'):
		# TODO: Eventually the parser/formatter interface will be changed and this
		#       insanity will stop.
		historic_barline = self.formatter.history[self.history_counter]
		expected_barline = barline_type * len(historic_barline[1])

		self.expectHistory(('format_barline', expected_barline))

	def expectNote(self, template, duration=Fraction(1,4)):
		def parse_note(note):
			try:
				return Note(note)
			except:
				return None
		notes = [parse_note(note) for note in template.split()]
		self.expectHistory(('format_note', tuple(notes), duration))

	def testComment(self):
		comment = '# This is a comment'
		self.parser.parse(comment)
		self.expectHistory(('format_attribute', 'comment', comment[2:]))

	def testError(self):
		self.parser.parse("===========")
		self.parser.parse("| | | | | 0")
		self.parser.parse("This is gibber")
		self.parser.parse("| | | | | 0")
		self.parser.flush()

		self.expectHistory(('format_barline', '==========='))
		# TODO: The comment appearing before the note is a consequence of the
		#       note length detection. The comment really ought to be delayed until after
		#       the note stops.
		self.expectHistory(('format_attribute', 'error', "Cannot parse 'This is gibber' at line 3"))
		self.expectNote('X  X  X  X  X  E4')
		self.expectNote('X  X  X  X  X  E4')

	def testUnderlinedTitle(self):
		title = 'This is a title'
		self.parser.parse(title)
		self.assertEqual(len(self.formatter.history), 0)

		self.parser.parse('========')
		self.expectHistory(('format_attribute', 'title', title))

	def testKeyPairTitle(self):
		title = 'This is a title'
		self.parser.parse('title: ' + title)
		self.expectHistory(('format_attribute', 'title', title))

	def testKeyPairCaseNormalization(self):
		title = 'This is a title'
		self.parser.parse('Title: ' + title)
		self.expectHistory(('format_attribute', 'title', title))

		self.parser.parse('TITLE: ' + title)
		self.expectHistory(('format_attribute', 'title', title))

	def testKeyPairWithoutWhitespace(self):
		title = 'This is a title'
		self.parser.parse('title:' + title)
		self.expectHistory(('format_attribute', 'title', title))

	def testKeyPairWithExcessiveWhitespace(self):
		title = 'This is a title'
		self.parser.parse('\ttitle  : \t ' + title)
		self.expectHistory(('format_attribute', 'title', title))

	def testSingleBarLine(self):
		self.parser.parse('--------')
		self.expectBarline('-')

	def testDoulbeBarLine(self):
		self.parser.parse('========')
		self.expectBarline('=')

	def testNoteBarLineInteraction(self):
		self.parser.parse('========')
		self.parser.parse('| | 0 | | | 2')
		self.parser.parse('| | 0 | | |')
		self.parser.parse('--------')
		self.parser.parse('| | 0 | | |')
		self.parser.parse('| | 0 | | |')
		self.parser.parse('========')
		self.parser.flush()

		self.expectBarline('=')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,2)))
		self.expectNote(' X  X D3  X  X  X', Fraction(1,2))
		self.expectNote(' X  X D3  X  X  X', Fraction(1,2))
		self.expectBarline('-')
		self.expectNote(' X  X D3  X  X  X', Fraction(1,2))
		self.expectNote(' X  X D3  X  X  X', Fraction(1,2))
		self.expectBarline('=')

	def testDecoratedBarLine(self):
		self.parser.parse('-------- 8 "Some-"')
		self.expectHistory(('format_attribute', 'duration', Fraction(1, 8)))
		self.expectHistory(('format_attribute', 'lyric', 'Some-'))
		self.expectBarline('-')

	def testRepeatOpen(self):
		self.parser.parse('=======:')
		# TODO: Need to check what type barline is (not yet implemented)
		self.formatter.history[0] = self.formatter.history[0][0:1]
		self.expectHistory(('format_barline',))

	def testRepeatClose(self):
		self.parser.parse(':=======')
		# TODO: Need to check what type barline is (not yet implemented)
		self.formatter.history[0] = self.formatter.history[0][0:1]
		self.expectHistory(('format_barline',))

	def testRepeatCloseOpen(self):
		self.parser.parse(':======:')
		# TODO: Need to check what type barline is (not yet implemented)
		self.formatter.history[0] = self.formatter.history[0][0:1]
		self.expectHistory(('format_barline',))

	def testOpenStrings(self):
		self.atomicParse('0 | | | | |')
		self.expectNote('E2  X  X  X  X  X')

		self.atomicParse('| 0 | | | |')
		self.expectNote(' X A2  X  X  X  X')

		self.atomicParse('| | 0 | | |')
		self.expectNote(' X  X D3  X  X  X')

		self.atomicParse('| | | 0 | |')
		self.expectNote(' X  X  X G3  X  X')

		self.atomicParse('| | | | 0 |')
		self.expectNote(' X  X  X  X B3  X')

		self.atomicParse('| | | | | 0')
		self.expectNote(' X  X  X  X  X E4')

	def testBigChords(self):
		self.atomicParse(' 3  2  0  0  0  3')
		self.expectNote(  'G2 B2 D3 G3 B3 G4')

		self.atomicParse(' |  3  2  0  1  0')
		self.expectNote(  ' X C3 E3 G3 C4 E4')

		self.atomicParse('12 14 14 13  12 12')
		self.expectNote(  'E3 B3 E4 G#4 B4 E5')

	def testDecoratedNotes(self):
		self.atomicParse('|  | 14 |  |  |  8')
		self.expectHistory(('format_attribute', 'duration', Fraction(1, 8)))
		self.expectNote (' X  X E4 X  X  X', Fraction(1, 8))

	def testNoteDurationMinim(self):
		self.parser.parse('-------------')
		self.parser.parse(' | 3 | | | |  2')
		self.parser.parse(' | 3 | | | |  4')
		self.parser.parse(' | | | | | |')

		self.parser.parse('-------------')
		self.parser.parse(' | 3 | | | |  8')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | 3 | | | |  16')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')

		self.parser.parse('-------------')
		self.parser.flush()

		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,2)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,2))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,4)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,2))

		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,8)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,2))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,16)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,2))

		self.expectBarline('-')

	def testNoteDurationCrotchet(self):
		self.parser.parse('-------------')
		self.parser.parse(' | 3 | | | |  4')
		self.parser.parse(' | 3 | | | |  8')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | 3 | | | |  16')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | 3 | | | |  32')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse('-------------')
		self.parser.flush()

		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,4)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,4))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,8)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,4))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,16)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,4))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,32)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,4))
		self.expectBarline('-')

	def testNoteDurationDottedCrotchet(self):
		self.parser.parse('-------------')
		self.parser.parse(' | 3 | | | |  8')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | 3 | | | |  16')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | 3 | | | |  4')
		self.parser.parse('-------------')
		self.parser.flush()

		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,8)))
		self.expectNote(' X C3  X  X  X  X', Fraction(3,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,16)))
		self.expectNote(' X C3  X  X  X  X', Fraction(3,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,4)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,4))
		self.expectBarline('-')

	def testNoteDurationQuaver(self):
		self.parser.parse(' | 3 | | | |  8')
		self.parser.parse(' | 3 | | | |  16')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | 3 | | | |  32')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | 3 | | | |  64')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.parse(' | | | | | |')
		self.parser.flush()

		self.expectHistory(('format_attribute', 'duration', Fraction(1,8)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,16)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,32)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,64)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,8))


if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()
