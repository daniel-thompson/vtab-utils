import StringIO
import unittest
from fractions import Fraction

import vtab
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
		self.parser = vtab.VtabParser()
		self.formatter = MockFormatter()
		self.parser.add_formatter(self.formatter)

		# This loop adds *all* the formatters to the parser during
		# the parser unit tests. Strictly speaking this is not within
		# the scope of unit tests but it has very little impact on the
		# behaviour of the parser but allows us (for free) to check
		# that the formatters don't react to formatting commands by
		# raising an exception.
		for fmt in (vtab.AsciiFormatter(),
			    vtab.DummyFormatter(),
			    vtab.LilypondFormatter()):
			sio = StringIO.StringIO()
			fmt.set_file(sio)
			self.parser.add_formatter(fmt)

		self.assertEqual(len(self.formatter.history), 0)
		self.history_counter = 0

	def tearDown(self):
		# Check for unexpected history
		self.assertEqual(len(self.formatter.history), self.history_counter)

		# Check that no state is held by the parser at the end of the test
		self.parser.flush()
		self.assertEqual(len(self.formatter.history), self.history_counter)

	def parse(self, s):
		for ln in s.split('\n'):
			self.parser.parse(ln)
		self.parser.flush()

	def expectHistory(self, t):
		self.assertTupleEqual(self.formatter.history[self.history_counter], t)
		self.history_counter += 1

	def expectBarline(self, barline_type='-'):
		expected_barline = None

		if barline_type == '-':
			expected_barline = {}
		elif barline_type == '=':
			expected_barline = { 'double': 'plain' }
		elif barline_type == ':-':
			expected_barline = { 'repeat': 'close' }
		elif barline_type == '-:':
			expected_barline = { 'repeat': 'open' }
		elif barline_type == ':-:':
			expected_barline = { 'repeat': 'both' }
		elif barline_type == ':=':
			expected_barline = { 'double': 'plain', 'repeat': 'close' }
		elif barline_type == '=:':
			expected_barline = { 'double': 'plain', 'repeat': 'open' }
		elif barline_type == ':=:':
			expected_barline = { 'double': 'plain', 'repeat': 'both' }

		assert(None != expected_barline)

		self.expectHistory(('format_barline', expected_barline))

	def expectNote(self, template, duration=Fraction(1,4), tie=False):
		def parse_note(note):
			try:
				return Note(note)
			except:
				return None
		notes = [parse_note(note) for note in template.split()]
		self.expectHistory(('format_note', tuple(notes), duration, tie))

	def testComment(self):
		comment = '# This is a comment'
		self.parse(comment)
		self.expectHistory(('format_attribute', 'comment', comment[2:]))

	def testError(self):
		self.parse("""
		===========
		| | | | | 0
		This is gibber
		| | | | | 0
		""")

		self.expectBarline('=')
		# TODO: The comment appearing before the note is a consequence of the
		#       note length detection. The comment really ought to be delayed until after
		#       the note stops.
		self.expectHistory(('format_attribute', 'error', "Cannot parse '\t\tThis is gibber' at line 4"))
		self.expectNote('X  X  X  X  X  E4')
		self.expectNote('X  X  X  X  X  E4')

	def testUnderlinedTitle(self):
		"""Check that a title line is not prematurely issued to the formatter.

		A title can be demarked by its underlining. Therefore is cannot be
		issued to the formatter until the next line has been parsed.

		Note: This implies that we cannot use the self.parse() helper function.
		"""
		title = 'This is a title'
		self.parser.parse(title)
		self.assertEqual(len(self.formatter.history), 0)

		self.parser.parse('========')
		self.expectHistory(('format_attribute', 'title', title))

	def testKeyPairTitle(self):
		title = 'This is a title'
		self.parse('title: ' + title)
		self.expectHistory(('format_attribute', 'title', title))

	def testKeyPairCaseNormalization(self):
		title = 'This is a title'
		self.parse('Title: ' + title)
		self.expectHistory(('format_attribute', 'title', title))

		self.parser.parse('TITLE: ' + title)
		self.expectHistory(('format_attribute', 'title', title))

	def testKeyPairWithoutWhitespace(self):
		title = 'This is a title'
		self.parse('title:' + title)
		self.expectHistory(('format_attribute', 'title', title))

	def testKeyPairWithExcessiveWhitespace(self):
		title = 'This is a title'
		self.parse('\ttitle  : \t ' + title)
		self.expectHistory(('format_attribute', 'title', title))

	def testSingleBarLine(self):
		self.parse('--------')
		self.expectBarline('-')

	def testDoubleBarLine(self):
		self.parse('========')
		self.expectBarline('=')

	def testDoubleRepeatBarLine(self):
		self.parse("""
		========:
		| | 0 | | | 1
		--------
		| | 0 | | |
		:=======
		""")

		self.expectBarline('=:')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,1)))
		self.expectNote(' X  X D3  X  X  X', Fraction(1,1))
		self.expectBarline('-')
		self.expectNote(' X  X D3  X  X  X', Fraction(1,1))
		self.expectBarline(':=')

	def testNoteBarLineInteraction(self):
		self.parse("""
		===========
		| | 0 | | |  2
		| | 0 | | |
		-----------
		| | 0 | | |
		| | 0 | | |
		===========
		""")

		self.expectBarline('=')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,2)))
		self.expectNote(' X  X D3  X  X  X', Fraction(1,2))
		self.expectNote(' X  X D3  X  X  X', Fraction(1,2))
		self.expectBarline('-')
		self.expectNote(' X  X D3  X  X  X', Fraction(1,2))
		self.expectNote(' X  X D3  X  X  X', Fraction(1,2))
		self.expectBarline('=')

	def testDecoratedBarLine(self):
		self.parse('-------- 8 "Some-"')
		self.expectHistory(('format_attribute', 'duration', Fraction(1, 8)))
		self.expectHistory(('format_attribute', 'lyric', 'Some-'))
		self.expectBarline('-')

	def testRepeatOpen(self):
		self.parse('--------:')
		self.expectBarline('-:')

	def testRepeatClose(self):
		self.parse(':-------')
		self.expectBarline(':-')

	def testRepeatCloseOpen(self):
		self.parse(':------:')
		self.expectBarline(':-:')

	def testOpenStrings(self):
		self.parse('0 | | | | |')
		self.expectNote('E2  X  X  X  X  X')

		self.parse('| 0 | | | |')
		self.expectNote(' X A2  X  X  X  X')

		self.parse('| | 0 | | |')
		self.expectNote(' X  X D3  X  X  X')

		self.parse('| | | 0 | |')
		self.expectNote(' X  X  X G3  X  X')

		self.parse('| | | | 0 |')
		self.expectNote(' X  X  X  X B3  X')

		self.parse('| | | | | 0')
		self.expectNote(' X  X  X  X  X E4')

	def testBigChords(self):
		self.parse(' 3  2  0  0  0  3')
		self.expectNote(  'G2 B2 D3 G3 B3 G4')

		self.parse(' |  3  2  0  1  0')
		self.expectNote(  ' X C3 E3 G3 C4 E4')

		self.parse('12 14 14 13  12 12')
		self.expectNote(  'E3 B3 E4 G#4 B4 E5')

	def testDecoratedNotes(self):
		self.parse('|  | 14 |  |  |  8')
		self.expectHistory(('format_attribute', 'duration', Fraction(1, 8)))
		self.expectNote (' X  X E4 X  X  X', Fraction(1, 8))

	def testNoteDurationMinim(self):
		self.parse("""
		-------------
		 | 3 | | | |  2
		 | 3 | | | |  4
		 | | | | | |
		-------------
		 | 3 | | | |  8
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | 3 | | | |  16
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		-------------
		""")

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
		self.parse("""
		-------------)
		 | 3 | | | |  4
		 | 3 | | | |  8
		 | | | | | |
		 | 3 | | | |  16
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | 3 | | | |  32
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		-------------
		""")

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
		self.parse("""
		-------------
		 | 3 | | | |   8
		 | | | | | |
		 | | | | | |
		 | 3 | | | |  16
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | 3 | | | |   4
		-------------
		""")

		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,8)))
		self.expectNote(' X C3  X  X  X  X', Fraction(3,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,16)))
		self.expectNote(' X C3  X  X  X  X', Fraction(3,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,4)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,4))
		self.expectBarline('-')

	def testNoteDurationQuaver(self):
		self.parse("""
		 | 3 | | | |   8
		 | 3 | | | |  16
		 | | | | | |
		 | 3 | | | |  32
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | 3 | | | |  64
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		 | | | | | |
		""")

		self.expectHistory(('format_attribute', 'duration', Fraction(1,8)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,16)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,32)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,8))
		self.expectHistory(('format_attribute', 'duration', Fraction(1,64)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,8))

	def testNotesAndRests(self):
		self.parse("""
			| | | 2 1 1  16
			| | | : : :
			| | | 2 1 1
			| | | : : :
			| | | | | |
			| | | | | |
			| | | 2 1 1
			| | | | | |
			| | | | | |
			| | | : : :
			| | | | | |
			| | | | | |
			| | | 2 1 1
			| | | | | |
			| | | : : :
			| | | | | |
		""")

		self.expectHistory(('format_attribute', 'duration', Fraction(1,16)))
		self.expectNote(' X  X  X A3 C4 F4', Fraction(1,16))
		self.expectNote(' X  X  X  X  X  X', Fraction(1,16))
		self.expectNote(' X  X  X A3 C4 F4', Fraction(1,16))
		self.expectNote(' X  X  X  X  X  X', Fraction(3,16))
		self.expectNote(' X  X  X A3 C4 F4', Fraction(3,16))
		self.expectNote(' X  X  X  X  X  X', Fraction(3,16))
		self.expectNote(' X  X  X A3 C4 F4', Fraction(2,16))
		self.expectNote(' X  X  X  X  X  X', Fraction(2,16))

	def testNoteCarriedOverBarline(self):
		self.parse("""
		 -----------
		 | 3 | | | |  2
		 | | | 0 1 0
		 -----------
		 | | | | | |
		 | | | 0 1 0
		 -----------
		""")

		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,2)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,2))
		self.expectNote(' X  X  X G3 C4 E4', Fraction(1,2))
		self.expectBarline('-')
		self.expectNote(' X  X  X G3 C4 E4', Fraction(1,2), True)
		self.expectNote(' X  X  X G3 C4 E4', Fraction(1,2))
		self.expectBarline('-')

	def testNoteStoppedAtBarline(self):
		self.parse("""
		 -----------
		 | 3 | | | |  2
		 | | | 0 1 0
		 -----------
		 | | | : : :
		 | | | 0 1 0
		 -----------
		""")

		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'duration', Fraction(1,2)))
		self.expectNote(' X C3  X  X  X  X', Fraction(1,2))
		self.expectNote(' X  X  X G3 C4 E4', Fraction(1,2))
		self.expectBarline('-')
		self.expectNote(' X  X  X  X  X  X', Fraction(1,2), False) # No tie
		self.expectNote(' X  X  X G3 C4 E4', Fraction(1,2))
		self.expectBarline('-')

	def testOverText(self):
		self.parse("""
		 -----------
		 | 3 | | | |  t:C
		 | | | 0 1 0
		 | | 2 | | |
		 | | | 0 1 0
		 -----------
		 3 | | | | |  text:G
		 | | | 0 0 3
		 | | 0 | | |
		 | | | 0 0 3
		 -----------
		 1 | | | | |  text:(F)
		 1 | | | | |  "text:Two words"
		 1 | | | | |  text:"Different quoting"
		 0 | | | | |  text:'Em'
		 -----------
		""")

		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'text', 'C'))
		self.expectNote(' X C3  X  X  X  X')
		self.expectNote(' X  X  X G3 C4 E4')
		self.expectNote(' X  X E3  X  X  X')
		self.expectNote(' X  X  X G3 C4 E4')
		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'text', 'G'))
		self.expectNote('G2  X  X  X  X  X')
		self.expectNote(' X  X  X G3 B3 G4')
		self.expectNote(' X  X D3  X  X  X')
		self.expectNote(' X  X  X G3 B3 G4')
		self.expectBarline('-')
		self.expectHistory(('format_attribute', 'text', '(F)'))
		self.expectNote('F2  X  X  X  X  X')
		self.expectHistory(('format_attribute', 'text', 'Two words'))
		self.expectNote('F2  X  X  X  X  X')
		self.expectHistory(('format_attribute', 'text', 'Different quoting'))
		self.expectNote('F2  X  X  X  X  X')
		self.expectHistory(('format_attribute', 'text', 'Em'))
		self.expectNote('E2  X  X  X  X  X')
		self.expectBarline('-')

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()
