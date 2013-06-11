import re

class VtabParser():
	'''Match a key-value pair, yeilding key and value
	Template is: "Key : Value"'''
	RE_KEYPAIR = re.compile(r'\s*(\w+)\s*:\s*(.*)$')

	'''Match a barline (or underline), yielding barline and decoration
	Template is: "============ <decoration>"'''
	RE_BARLINE = re.compile(r'\s*([-=]{4}[-=]*)\s*(.*)$')

	def __init__(self):
		self.formatters = []

	def add_formatter(self, formatter):
		if not formatter in self.formatters:
			self.formatters += formatter,

	def remove_formatter(self, formatter):
		self.formatters.remove(formatter)

	def format_attribute(self, key, value):
		for formatter in self.formatters:
			formatter.format_attribute(key, value)

	def parse_keypair(self, key, value):
		self.format_attribute(key, value)

	def parse_decoration(self, decoration):
		pass

	def parse_barline(self, line):
		pass

	def parse_note(self, note):
		pass

	def parse(self, s):
		'''Categorize the line and handle any error reporting.'''
		keypair = self.RE_KEYPAIR.match(s)
		if None != keypair:
			self.parse_keypair(keypair.group(1), keypair.group(2))
			return
		barline = self.RE_BARLINE.match(s)
		if None != barline:
			self.parse_decoration(barline.group(2))
			self.parse_barline(barline.group(1))
