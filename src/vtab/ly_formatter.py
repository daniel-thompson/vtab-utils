import re, string, sys, unittest
from fractions import Fraction
from vtab import tunings


VERSION='''\
\\version "2.16.0"
'''
HEADER=string.Template('''\
\\header {
  title = "${title}"
  tagline = ##f
}
''')
PAPER='''\
\\paper {
  #(set-paper-size "a4")

  % Align the first line with everything else
  indent = #0

  % A4 paper is 210mm, this gives a left margin of 20mm and right margin of 10mm
  left-margin = 20 \\mm
  line-width = 180 \\mm
}
'''
MELODY=string.Template('''\
Melody = {
  \\voiceOne
  \\key ${key}
  \\time ${time}
  ${melody}
}
''')
FINALIZE='''\
NoStringNumbers = {
  % Setting the stencil to false causes problems placing other objects
  \\override StringNumber #'transparent = ##t
}

NoStems = {
  \\override Beam #'stencil = ##f
  \\override Dots #'stencil = ##f
  \\override Stem #'stencil = ##f
}

StaffMelody = {
  \\NoStringNumbers
  \\Melody
}

TabMelody  = {
  \\NoStems
  \\removeWithTag #'chords
  \\removeWithTag #'texts
  \\Melody
}

\\score {
  <<
    \\new StaffGroup = "Fingerstyle" <<
      \\new Staff = "TraditionalStaff" <<
        \\clef "treble_8"
        \\context Voice = "Melody" { \\StaffMelody }
      >>
      \\new TabStaff = "TabStaff" <<
        \\context TabVoice = "Melody" { \\TabMelody }
      >>
    >>
  >>
}
'''

