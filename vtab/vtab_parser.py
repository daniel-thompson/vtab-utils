import shlex
import re
import unittest
from fractions import Fraction
from vtab import tunings
from note import Note

class VtabParser(object):
	'''Match a barline (or underline), yielding barline and decoration
	Template is: "============ <decoration>"'''
	RE_BARLINE = re.compile(r'^\s*(:*[-=]{4}[-=]*:*)\s*(.*)$')

	'''Match a # character, yielding the associated comment
	Template is: "# This is a comment"'''
	RE_COMMENT = re.compile(r'^\s*#+\s*(.*)$')

	'''Match a key-value pair, yielding key and value
	Template is: "Key : Value"'''
	RE_KEYPAIR = re.compile(r'^\s*(\w+)\s*:\s*(.*)$')

	'''Match a tab line. This does not yield anything, it is only
	a recogniser (based on all tabs being for instruments with at
	least four strings).
	Template is: " | 10  |  9"'''
	RE_NOTE = re.compile(r'^\s*[|:0-9]+\s+[|:0-9]+\s+[|:0-9]+\s+[|:0-9]+')

	def __init__(self):
		self.formatters = []
		self.prev_line = None

		self._tuning = tunings.STANDARD_TUNING
		self._lineno = 0
		self._duration = Fraction(1, 4)
		self._note_len = Fraction(0, 1)

	def add_formatter(self, formatter):
		if not formatter in self.formatters:
			self.formatters += formatter,

	def remove_formatter(self, formatter):
		self.formatters.remove(formatter)

	def format_attribute(self, key, value):
		for formatter in self.formatters:
			formatter.format_attribute(key, value)

	def format_barline(self, line):
		for formatter in self.formatters:
			formatter.format_barline(line)

	def format_note(self, note, duration):
		for formatter in self.formatters:
			formatter.format_note(note, duration)

	def parse_keypair(self, key, value):
		key = key.lower()
		self.format_attribute(key, value)

	def parse_decorations(self, decorations):
		for token in decorations:
			if token[0].isdigit():
				self._duration = Fraction(1, int(token))
				self.format_attribute('duration', self._duration)
			else:
				self.format_attribute('lyric', token)

	def parse_barline(self, line):
		self._flush_current_note()
		tokens = shlex.split(line)
		self.parse_decorations(tokens[1:])
		self.format_barline(tokens[0])

	def parse_note(self, note):
		notes = shlex.split(note)
		decorations = notes[len(self._tuning):]

		def parse_string(open_string, fret):
			try:
				return open_string + int(fret)
			except:
				return None

		is_rest = ':' in notes

		notes = notes[0:len(self._tuning)]
		notes = [ parse_string(open_string, fret) for (open_string, fret) in zip(self._tuning, notes) ]

		if len(notes) != notes.count(None) or is_rest:
			# New note starts
			self._flush_current_note()
			self.parse_decorations(decorations)
			self._notes = tuple(notes)
			self._note_len = self._duration
		else:
			# Note continues
			self.parse_decorations(decorations)
			self._note_len += self._duration

	def parse(self, s):
		'''Categorize the line and handle any error reporting.'''
		self._lineno += 1
		barline = self.RE_BARLINE.match(s)
		if None != barline:
			# Handle the special case of titles (meaning the barline is a actually
			# an underline
			if (barline.group(2) == '' and self.prev_line != None):
				self.parse_keypair("title", self.prev_line)
				self.prev_line = None
				return

			self._flush_prev_line()
			self.parse_barline(s)
			return

		self._flush_prev_line()

		comment = self.RE_COMMENT.match(s)
		if None != comment:
			self.format_attribute('comment', comment.group(1))
			return

		keypair = self.RE_KEYPAIR.match(s)
		if None != keypair:
			self.parse_keypair(keypair.group(1), keypair.group(2))
			return

		note = self.RE_NOTE.match(s)
		if None != note:
			self.parse_note(s)
			return

		if s.strip() != '': # not whitespace
			self.prev_line = s

	def _flush_current_note(self):
		if 0 != self._note_len:
			self.format_note(self._notes, self._note_len)
			self._note_len = Fraction(0, 1)
			self._notes = None

	def _flush_prev_line(self):
		if self.prev_line != None:
			self.format_attribute("error", "Cannot parse '%s' at line %d" %
					(self.prev_line, self._lineno-1))
			self.prev_line = None

	def flush(self):
		self._flush_current_note()
		self._flush_prev_line()

	def parse_file(self, f):
		for ln in f.readlines():
			self.parse(ln.rstrip())
		self.flush()
		for formatter in self.formatters:
			formatter.flush()


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
