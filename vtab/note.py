import re

class Note(object):
	'''
	classdocs
	'''

	RE_PITCH = re.compile(r'([A-G])([#b]{0,1})([0-9])')

	MIDI_OFFSET = 12

	def __init__(self, s):
		try:
			self.pitch = int(s)
		except:
			self.set(s)

	def __cmp__(self, other):
		if None == other:
			return 1

		return int(self) - int(other)

	def __add__(self, other):
		return Note(self.pitch + int(other))

	def __sub__(self, other):
		if isinstance(other, Note):
			return self.pitch - other.pitch
		else:
			return Note(self.pitch - int(other))

	def __repr__(self):
		me = self.decompose()
		return me[0] + me[1] + str(me[2])

	def decompose(self):
		octave = int((self.pitch - self.MIDI_OFFSET) / 12)
		semitone = (self.pitch - self.MIDI_OFFSET) % 12

		letter =    'CCDDEFFGGAAB'[semitone]
		sharpflat = ' # #  # # # '[semitone].strip()

		return (letter, sharpflat, octave)

	def to_lilypond(self):
		(letter, sharpflat, octave) = self.decompose()
		letter = letter.lower()
		if sharpflat == '#':
			letter += 'is'
		elif sharpflat == 'b':
			letter += 'es'
		else:
			assert sharpflat == ''

		if octave > 3:
			letter += "'" * (octave - 3)
		elif octave < 3:
			letter += ',' * (3 - octave)

		return letter

	def set(self, s):
		m = self.RE_PITCH.match(s)

		letter = m.group(1)
		sharpflat = m.group(2)
		octave = m.group(3)

		if letter == 'C':
			self.pitch = 0
		elif letter == 'D':
			self.pitch = 2
		elif letter == 'E':
			self.pitch = 4
		elif letter == 'F':
			self.pitch = 5
		elif letter == 'G':
			self.pitch = 7
		elif letter == 'A':
			self.pitch = 9
		elif letter == 'B':
			self.pitch = 11
		else:
			assert(0)

		if sharpflat == '#':
			self.pitch += 1
		elif sharpflat == 'b':
			self.pitch -= 1
		elif sharpflat == '':
			pass
		else:
			assert(0)

		self.pitch += self.MIDI_OFFSET + 12 * int(octave)

	def __int__(self):
		return self.pitch
