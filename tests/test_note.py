import unittest
from vtab.note import Note

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

	def testToLilypond(self):
		self.assertEqual(self.note.to_lilypond(), "c'")
		self.note.set('C#4')
		self.assertEqual(self.note.to_lilypond(), "cis'")
		self.note.set('D1')
		self.assertEqual(self.note.to_lilypond(), 'd,,')


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

	def testNoteSubtraction(self):
		self.assertEqual(1, self.note - Note('B3'))
		self.assertEqual(0, self.note - Note('C4'))
		self.assertEqual(-1, self.note - Note('C#4'))

	def testIncrementalAddition(self):
		self.note += 2
		self.assertEqual('D4', str(self.note))

	def testIncrementalSubtraction(self):
		self.note -= 1
		self.assertEqual('B3', str(self.note))

	def testEqualityComparison(self):
		localnote = Note(int(self.note))
		self.assertEqual(localnote, self.note)

	def testNoneComparision(self):
		self.assertNotEqual(self.note, None)
		self.assertNotEqual(None, self.note)

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
