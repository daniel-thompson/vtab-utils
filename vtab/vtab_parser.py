import shlex
import re
import unittest
from fractions import Fraction
from vtab import tunings
from note import Note

class VtabParser(object):
	'''Match a barline (or underline), yielding barline and decoration
	Template is: "============ <decoration>"'''
	RE_BARLINE = re.compile(r'^\s*(:*[-=]{4}[-=]*:*)\s*(.*)$')

	'''Match a # character, yielding the associated comment
	Template is: "# This is a comment"'''
	RE_COMMENT = re.compile(r'^\s*#+\s*(.*)$')

	'''Match a key-value pair, yielding key and value
	Template is: "Key : Value"'''
	RE_KEYPAIR = re.compile(r'^\s*(\w+)\s*:\s*(.*)$')

	'''Match a tab line. This does not yield anything, it is only
	a recogniser (based on all tabs being for instruments with at
	least four strings).
	Template is: " | 10  |  9"'''
	RE_NOTE = re.compile(r'^\s*[|:0-9]+\s+[|:0-9]+\s+[|:0-9]+\s+[|:0-9]+')

	def __init__(self):
		self.formatters = []
		self.prev_line = None

		self._tuning = tunings.STANDARD_TUNING
		self._lineno = 0
		self._duration = Fraction(1, 4)
		self._note_len = Fraction(0, 1)

	def add_formatter(self, formatter):
		if not formatter in self.formatters:
			self.formatters += formatter,

	def remove_formatter(self, formatter):
		self.formatters.remove(formatter)

	def format_attribute(self, key, value):
		for formatter in self.formatters:
			formatter.format_attribute(key, value)

	def format_barline(self, line):
		for formatter in self.formatters:
			formatter.format_barline(line)

	def format_note(self, note, duration):
		for formatter in self.formatters:
			formatter.format_note(note, duration)

	def parse_keypair(self, key, value):
		key = key.lower()
		self.format_attribute(key, value)

	def parse_decorations(self, decorations):
		for token in decorations:
			if token[0].isdigit():
				self._duration = Fraction(1, int(token))
				self.format_attribute('duration', self._duration)
			else:
				self.format_attribute('lyric', token)

	def parse_barline(self, line):
		self._flush_current_note()
		tokens = shlex.split(line)
		self.parse_decorations(tokens[1:])
		self.format_barline(tokens[0])

	def parse_note(self, note):
		notes = shlex.split(note)
		decorations = notes[len(self._tuning):]

		def parse_string(open_string, fret):
			try:
				return open_string + int(fret)
			except:
				return None

		is_rest = ':' in notes

		notes = notes[0:len(self._tuning)]
		notes = [ parse_string(open_string, fret) for (open_string, fret) in zip(self._tuning, notes) ]

		if len(notes) != notes.count(None) or is_rest:
			# New note starts
			self._flush_current_note()
			self.parse_decorations(decorations)
			self._notes = tuple(notes)
			self._note_len = self._duration
		else:
			# Note continues
			self.parse_decorations(decorations)
			self._note_len += self._duration

	def parse(self, s):
		'''Categorize the line and handle any error reporting.'''
		self._lineno += 1
		barline = self.RE_BARLINE.match(s)
		if None != barline:
			# Handle the special case of titles (meaning the barline is a actually
			# an underline
			if (barline.group(2) == '' and self.prev_line != None):
				self.parse_keypair("title", self.prev_line)
				self.prev_line = None
				return

			self._flush_prev_line()
			self.parse_barline(s)
			return

		self._flush_prev_line()

		comment = self.RE_COMMENT.match(s)
		if None != comment:
			self.format_attribute('comment', comment.group(1))
			return

		keypair = self.RE_KEYPAIR.match(s)
		if None != keypair:
			self.parse_keypair(keypair.group(1), keypair.group(2))
			return

		note = self.RE_NOTE.match(s)
		if None != note:
			self.parse_note(s)
			return

		if s.strip() != '': # not whitespace
			self.prev_line = s

	def _flush_current_note(self):
		if 0 != self._note_len:
			self.format_note(self._notes, self._note_len)
			self._note_len = Fraction(0, 1)
			self._notes = None

	def _flush_prev_line(self):
		if self.prev_line != None:
			self.format_attribute("error", "Cannot parse '%s' at line %d" %
					(self.prev_line, self._lineno-1))
			self.prev_line = None

	def flush(self):
		self._flush_current_note()
		self._flush_prev_line()

	def parse_file(self, f):
		for ln in f.readlines():
			self.parse(ln.rstrip())
		self.flush()
		for formatter in self.formatters:
			formatter.flush()