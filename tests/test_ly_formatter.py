import re
import sys
import unittest
from fractions import Fraction
from vtab import tunings
from vtab.ly_formatter import LilypondFormatter
from vtab.note import Note

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

	def format_note(self, notes, duration=Fraction(1, 4), tie=False):
		'''A simple typing convenience to provide a default note length for tests.'''
		def parse_note(note):
			try:
				return Note(note)
			except:
				return None
		try:
			notes = tuple([parse_note(n) for n in notes.split()])
		except:
			pass
		self.formatter.format_note(notes, duration, tie)

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
		# regex allows for some evolution of formatting but does require that the title
		# be wrapped up in double quotes
		self.assertTrue(self.skipToRegex('title.*"%s"' % (title)))

	def testFormatNoComposer(self):
		self.formatter.flush()
		self.assertTrue(self.skipToRegex('composer.*##f'))

	def testFormatAttributeComposer(self):
		title = 'Unit test composer'
		self.formatter.format_attribute('composer', title)
		self.formatter.flush()
		# regex allows some change of formatting but does require that the title
		# be wrapped up in double quotes
		self.assertTrue(self.skipToRegex('composer.*"%s"' % (title)))


	def testFormatAttributeSimpleComment(self):
		comment = 'This is a comment'
		self.formatter.format_attribute('comment', comment)
		self.formatter.flush()
		self.assertTrue(self.skipToRegex('^  %% %s$' % (comment)))

	def testFormatAttributeDelayedComment(self):
		comment = 'This is a comment'
		notes = 'X  X  D3 A3 X  X'

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
		self.format_note('X C3  X  X  X  X', Fraction(1, 1))
		self.formatter.format_barline({})
		self.formatter.format_attribute('duration', Fraction(1, 2))
		self.format_note('X  X  D3 X  X  X', Fraction(1,2))
		self.format_note('X  X  E3 X  X  X', Fraction(1,2))
		self.formatter.format_barline({})
		self.formatter.flush()

		self.assertTrue(self.skipToRegex(r"^  <"))
		self.expectRegex(r"^  <c\\5>1  [|]$")
		self.expectRegex(r"^  <d\\4>2  <e\\4>2  [|]$")

	def testFormatDoubleBar(self):
		self.formatter.format_attribute('duration', Fraction(1, 1))
		self.format_note('X C3  X  X  X  X', Fraction(1, 1))
		self.formatter.format_barline({ 'double': 'plain' })
		self.formatter.format_attribute('duration', Fraction(1, 2))
		self.format_note('X  X  D3 X  X  X', Fraction(1,2))
		self.format_note('X  X  E3 X  X  X', Fraction(1,2))
		self.formatter.format_barline({ 'double': 'plain' })
		self.formatter.flush()

		self.assertTrue(self.skipToRegex(r"^  <"))
		self.expectRegex(r"^  <c\\5>1  [|][|]$")
		self.expectRegex(r"^  <d\\4>2  <e\\4>2  [|][|]$")

	def testFormatRepeat(self):
		self.formatter.format_attribute('duration', Fraction(1, 1))
		self.format_note('X C3  X  X  X  X', Fraction(1, 1))
		self.formatter.format_barline({ 'repeat' : 'open'})
		self.formatter.format_attribute('duration', Fraction(1, 2))
		self.format_note('X  X  D3 X  X  X', Fraction(1,2))
		self.format_note('X  X  E3 X  X  X', Fraction(1,2))
		self.formatter.format_barline({'repeat' : 'close'})
		self.formatter.flush()

		r = r"^  <c\\5>1  \\repeat volta 2 {$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)
		self.expectRegex(r"^  <d\\4>2  <e\\4>2  }$")


	def testFormatNoteWithUnfrettedStrum(self):
		self.format_note(tunings.STANDARD_TUNING)
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <e,\\6 a,\\5 d\\4 g\\3 b\\2 e'\\1>4$"))

	def testFormatNoteBigEChord(self):
		self.format_note('E2 B2 E3 G#3 B3 E4')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <e,\\6 b,\\5 e\\4 gis\\3 b\\2 e'\\1>4$"))

	def testFormatNoteDChord(self):
		self.format_note('X  X  D3 A3 D4 F#4')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <d\\4 a\\3 d'\\2 fis'\\1>4$"))

	def testFormatNoteNinthPositionBarre(self):
		self.format_note('C#3 G#3 C#4 F4 G#4 C#5')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <cis\\6 gis\\5 cis'\\4 f'\\3 gis'\\2 cis''\\1>4$"))

	def testFormatMinim(self):
		self.formatter.format_attribute('duration', Fraction(1, 2))
		self.format_note('X C3  X  X  X  X', Fraction(1,2))
		self.formatter.format_attribute('duration', Fraction(1, 4))
		self.format_note('X C3  X  X  X  X', Fraction(1,2))
		self.formatter.format_barline('unused')
		self.formatter.format_attribute('duration', Fraction(1, 8))
		self.format_note('X C3  X  X  X  X', Fraction(1,2))
		self.formatter.format_attribute('duration', Fraction(1, 16))
		self.format_note('X C3  X  X  X  X', Fraction(1,2))
		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>2  <c\\5>2  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)
		self.expectRegex(r)

	def testFormatCrotchet(self):
		self.formatter.format_attribute('duration', Fraction(1, 4))
		self.format_note('X C3  X  X  X  X')

		self.formatter.format_attribute('duration', Fraction(1, 8))
		self.format_note('X C3  X  X  X  X')

		self.formatter.format_attribute('duration', Fraction(1, 16))
		self.format_note('X C3  X  X  X  X')

		self.formatter.format_attribute('duration', Fraction(1, 32))
		self.format_note('X C3  X  X  X  X')

		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>4  <c\\5>4  <c\\5>4  <c\\5>4  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)

	def testFormatDottedCrotchet(self):
		self.formatter.format_attribute('duration', Fraction(1, 8))
		self.format_note('X C3  X  X  X  X', Fraction(3, 8))

		self.formatter.format_attribute('duration', Fraction(1, 16))
		self.format_note('X C3  X  X  X  X', Fraction(3, 8))

		self.formatter.format_attribute('duration', Fraction(1, 4))
		self.format_note('X C3  X  X  X  X')

		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>4.  <c\\5>4.  <c\\5>4  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)

	def testFormatQuaver(self):
		self.formatter.format_attribute('duration', Fraction(1, 8))
		self.format_note('X C3  X  X  X  X', Fraction(1,8))

		self.formatter.format_attribute('duration', Fraction(1, 16))
		self.format_note('X C3  X  X  X  X', Fraction(1,8))

		self.formatter.format_attribute('duration', Fraction(1, 32))
		self.format_note('X C3  X  X  X  X', Fraction(1,8))

		self.formatter.format_attribute('duration', Fraction(1, 64))
		self.format_note('X C3  X  X  X  X', Fraction(1,8))

		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>8  <c\\5>8  <c\\5>8  <c\\5>8  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)

	def testFormatTie(self):
		self.format_note('X C3  X  X  X  X', Fraction(1,4))
		self.format_note('X C3  X  X  X  X', Fraction(1,4), tie=True)
		self.format_note('X C3  X  X  X  X', Fraction(1,2))
		self.formatter.format_barline('unused')
		self.format_note('X C3  X  X  X  X', Fraction(1,1), tie=True)
		self.formatter.format_barline('unused')

		self.formatter.flush()

		self.assertTrue(self.skipToRegex(r"^  <"))
		self.expectRegex(r"^  <c\\5>4~  <c\\5>4  <c\\5>2~  [|]$")
		self.expectRegex(r"^  <c\\5>1  [|]$")

	def testFormatOverText(self):
		self.formatter.format_attribute('text', 'C')
		self.format_note('X C3  X  X  X  X')

		self.formatter.format_attribute('text', 'Dm')
		self.format_note('X  X  D3 X  X  X')

		self.formatter.format_attribute('text', 'Em')
		self.format_note('X  X  E3 X  X  X')

		self.formatter.format_attribute('text', 'F')
		self.format_note('X  X F3 X  X  X')

		self.formatter.format_barline('unused')
		self.formatter.flush()

		r = r'^  <c\\5>4\^"C"  <d\\4>4\^"Dm"  <e\\4>4\^"Em"  <f\\4>4\^"F"  [|]$'
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)


if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()

