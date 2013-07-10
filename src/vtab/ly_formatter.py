import re, string, sys, unittest
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
		if len(self._melody) and not self._melody[-1].endswith('\n'):
			self._melody.append('\n')
		self._melody.append('% ' + comment + '\n')

	def format_duration(self, duration):
		self._duration = duration

	def format_key(self, unused):
		# For tab only output the key is not important
		pass

	def format_time(self, unused):
		# For tab only output the timing is not important
		pass

	def format_title(self, title):
		self._attributes['title'] = title

	def format_barline(self, unused):
		self._melody.append('|\n')

	def format_note(self, notes):
		ly_notes = []
		for note, string in zip(notes, range(6, 1, -1)):
			if note is None:
				continue
			ly_notes.append(note.to_lilypond() + '\\' + str(string))
		self._melody.append('<' + (' '.join(ly_notes)) + '>' + self._duration)

	def flush(self):
		self._attributes['melody'] = ' '.join(self._melody)

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
				sys.stdout.write('output >>> ' + line + '\n')
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

	def tearDown(self):
		pass

	def expectRegex(self, r):
		h = self.writer.history[self.history_counter]
		self.history_counter += 1

		self.assertEqual(len(h), 2)
		self.assertEqual(h[0], 'write')
		ln = h[1]
		self.assertTrue(re.search(r, ln))

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
		self.assertTrue(self.skipToRegex('^%% %s$' % (comment)))

	def xtestFormatAttributeDelayedComment(self):
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

	def xtestFormatAttributeUnknown(self):
		self.formatter.format_attribute('unknown', 'unknown')
		self.expectRegex('Unsupported attribute')

	def xtestFormatBar(self):
		self.formatter.format_barline('unused')
		self.expectNoOutput()
		self.formatter.flush()
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^|$')
		self.expectRegex('^$')

	def xtestFormatNoteWithUnfrettedStrum(self):
		self.formatter.format_note(tunings.STANDARD_TUNING)
		self.expectNoOutput()
		self.formatter.flush()
		for dummy in tunings.STANDARD_TUNING:
			self.expectRegex('^-0$')
		self.expectRegex('^$')

	def xtestFormatNoteBigEChord(self):
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
		self.expectRegex('^$')

	def xtestFormatNoteDChord(self):
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
		self.expectRegex('^$')

	def xtestFormatNoteNinthPositionBarre(self):
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
		self.expectRegex('^$')

	def xtestFormatNoteLineEndings(self):
		for dummy in range(39):
			self.formatter.format_note(tunings.STANDARD_TUNING)
		self.expectNoOutput()
		self.formatter.format_note(tunings.STANDARD_TUNING)
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

