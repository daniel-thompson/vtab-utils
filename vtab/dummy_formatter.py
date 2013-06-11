class DummyFormatter(object):
	def __getattr__(self, name):
		def dump_args(*args, **kwargs):
			if 0 == len(kwargs):
				print('%s%s' % (name, args))
			else:
				print('%s%s%s' % (name, args, kwargs))
		return dump_args
