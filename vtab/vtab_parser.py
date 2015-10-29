

import shlex
import re
import sys
import traceback

from fractions import Fraction
from vtab import tunings
import vtab.note

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
	RE_NOTE = re.compile(r'^\s*[hp\-]*[|:0-9]+[\-]*\s+[hp\-]*[|:0-9]+[\-]*\s+[hp\-]*[|:0-9]+[\-]*\s+[hp\-]*[|:0-9]+[\-]*')

	def __init__(self):
		self.formatters = []
		self.prev_line = None

		self._tuning = tunings.STANDARD_TUNING
		self._notes = (None,) * len(self._tuning)

		self._lineno = 0
		self._barno = 0
		self._duration = Fraction(1, 4)
		self._note_len = Fraction(0, 1)
		self._tied_note = False

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

	def format_note(self, note, duration, tied):
		for formatter in self.formatters:
			formatter.format_note(note, duration, tied)

	def parse_keypair(self, key, value):
		lookup  = {
			'a' : 'articulation',
			't' : 'text',
		}
		key = key.lower()
		if key in lookup:
			key = lookup[key]
		self.format_attribute(key, value)

	def parse_decorations(self, decorations):
		for token in decorations:
			if token[0].isdigit():
				self._duration = Fraction(1, int(token))
				self.format_attribute('duration', self._duration)
				continue

			keypair = self.RE_KEYPAIR.match(token)
			if None != keypair:
				self.parse_keypair(keypair.group(1), keypair.group(2))
				continue

			# else
			self.format_attribute('lyric', token)

	def parse_barline(self, line):
		self._flush_current_note(new_bar=(self._barno >= 1))
		self._barno += 1

		tokens = shlex.split(line)
		self.parse_decorations(tokens[1:])

		properties = {}

		barline = tokens[0]
		num_special = min(2, int(len(barline) / 2))
		prefix = barline[:num_special]
		postfix = barline[-num_special:]

		if '=' in barline:
			properties['double'] = 'plain'

		if ':' in prefix:
			properties['repeat'] = 'close'
		if ':' in postfix:
			if 'repeat' in properties:
				properties['repeat'] = 'both'
			else:
				properties['repeat'] = 'open'

		if '|' in prefix:
			properties['double'] = 'left'
		if '|' in prefix:
			if 'double' in properties and properties['double'] == 'left':
				properties['double'] = 'both'
			else:
				properties['double'] = 'right'

		self.format_barline(properties)

	def parse_note(self, note):
		notes = shlex.split(note)
		decorations = notes[len(self._tuning):]

		def parse_string(open_string, fret):
			try:
				articulation = fret
				fret = fret.lstrip('hp-')
				articulation = articulation.replace(fret, '')
				fret = fret.rstrip('-') # Fake voice support
				note = open_string + int(fret)
				if 'h' in articulation:
					note.add_articulation(vtab.note.HAMMER_ON)
				if 'p' in articulation:
					note.add_articulation(vtab.note.PULL_OFF)
				return note
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

	def _flush_current_note(self, new_bar=False):
		if 0 != self._note_len:
			if None == self._notes:
				self._notes = (None,) * len(self._tuning)
			self.format_note(self._notes, self._note_len, self._tied_note)
			self._note_len = Fraction(0, 1)
			if not new_bar:
				self._notes = (None,) * len(self._tuning)
		self._tied_note = new_bar

	def _flush_prev_line(self):
		if self.prev_line != None:
			self.format_attribute("error", "Cannot parse '%s' at line %d" %
					(self.prev_line, self._lineno-1))
			self.prev_line = None

	def flush(self):
		self._flush_current_note()
		self._flush_prev_line()

	def parse_file(self, f):
		num_errors = 0
		(self._lineno, saved_lineno) = (0, self._lineno)
		for ln in f.readlines():
			try:
				self.parse(ln.rstrip())
			except:
				print('%s:%d:%d: Internal error (please file a bug report)' %
						(f.name, self._lineno, 0), file=sys.stderr)
				num_errors += 1
				traceback.print_exc(file=sys.stderr)

		self.flush()
		for formatter in self.formatters:
			formatter.flush()
		self._lineno = saved_lineno

		return num_errors
