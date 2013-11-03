import re
import unittest
import sys
from fractions import Fraction
from vtab import tunings
from vtab.ascii_formatter import AsciiFormatter

class MockWriter(object):
	def __init__(self):
		self.history = []
		self.log = False
	def write(self, s):
		if self.log:
			sys.stdout.write('output >>> ' + s)
		self.history.append(('write', s.rstrip()))

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

	def format_note(self, note, duration=Fraction(1, 4), tie=False):
		'''A simple typing convenience to provide a default note length for tests.'''
		self.formatter.format_note(note, duration, tie)

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
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^|$')
		self.expectRegex('^# %s$' % (comment))
		self.expectRegex('^$')

	def testFormatAttributeKey(self):
		self.formatter.format_attribute('key', 'C')
		# No output expected (and tested for by tearDown() )

	def testFormatAttributeTime(self):
		self.formatter.format_attribute('time', '4/4')
		# No output expected (and tested for by tearDown() )

	def testFormatAttributeUnknown(self):
		self.formatter.format_attribute('unknown', 'unknown')
		self.expectRegex('Unsupported attribute')

	def testFormatBarlineAtStartOfLine(self):
		self.formatter.format_barline('unused')
		self.expectNoOutput()
		self.formatter.flush()
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^|$')
		self.expectRegex('^$')

	def testFormatBarlineAtEndOfLine(self):
		self.format_note(tunings.STANDARD_TUNING)
		self.formatter.format_barline('unused')
		self.expectNoOutput()
		self.formatter.flush()
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^-0-|$')
		self.expectRegex('^$')

	def testFormatBarlineEarlyWrap(self):
		for dummy in range(32):
			self.formatter.format_barline('unused')
		self.expectNoOutput()
		self.formatter.format_barline('unused')
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^|' + ('-|' * 31) + '$')
		self.expectRegex('^$')
		self.formatter.flush()
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^|$')
		self.expectRegex('^$')

	def testFormatBarlineLastCharacterWrap(self):
		self.formatter.format_barline('unused')
		for dummy in range(38):
			self.format_note(tunings.STANDARD_TUNING)
		self.expectNoOutput()
		self.formatter.format_barline('unused')
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^|' + ('-0' * 38) + '-|$')
		self.expectRegex('^$')
		self.formatter.flush()
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^|$')
		self.expectRegex('^$')

	def testFormatBarlineLateWrap(self):
		for dummy in range(39):
			self.format_note(tunings.STANDARD_TUNING)
		self.expectNoOutput()
		self.formatter.format_barline('unused')
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^' + ('-0' * 39) + '$')
		self.expectRegex('^$')
		self.formatter.flush()
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^|$')
		self.expectRegex('^$')

	def testFormatNoteWithUnfrettedStrum(self):
		self.format_note(tunings.STANDARD_TUNING)
		self.expectNoOutput()
		self.formatter.flush()
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^-0$')
		self.expectRegex('^$')

	def testFormatNoteBigEChord(self):
		chord = (0, 2, 2, 1, 0, 0)
		notes = tunings.chord(chord)
		self.format_note(notes)
		self.expectNoOutput()
		self.formatter.flush()
		self.expectRegex('^-0$')
		self.expectRegex('^-0$')
		self.expectRegex('^-1$')
		self.expectRegex('^-2$')
		self.expectRegex('^-2$')
		self.expectRegex('^-0$')
		self.expectRegex('^$')

	def testFormatNoteDChord(self):
		chord = (None, None, 0, 2, 3, 2)
		notes = tunings.chord(chord)
		self.format_note(notes)
		self.expectNoOutput()
		self.formatter.flush()
		self.expectRegex('^-2$')
		self.expectRegex('^-3$')
		self.expectRegex('^-2$')
		self.expectRegex('^-0$')
		self.expectRegex('^--$')
		self.expectRegex('^--$')
		self.expectRegex('^$')

	def testFormatNoteNinthPositionBarre(self):
		chord = (9, 11, 11, 10, 9, 9)
		notes = tunings.chord(chord)
		self.format_note(notes)
		self.expectNoOutput()
		self.formatter.flush()
		self.expectRegex('^--9$')
		self.expectRegex('^--9$')
		self.expectRegex('^-10$')
		self.expectRegex('^-11$')
		self.expectRegex('^-11$')
		self.expectRegex('^--9$')
		self.expectRegex('^$')

	def testFormatNoteLineEndings(self):
		for dummy in range(39):
			self.format_note(tunings.STANDARD_TUNING)
		self.expectNoOutput()
		self.format_note(tunings.STANDARD_TUNING)
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^' + ('-0' * 39) + '$')
		self.expectRegex('^$')
		self.formatter.flush()
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^-0$')
		self.expectRegex('^$')

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()

