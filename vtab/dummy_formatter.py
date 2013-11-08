from __future__ import print_function
import sys

class DummyFormatter(object):
	def __init__(self):
		self.f = sys.stdout

	def set_file(self, f):
		self.f = f

	def __getattr__(self, name):
		def dump_args(*args, **kwargs):
			if 0 == len(kwargs):
				print('%s%s' % (name, args), file=self.f)
			else:
				print('%s%s%s' % (name, args, kwargs), file=self.f)
		return dump_args
