import re, unittest, sys
from vtab import tunings

class AsciiFormatter(object):
	LINE_LENGTH = 80

	def __init__(self):
		self.f = sys.stdout
		self._staff_lines = ()
		self._comments = []
		self._pad = False

		self.set_tuning(tunings.STANDARD_TUNING)

	def set_file(self, f):
		self.f = f

	def set_tuning(self, tuning):
		self.flush()
		self._tuning = tuning

		staff_lines = []
		for dummy in self._tuning:
			staff_lines.append([])
		self._staff_lines = tuple(staff_lines)

	def format_attribute(self, key, value):
		try:
			fn = getattr(self, 'format_' + key)
		except:
			fn = None
		if None != fn:
			fn(value)
		else:
			self.flush()
			self.f.write("ERROR: Unsupported attribute (%s: '%s')\n" % (key, value))

	def format_comment(self, comment):
		comment = '# %s\n' % (comment)
		if len(self._staff_lines[0]) == 0:
			self.f.write(comment)
		else:
			self._comments.append(comment)

	def format_duration(self, unused):
		# For asciitab the duration is not important
		pass

	def format_key(self, unused):
		# For tab only output the key is not important
		pass

	def format_time(self, unused):
		# For tab only output the timing is not important
		pass

	def format_text(self, unused):
		# TODO: Over-text is useful for tab but requires quite
		# a lot of effort for, for now, this is not implemented.
		pass

	def format_title(self, title):
		self.f.write(title + '\n')
		self.f.write(('=' * len(title)) + '\n')
		self.f.write('\n')

	def format_composer(self, composer):
		self.f.write('Composer: %s\n' % composer)
		self._pad = True

	def format_barline(self, unused):
		width = len(''.join(self._staff_lines[0])) + 2
		if width >= self.LINE_LENGTH:
			self.flush()
			width = 0

		for s in self._staff_lines:
			if len(s) == 0:
				s.append('|')
			else:
				s.append('-|')

		if width >= self.LINE_LENGTH - 16:
			self.flush()
			self.format_barline(unused)

	def format_note(self, notes, duration, tie):
		frets = []
		for note, tuning in zip(notes, self._tuning):
			if note == None or tie:
				frets.append('')
			else:
				fret = int(note - tuning)
				frets.append(str(fret))
		width = max([ len(fret) for fret in frets ]) + 1
		if len(''.join(self._staff_lines[0])) + width >= self.LINE_LENGTH:
			self.flush()
		for line, fret in zip(self._staff_lines, frets):
			padding = width - len(fret)
			line.append(('-' * padding) + fret)

	def flush(self):
		if self._pad:
			self.f.write('\n')
			self._pad = False

		issue_seperator = False
		if len(self._staff_lines) > 0 and len(self._staff_lines[0]) > 0:
			lastline = None
			for s in reversed(self._staff_lines):
				line = ''.join(s) + '\n'
				self.f.write(line)
				del s[:]

				# Check that all staff lines are the same length
				assert(lastline == None or len(line) == len(lastline))
				lastline = line
			issue_seperator = True
		for c in self._comments:
			self.f.write(c)
		del self._comments[:]
		if issue_seperator:
			self.f.write('\n')
