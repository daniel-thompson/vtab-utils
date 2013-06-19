import re

class VtabParser():
	'''Match a barline (or underline), yielding barline and decoration
	Template is: "============ <decoration>"'''
	RE_BARLINE = re.compile(r'^\s*([-=]{4}[-=]*)\s*(.*)$')

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
	RE_NOTE = re.compile(r'^\s*[|0-9]+\s+[|0-9]+\s+[|0-9]+\s+[|0-9]+')


	def __init__(self):
		self.formatters = []
		self.prev_line = None

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

	def format_note(self, note):
		for formatter in self.formatters:
			formatter.format_note(note)

	def parse_keypair(self, key, value):
		key = key.lower()
		self.format_attribute(key, value)

	def parse_decoration(self, decoration):
		pass

	def parse_barline(self, line):
		self.format_barline(line)

	def parse_note(self, note):
		self.format_note(note)

	def parse(self, s):
		'''Categorize the line and handle any error reporting.'''
		barline = self.RE_BARLINE.match(s)
		if None != barline:
			# Handle the special case of titles (meaning the barline is a actually
			# an underline
			if (barline.group(2) == '' and self.prev_line != None):
				self.parse_keypair("title", self.prev_line)
				self.prev_line = None
				return
			
			self.flush()
			self.parse_decoration(barline.group(2))
			self.parse_barline(barline.group(1))
			return
		
		self.flush()
		
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

	def flush(self):
		if self.prev_line != None:
			self.format_attribute("error", self.prev_line)
			self.prev_line = None

	def parse_file(self, f):
		for ln in f.readlines():
			self.parse(ln.rstrip())
		self.flush()
