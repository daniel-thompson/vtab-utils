import re, string, sys, unittest
from fractions import Fraction
from vtab import tunings


VERSION='''\
\\version "2.16.0"
'''
HEADER=string.Template('''\
\\header {
  title = ${title}
  composer = ${composer}
  tagline = ##f
}
''')
PAPER='''\
\\paper {
$(if (not (ly:get-option 'afive)) #{
  \\paper {
    #(set-paper-size "a4")
    left-margin = 20
    line-width = 180
  }
#}
#{
  \\paper {
    #(set-paper-size "a5")
    top-margin = 3
    bottom-margin = 3
    left-margin = 5
    line-width = 140.5
  }
#})

  % Align the first line with everything else
  indent = #0
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

GuitarStaffAndTab = <<
  \\new StaffGroup = "Guitar" <<
    \\new Staff = "TraditionalStaff" <<
      \\clef "treble_8"
      \\context Voice = "Melody" { \\StaffMelody }
    >>
    \\new TabStaff = "TabStaff" <<
      \\context TabVoice = "Melody" { \\TabMelody }
    >>
  >>
>>

GuitarTabOnly = <<
  \\new StaffGroup = "Guitar" <<
    \\new TabStaff = "TabStaff" <<
      \\context TabVoice = "Melody" { \TabMelody }
    >>
  >>
>>

Guitar =
$(if (ly:get-option 'afive) #{
\GuitarTabOnly
#}
#{
\GuitarStaffAndTab
#})

\\score { \\Guitar }
'''

class LilypondFormatter(object):
	def __init__(self):
		self.f = sys.stdout
		self.set_tuning(tunings.STANDARD_TUNING)

		self._attributes = {
			'key' : 'c \\major',
			'time' : '4/4',
			'duration' : Fraction(1, 8),
		}

		self._melody = []
		self._melody_last_note = None
		self._note_len = Fraction(0, 1)
		self._text = None
		self._brace_count = 0

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

	def format_composer(self, composer):
		self._attributes['composer'] = composer

	def format_duration(self, duration):
		self._duration = duration

	def format_key(self, key):
		assert(len(key) > 0)

		tonality = ' \\major'
		if key[-1] == 'm':
			tonality = ' \\minor'
			key = key[:-1]

		scale = key.replace('#', 'is').replace('b', 'es').lower()

		self._attributes['key'] = scale + tonality

	def format_text(self, text):
		assert(None == self._text)
		self._text = text

	def format_time(self, unused):
		# For tab only output the timing is not important
		pass

	def format_title(self, title):
		self._attributes['title'] = title

	def format_barline(self, attributes):
		bar = '|'

		if 'double' in attributes:
			if attributes['double'] == 'plain':
				bar = '||'
			elif attributes['double'] == 'left':
				bar = '.|'
			elif attributes['double'] == 'right':
				bar = '|.'
			elif attributes['double'] == 'both':
				bar = '.|.'
				
		# At present repeat attributes deliberately clobber double attributes		
		if 'repeat' in attributes:
			if attributes['repeat'] == 'open':
				bar = '\\repeat volta 2 {'
				self._brace_count += 1
			elif attributes['repeat'] == 'close':
				bar = '}'
				self._brace_count -= 1
			elif attributes['repeat'] == 'both':
				bar = '} \\repeat volta 2 {'

		self._melody.append(bar + '\n')

	def format_note(self, notes, duration, tie):
		ly_notes = []
		for note, string in zip(notes, range(6, 0, -1)):
			if note is None:
				continue
			ly_notes.append(note.to_lilypond() + '\\' + str(string))

		if 0 != len(ly_notes):
			lynote = '<' + (' '.join(ly_notes)) + '>'
		else:
			lynote = 'r'

		if duration.numerator == 3:
			remaining_duration = duration - duration/3
			dot = '.'
		else:
			remaining_duration = duration
			dot = ''
		assert(remaining_duration.numerator == 1)
		lyduration = str(remaining_duration.denominator) + dot
		lytext = ''
		if self._text:
			lytext = '^"%s"' % self._text
			self._text = None

		if tie:
			assert(None != self._melody_last_note)
			assert(0 != len(ly_notes))
			self._melody[self._melody_last_note] += '~'
		self._melody_last_note = len(self._melody)
		self._melody.append(lynote + lyduration + lytext)

	def flush(self):
		while self._brace_count > 0:
			self._melody.append('}')
			self._brace_count -= 1
		assert(self._brace_count >= 0)

		self._attributes['melody'] = '  '.join(self._melody)

		# Fixup the header attributes if needed
		for attr in ('title', 'composer'):
			if attr in self._attributes and '"' not in self._attributes[attr]:
				self._attributes[attr] = '"' + self._attributes[attr] + '"'
			else:
				self._attributes[attr] = '##f'

		self.f.write(VERSION)
		self.f.write(HEADER.safe_substitute(self._attributes))
		self.f.write(PAPER)
		self.f.write(MELODY.safe_substitute(self._attributes))
		self.f.write(FINALIZE)
