import re, unittest
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
	RE_NOTE = re.compile(r'^\s*[|0-9]+\s+[|0-9]+\s+[|0-9]+\s+[|0-9]+')


	def __init__(self):
		self.formatters = []
		self.prev_line = None

		self._tuning = tunings.STANDARD_TUNING

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

	def format_note(self, note):
		for formatter in self.formatters:
			formatter.format_note(note)

	def parse_keypair(self, key, value):
		key = key.lower()
		self.format_attribute(key, value)

	def parse_decoration(self, decoration):
		pass

	def parse_barline(self, line):
		self.format_barline(line)

	def parse_note(self, note):
		notes = note.split()

		decorations = notes[len(self._tuning):]
		notes = notes[0:len(self._tuning)]

		def parse_string(open_string, fret):
			try:
				return open_string + int(fret)
			except:
				return None
		notes = [ parse_string(open_string, fret) for (open_string, fret) in zip(self._tuning, notes) ]

		self.format_note(tuple(notes))

	def parse(self, s):
		'''Categorize the line and handle any error reporting.'''
		barline = self.RE_BARLINE.match(s)
		if None != barline:
			# Handle the special case of titles (meaning the barline is a actually
			# an underline
			if (barline.group(2) == '' and self.prev_line != None):
				self.parse_keypair("title", self.prev_line)
				self.prev_line = None
				return

			self.flush()
			self.parse_decoration(barline.group(2))
			self.parse_barline(barline.group(1))
			return

		self.flush()

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

	def flush(self):
		if self.prev_line != None:
			self.format_attribute("error", self.prev_line)
			self.prev_line = None

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

	def expectHistory(self, t):
		self.assertTupleEqual(self.formatter.history[self.history_counter], t)
		self.history_counter += 1

	def expectNote(self, template):
		def parse_note(note):
			try:
				return Note(note)
			except:
				return None
		notes = [parse_note(note) for note in template.split()]
		self.expectHistory(('format_note', tuple(notes)))

	def testComment(self):
		comment = '# This is a comment'
		self.parser.parse(comment)
		self.expectHistory(('format_attribute', 'comment', comment[2:]))

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
		# TODO: Need to check what type barline is (not yet implemented)
		self.formatter.history[0] = self.formatter.history[0][0:1]
		self.expectHistory(('format_barline',))

	def testDoulbeBarLine(self):
		self.parser.parse('========')
		# TODO: Need to check what type barline is (not yet implemented)
		self.formatter.history[0] = self.formatter.history[0][0:1]
		self.expectHistory(('format_barline',))

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
		self.parser.parse('0 | | | | |')
		self.expectNote('E2  X  X  X  X  X')

		self.parser.parse('| 0 | | | |')
		self.expectNote(' X A2  X  X  X  X')

		self.parser.parse('| | 0 | | |')
		self.expectNote(' X  X D3  X  X  X')

		self.parser.parse('| | | 0 | |')
		self.expectNote(' X  X  X G3  X  X')

		self.parser.parse('| | | | 0 |')
		self.expectNote(' X  X  X  X B3  X')

		self.parser.parse('| | | | | 0')
		self.expectNote(' X  X  X  X  X E4')

	def testBigChords(self):
		self.parser.parse(' 3  2  0  0  0  3')
		self.expectNote(  'G2 B2 D3 G3 B3 G4')

		self.parser.parse(' |  3  2  0  1  0')
		self.expectNote(  ' X C3 E3 G3 C4 E4')

		self.parser.parse('12 14 14 13  12 12')
		self.expectNote(  'E3 B3 E4 G#4 B4 E5')

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()