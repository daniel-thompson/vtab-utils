import re
import sys
import unittest
from fractions import Fraction
from vtab import tunings
from vtab.ly_formatter import LilypondFormatter

class MockWriter(object):
	def __init__(self):
		self.history = []
		self.log = False
	def write(self, s):
		for line in s.split('\n'):
			if self.log:
				sys.stdout.write('output >>> ' + line.rstrip() + '\n')
			self.history.append(('write', line.rstrip()))

	def __getattr__(self, name):
		def mock(*args, **kwargs):
			if 0 == len(kwargs):
				self.history.append((name,) + args)
			else:
				self.history.append((name,) + args + (kwargs,))
		return mock

class LilypondFormatterTest(unittest.TestCase):
	def setUp(self):
		self.formatter = LilypondFormatter()
		self.writer = MockWriter()
		self.history_counter = 0

		self.formatter.set_file(self.writer)
		self.formatter.format_attribute('duration', Fraction(1, 4))

	def tearDown(self):
		pass

	def format_note(self, note, duration=Fraction(1, 4)):
		'''A simple typing convenience to provide a default note length for tests.'''
		self.formatter.format_note(note, duration)

	def expectRegex(self, r):
		h = self.writer.history[self.history_counter]
		self.history_counter += 1

		self.assertEqual(len(h), 2)
		self.assertEqual(h[0], 'write')
		ln = h[1]
		self.assertTrue(re.search(r, ln),
			"'%s' does not match in '%s' at line %d" % (r, ln, self.history_counter))

	def skipToRegex(self, r):
		while self.history_counter < len(self.writer.history):
			h = self.writer.history[self.history_counter]
			if h[0] == 'write':
				ln = h[1]
				if re.search(r, ln):
					return True

			self.history_counter += 1

		return False

	def expectNoOutput(self):
		self.assertEqual(self.history_counter, len(self.writer.history))

	def testFormatNoTitle(self):
		self.formatter.flush()
		self.assertTrue(self.skipToRegex('title.*##f'))

	def testFormatAttributeTitle(self):
		title = 'Unit test title'
		self.formatter.format_attribute('title', title)
		self.formatter.flush()
		# regex allows some change of formatting but does require that the title
		# be wrapped up in double quotes
		self.assertTrue(self.skipToRegex('title.*"%s"' % (title)))

	def testFormatAttributeSimpleComment(self):
		comment = 'This is a comment'
		self.formatter.format_attribute('comment', comment)
		self.formatter.flush()
		self.assertTrue(self.skipToRegex('^  %% %s$' % (comment)))

	def testFormatAttributeDelayedComment(self):
		comment = 'This is a comment'
		chord = (None, None, 0, 2, None, None)
		notes = tunings.chord(chord)

		self.format_note(notes)
		self.formatter.format_attribute('comment', comment)
		self.format_note(notes)
		self.formatter.flush()

		self.assertTrue(self.skipToRegex(r'^  <d\\4 a\\3>4$'))
		self.expectRegex(r'^  <d\\4 a\\3>4$')
		self.expectRegex(r'^  %% %s$' % (comment))
		self.expectRegex(r'^  <d\\4 a\\3>4$')

	def testFormatAttributeKeyDefault(self):
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r'\\key c \\major'))

	def testFormatAttributeKeyCMajor(self):
		self.formatter.format_attribute('key', 'C')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r'\\key c \\major'))

	def testFormatAttributeKeyAMajor(self):
		self.formatter.format_attribute('key', 'A')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r'\\key a \\major'))

	def testFormatAttributeKeyBMinor(self):
		self.formatter.format_attribute('key', 'Bm')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r'\\key b \\minor'))

	def testFormatAttributeKeyASharpMajor(self):
		self.formatter.format_attribute('key', 'A#')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r'\\key ais \\major'))

	def testFormatAttributeKeyBFlatMinor(self):
		self.formatter.format_attribute('key', 'Bbm')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r'\\key bes \\minor'))

	def testFormatAttributeTime(self):
		self.formatter.format_attribute('time', '4/4')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r'\\time 4/4'))

	def testFormatAttributeUnknown(self):
		self.formatter.format_attribute('unknown', 'unknown')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex('^  % ERROR.*Unsupported attribute'))

	def testFormatBar(self):
		self.formatter.format_attribute('duration', Fraction(1, 1))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(1, 1))
		self.formatter.format_barline('unused')
		self.formatter.format_attribute('duration', Fraction(1, 2))
		self.format_note(tunings.chord((None, None, 0, None, None, None)), Fraction(1,2))
		self.format_note(tunings.chord((None, None, 2, None, None, None)), Fraction(1,2))
		self.formatter.format_barline('unused')
		self.formatter.flush()

		r = r"^  <c\\5>1  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)
		self.expectRegex(r"^  <d\\4>2  <e\\4>2  [|]$")

	def testFormatNoteWithUnfrettedStrum(self):
		self.format_note(tunings.STANDARD_TUNING)
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <e,\\6 a,\\5 d\\4 g\\3 b\\2 e'\\1>4$"))

	def testFormatNoteBigEChord(self):
		self.format_note(tunings.chord((0, 2, 2, 1, 0, 0)))
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <e,\\6 b,\\5 e\\4 gis\\3 b\\2 e'\\1>4$"))

	def testFormatNoteDChord(self):
		self.format_note(tunings.chord((None, None, 0, 2, 3, 2)))
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <d\\4 a\\3 d'\\2 fis'\\1>4$"))

	def testFormatNoteNinthPositionBarre(self):
		self.format_note(tunings.chord((9, 11, 11, 10, 9, 9)))
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <cis\\6 gis\\5 cis'\\4 f'\\3 gis'\\2 cis''\\1>4$"))

	def testFormatMinim(self):
		self.formatter.format_attribute('duration', Fraction(1, 2))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(1,2))
		self.formatter.format_attribute('duration', Fraction(1, 4))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(1,2))
		self.formatter.format_barline('unused')
		self.formatter.format_attribute('duration', Fraction(1, 8))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(1,2))
		self.formatter.format_attribute('duration', Fraction(1, 16))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(1,2))
		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>2  <c\\5>2  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)
		self.expectRegex(r)

	def testFormatCrotchet(self):
		self.formatter.format_attribute('duration', Fraction(1, 4))
		self.format_note(tunings.chord((None, 3, None, None, None, None)))

		self.formatter.format_attribute('duration', Fraction(1, 8))
		self.format_note(tunings.chord((None, 3, None, None, None, None)))

		self.formatter.format_attribute('duration', Fraction(1, 16))
		self.format_note(tunings.chord((None, 3, None, None, None, None)))

		self.formatter.format_attribute('duration', Fraction(1, 32))
		self.format_note(tunings.chord((None, 3, None, None, None, None)))

		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>4  <c\\5>4  <c\\5>4  <c\\5>4  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)

	def testFormatDottedCrotchet(self):
		self.formatter.format_attribute('duration', Fraction(1, 8))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(3, 8))

		self.formatter.format_attribute('duration', Fraction(1, 16))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(3, 8))

		self.formatter.format_attribute('duration', Fraction(1, 4))
		self.format_note(tunings.chord((None, 3, None, None, None, None)))

		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>4.  <c\\5>4.  <c\\5>4  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)

	def testFormatQuaver(self):
		self.formatter.format_attribute('duration', Fraction(1, 8))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(1,8))

		self.formatter.format_attribute('duration', Fraction(1, 16))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(1,8))

		self.formatter.format_attribute('duration', Fraction(1, 32))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(1,8))

		self.formatter.format_attribute('duration', Fraction(1, 64))
		self.format_note(tunings.chord((None, 3, None, None, None, None)), Fraction(1,8))

		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>8  <c\\5>8  <c\\5>8  <c\\5>8  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()

