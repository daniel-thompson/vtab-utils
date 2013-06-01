class DummyFormatter(object):
	def __getattr__(self, name):
		def dump_args(*args, **kwargs):
			print(name)
			print(args)
			print(kwargs)
		return dump_args
