import re, unittest

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
		return int(self) - int(other)

	def __add__(self, other):
		return Note(self.pitch + other)

	def __sub__(self, other):
		return Note(self.pitch - other)

	def __repr__(self):
		me = self.decompose()
		return me[0] + me[1] + str(me[2])

	def decompose(self):
		octave = int((self.pitch - self.MIDI_OFFSET) / 12)
		semitone = (self.pitch - self.MIDI_OFFSET) % 12
		
		letter =    'CCDDEFFGGAAB'[semitone]
		sharpflat = ' # #  # # # '[semitone].strip()

		return (letter, sharpflat, octave)

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

class NoteTest(unittest.TestCase):
	NOTES_WITH_SHARPS = ( 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B' )
	NOTES_WITH_FLATS = ( 'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B' )

	def setUp(self):
		self.note = Note('C4')

	def tearDown(self):
		self.note = None

	def testMatchMidiEnumeration(self):
		self.assertEqual(int(self.note), 60)

	def testSimpleRepr(self):
		self.assertEqual(str(self.note), 'C4')

	def testSimpleSharp(self):
		self.note.set('C#4')
		self.assertEqual(int(self.note), 61)

	def testIdentityInKeyOfC(self):
		for octave in range(0, 9):
			for note in self.NOTES_WITH_SHARPS:
				self.note.set(note + str(octave))
				self.assertEqual(note + str(octave), str(self.note))
				
	def testFlatNotesInKeyOfC(self):
		'''Set notes using flat notation, extract in a way correct for the key of C major.'''
		for octave in range(0, 9):
			for i in range(0,12):
				self.note.set(self.NOTES_WITH_FLATS[i] + str(octave))
				self.assertEqual(self.NOTES_WITH_SHARPS[i] + str(octave), str(self.note))
		
	def testNoRepeatsOfPitch(self):
		d = {}
		for octave in range(0, 9):
			for note in self.NOTES_WITH_SHARPS:
				self.note.set(note + str(octave))
				self.assertFalse(int(self.note) in d, "pitch already used")
				d[int(self.note)] = True
				
	def testNoGapsInPitch(self):
		last_pitch = 11 # MIDI represenation of B-1
		for octave in range(0, 9):
			for note in self.NOTES_WITH_SHARPS:
				self.note.set(note + str(octave))
				self.assertEqual(last_pitch+1, int(self.note))
				last_pitch = int(self.note)
				
	def testAddition(self):
		self.assertEqual('D4', str(self.note + 2))
		
	def testSubraction(self):
		self.assertEqual('B3', str(self.note - 1))
	
	def testIncrementalAddition(self):
		self.note += 2
		self.assertEqual('D4', str(self.note))
	
	def testIncrementalSubtraction(self):
		self.note -= 1
		self.assertEqual('B3', str(self.note))

	def testEqualityComparison(self):
		localnote = Note(int(self.note))
		self.assertEqual(localnote, self.note)

	def testGreaterThan(self):
		localnote = Note(int(self.note) + 1)
		self.assertGreater(localnote, self.note)
		self.assertFalse(self.note > localnote)

	def testLessThan(self):
		localnote = Note(int(self.note) - 1)
		self.assertLess(localnote, self.note)
		self.assertFalse(self.note < localnote)

if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()	