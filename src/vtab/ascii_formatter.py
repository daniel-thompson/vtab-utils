import re, unittest, sys
from vtab import tunings
from note import Note

class AsciiFormatter(object):
	def __init__(self):
		self.f = sys.stdout
		self._staff_lines = ()
		self._comments = []

		self.set_tuning(tunings.STANDARD_TUNING)

	def set_file(self, f):
		self.f = f

	def set_tuning(self, tuning):
		self.flush()
		self._tuning = tuning

		staff_lines = []
		for s in self._tuning:
			staff_lines.append([])
		self._staff_lines = tuple(staff_lines)

	def format_attribute(self, key, value):
		try:
			fn = getattr(self, 'format_' + key)
		except:
			fn = None
		if None != fn:
			fn(value)
		else:
			self.flush()
			self.f.write("ERROR: Unsupported attribute (%s: '%s')\n" % (key, value))

	def format_comment(self, comment):
		comment = '# %s\n' % (comment)
		if len(self._staff_lines[0]) == 0:
			self.f.write(comment)
		else:
			self._comments.append(comment)

	def format_key(self, unused):
		# For tab only output the key is not important
		pass

	def format_time(self, unused):
		# For tab only output the timing is not important
		pass

	def format_title(self, title):
		self.f.write(title + '\n')
		self.f.write(('=' * len(title)) + '\n')
		self.f.write('\n')

	def format_barline(self, unused):
		for s in self._staff_lines:
			if len(s) == 0:
				s.append('|')
			else:
				s.append('-|')

	def format_note(self, notes):
		frets = []
		for note, tuning in zip(notes, self._tuning):
			if note == None:
				frets.append('')
			else:
				fret = int(note - tuning)
				frets.append(str(fret))
		width = max([ len(fret) for fret in frets ]) + 1
		for line, fret in zip(self._staff_lines, frets):
			padding = width - len(fret)
			line.append(('-' * padding) + fret)

	def flush(self):
		for s in reversed(self._staff_lines):
			if len(s) > 0:
				self.f.write(''.join(s) + '\n')
				del s[:]
		for c in self._comments:
			self.f.write(c)
		del self._comments[:]

class MockWriter(object):
	def __init__(self):
		self.history = []
		self.log = False
	def write(self, s):
		if self.log:
			sys.stdout.write('output >>> ' + s)
		self.history.append(('write', s.rstrip()))

	def flush(self, s):
		# We avoid adding flush calls to the history (the implementation can
		# call this at all sorts of th different times).
		pass

	def __getattr__(self, name):
		def mock(*args, **kwargs):
			if 0 == len(kwargs):
				self.history.append((name,) + args)
			else:
				self.history.append((name,) + args + (kwargs,))
		return mock

class AsciiFormatterTest(unittest.TestCase):
	def setUp(self):
		self.formatter = AsciiFormatter()
		self.writer = MockWriter()
		self.history_counter = 0

		self.formatter.set_file(self.writer)

	def tearDown(self):
		# Check for unexpected history
		self.assertEqual(self.history_counter, len(self.writer.history))

		# Check that no state is held by the formatter at the end of the test
		self.formatter.flush()
		self.assertEqual(self.history_counter, len(self.writer.history))

	def expectRegex(self, r):
		h = self.writer.history[self.history_counter]
		self.history_counter += 1

		self.assertEqual(len(h), 2)
		self.assertEqual(h[0], 'write')
		ln = h[1]
		self.assertTrue(re.search(r, ln))

	def expectNoOutput(self):
		self.assertEqual(self.history_counter, len(self.writer.history))

	def testFormatAttributeTitle(self):
		title = 'Unit test title'
		self.formatter.format_attribute('title', title)
		self.expectRegex('^%s$' % (title))
		self.expectRegex('^===============$')
		self.expectRegex('^$')

	def testFormatAttributeSimpleComment(self):
		comment = 'This is a comment'
		self.formatter.format_attribute('comment', comment)
		# Should self-flush because there are no staff text acculated
		self.expectRegex('^# %s$' % (comment))

	def testFormatAttributeDelayedComment(self):
		comment = 'This is a comment'
		self.formatter.format_barline('unused')
		self.formatter.format_attribute('comment', comment)
		self.expectNoOutput() # No output until flush
		self.formatter.flush()
		for t in tunings.STANDARD_TUNING:
			self.expectRegex('^|$')
		self.expectRegex('^# %s$' % (comment))
			

	def testFormatAttributeKey(self):
		self.formatter.format_attribute('key', 'C')
		# No output expected (and tested for by tearDown() )

	def testFormatAttributeTime(self):
		self.formatter.format_attribute('time', '4/4')
		# No output expected (and tested for by tearDown() )

	def testFormatBarlineAtStartOfLine(self):
		self.formatter.format_barline('unused')
		self.expectNoOutput()
		self.formatter.flush()
		for t in tunings.STANDARD_TUNING:
			self.expectRegex('^|$')

	def testFormatBarlineAtEndOfLine(self):
		self.formatter.format_note(tunings.STANDARD_TUNING)
		self.formatter.format_barline('unused')
		self.expectNoOutput()
		self.formatter.flush()
		for t in tunings.STANDARD_TUNING:
			self.expectRegex('^-0-|$')

	def testFormatNoteWithUnfrettedStrum(self):
		self.formatter.format_note(tunings.STANDARD_TUNING)
		self.expectNoOutput()
		self.formatter.flush()
		for t in tunings.STANDARD_TUNING:
			self.expectRegex('^-0$')

	def testFormatNoteBigEChord(self):
		chord = (0, 2, 2, 1, 0, 0)
		notes = tunings.chord(chord)
		self.formatter.format_note(notes)
		self.expectNoOutput()
		self.formatter.flush()
		self.expectRegex('^-0$')
		self.expectRegex('^-0$')
		self.expectRegex('^-1$')
		self.expectRegex('^-2$')
		self.expectRegex('^-2$')
		self.expectRegex('^-0$')

	def testFormatNoteDChord(self):
		chord = (None, None, 0, 2, 3, 2)
		notes = tunings.chord(chord)
		self.formatter.format_note(notes)
		self.expectNoOutput()
		self.formatter.flush()
		self.expectRegex('^-2$')
		self.expectRegex('^-3$')
		self.expectRegex('^-2$')
		self.expectRegex('^-0$')
		self.expectRegex('^--$')
		self.expectRegex('^--$')
		
	def testFormatNoteNinthPositionBarre(self):
		chord = (9, 11, 11, 10, 9, 9)
		notes = tunings.chord(chord)
		self.formatter.format_note(notes)
		self.expectNoOutput()
		self.formatter.flush()
		self.expectRegex('^--9$')
		self.expectRegex('^--9$')
		self.expectRegex('^-10$')
		self.expectRegex('^-11$')
		self.expectRegex('^-11$')
		self.expectRegex('^--9$')

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()

