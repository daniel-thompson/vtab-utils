import re

HAMMER_ON = 'hammer-on'
PULL_OFF = 'pull-off'

class Note(object):
	'''
	classdocs
	'''

	RE_PITCH = re.compile(r'([A-G])([#b]{0,1})([0-9])')

	MIDI_OFFSET = 12

	VALID_ARTICULATION = ( HAMMER_ON, PULL_OFF )

	def __init__(self, s):
		try:
			self.pitch = int(s)
		except:
			self.set(s)
		self.articulation = set()

	def __hash__(self):
		return int(self)

	def __lt__(self, other):
		return int(self) < int(other)

	def __le__(self, other):
		return int(self) <= int(other)

	def __eq__(self, other):
		if not other:
			return False

		return int(self) == int(other)

	def __ge__(self, other):
		return int(self) >= int(other)

	def __gt__(self, other):
		return int(self) > int(other)

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

	def add_articulation(self, a):
		"""Add articulation metadata to the current note.

		Metadata is *not* included during copy, compare, stringize or any
		similar operation.

		"""
		assert(a in self.VALID_ARTICULATION)
		self.articulation.add(a)

	def remove_articulation(self, a):
		"""Remove articulation metadata from the current note.

		Metadata is *not* included during copy, compare, stringize or any
		similar operation.

		"""
		assert(a in self.VALID_ARTICULATION)
		self.articulation.discard(a)

	def has_articulation(self, a):
		"""Test whether the note includes a specific item of metadata."""
		assert(a in self.VALID_ARTICULATION)
		return a in self.articulation