class LilypondFormatter(object):
	def __init__(self):
		self.f = sys.stdout
		self.set_tuning(tunings.STANDARD_TUNING)

		self._attributes = {
			'key' : 'c \\major',
			'time' : '4/4',
			'duration' : '8',
		}

		self._melody = []
		self._note_len = Fraction(0, 1)

	def set_file(self, f):
		self.f = f

	def set_tuning(self, tuning):
		self._tuning = tuning

	def format_attribute(self, key, value):
		try:
			fn = getattr(self, 'format_' + key)
		except:
			fn = None
		if None != fn:
			fn(value)
		else:
			self.format_comment("ERROR: Unsupported attribute (%s: '%s')\n" % (key, value))

	def format_comment(self, comment):
		# Force a line break if the last line does not have one
		self._flush_current_note()
		if len(self._melody) and not self._melody[-1].endswith('\n'):
			self._melody.append('\n')
		self._melody.append('% ' + comment + '\n')

	def format_duration(self, duration):
		self._duration = Fraction(1, int(duration))

	def format_key(self, key):
		assert(len(key) > 0)

		letter = key[0].lower()

		thingness = '\\major'
		if len(key) == 2 and key[1] == 'm':
			thingness = '\\minor'
		elif len(key) >= 2:
			self.format_comment("ERROR: Unsupported key ('%s')\n" % (key))

		self._attributes['key'] = letter + ' ' + thingness

	def format_time(self, unused):
		# For tab only output the timing is not important
		pass

	def format_title(self, title):
		self._attributes['title'] = title

	def format_barline(self, unused):
		self._flush_current_note()
		self._melody.append('|\n')

	def format_note(self, notes):
		ly_notes = []
		for note, string in zip(notes, range(6, 0, -1)):
			if note is None:
				continue
			ly_notes.append(note.to_lilypond() + '\\' + str(string))
		if len(ly_notes):
			self._flush_current_note()
			self._melody.append('<' + (' '.join(ly_notes)) + '>')
			self._note_len = self._duration
		else:
			self._note_len += self._duration

	def _flush_current_note(self):
		if self._note_len:
			assert(self._note_len.numerator == 1)
			self._melody[-1] += str(self._note_len.denominator)
			self._note_len = Fraction(0, 1)

	def flush(self):
		self._flush_current_note()

		self._attributes['melody'] = '  '.join(self._melody)

		self.f.write(VERSION)
		self.f.write(HEADER.safe_substitute(self._attributes))
		self.f.write(PAPER)
		self.f.write(MELODY.safe_substitute(self._attributes))
		self.f.write(FINALIZE)

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
		self.formatter.format_attribute('duration', '4')

	def tearDown(self):
		pass

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

	def testFormatAttributeTitle(self):
		title = 'Unit test title'
		self.formatter.format_attribute('title', title)
		self.formatter.flush()
		self.assertTrue(self.skipToRegex('title.*%s' % (title)))

	def testFormatAttributeSimpleComment(self):
		comment = 'This is a comment'
		self.formatter.format_attribute('comment', comment)
		self.formatter.flush()
		self.assertTrue(self.skipToRegex('^  %% %s$' % (comment)))

	def testFormatAttributeDelayedComment(self):
		comment = 'This is a comment'
		chord = (None, None, 0, 2, None, None)
		notes = tunings.chord(chord)

		self.formatter.format_note(notes)
		self.formatter.format_attribute('comment', comment)
		self.formatter.format_note(notes)
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

	def testFormatAttributeTime(self):
		self.formatter.format_attribute('time', '4/4')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r'\\time 4/4'))

	def testFormatAttributeUnknown(self):
		self.formatter.format_attribute('unknown', 'unknown')
		self.formatter.flush()
		self.assertTrue(self.skipToRegex('^  % ERROR.*Unsupported attribute'))

	def testFormatBar(self):
		self.formatter.format_attribute('duration', '1')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_barline('unused')
		self.formatter.format_attribute('duration', '2')
		self.formatter.format_note(tunings.chord((None, None, 0, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, 2, None, None, None)))
		self.formatter.format_barline('unused')
		self.formatter.flush()

		r = r"^  <c\\5>1  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)
		self.expectRegex(r"^  <d\\4>2  <e\\4>2  [|]$")

	def testFormatNoteWithUnfrettedStrum(self):
		self.formatter.format_note(tunings.STANDARD_TUNING)
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <e,\\6 a,\\5 d\\4 g\\3 b\\2 e'\\1>4$"))

	def testFormatNoteBigEChord(self):
		self.formatter.format_note(tunings.chord((0, 2, 2, 1, 0, 0)))
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <e,\\6 b,\\5 e\\4 gis\\3 b\\2 e'\\1>4$"))

	def testFormatNoteDChord(self):
		self.formatter.format_note(tunings.chord((None, None, 0, 2, 3, 2)))
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <d\\4 a\\3 d'\\2 fis'\\1>4$"))

	def testFormatNoteNinthPositionBarre(self):
		self.formatter.format_note(tunings.chord((9, 11, 11, 10, 9, 9)))
		self.formatter.flush()
		self.assertTrue(self.skipToRegex(r"^  <cis\\6 gis\\5 cis'\\4 f'\\3 gis'\\2 cis''\\1>4$"))

	def testDurationInferenceMinim(self):
		self.formatter.format_attribute('duration', '2')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))

		self.formatter.format_attribute('duration', '4')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))

		self.formatter.format_barline('unused')

		self.formatter.format_attribute('duration', '8')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))

		self.formatter.format_attribute('duration', '16')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))

		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>2  <c\\5>2  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)
		self.expectRegex(r)

	def testDurationInferenceCrotchet(self):
		self.formatter.format_attribute('duration', '4')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))

		self.formatter.format_attribute('duration', '8')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))

		self.formatter.format_attribute('duration', '16')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))

		self.formatter.format_attribute('duration', '32')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))

		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>4  <c\\5>4  <c\\5>4  <c\\5>4  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)

	def testDurationInferenceQuaver(self):
		self.formatter.format_attribute('duration', '8')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))

		self.formatter.format_attribute('duration', '16')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))

		self.formatter.format_attribute('duration', '32')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))

		self.formatter.format_attribute('duration', '64')
		self.formatter.format_note(tunings.chord((None, 3, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))
		self.formatter.format_note(tunings.chord((None, None, None, None, None, None)))

		self.formatter.format_barline('unused')

		self.formatter.flush()

		r = r"^  <c\\5>8  <c\\5>8  <c\\5>8  <c\\5>8  [|]$"
		self.assertTrue(self.skipToRegex(r))
		self.expectRegex(r)

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()

