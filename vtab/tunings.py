'''
Created on 24 Jun 2013

@author: drt
'''

from .note import Note

STANDARD_TUNING = (
		Note('E2'),
		Note('A2'),
		Note('D3'),
		Note('G3'),
		Note('B3'),
		Note('E4'))

BASS_TUNING = (
		Note('E1'),
		Note('A1'),
		Note('D2'),
		Note('G2'))

def chord(frets, tuning=STANDARD_TUNING):
	c = []
	for f, t in zip(frets, tuning):
		if None == f:
			c.append(None)
		else:
			c.append(t + f)
	return tuple(c)
