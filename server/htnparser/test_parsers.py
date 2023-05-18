import time

from modular_parser import ModularHTNParser
from test_table import TEST_TABLE

# local_model = 'EleutherAI/gpt-neox-20b'
local_model = None

parsers = [('modular', ModularHTNParser(local_model=local_model))]

for (parser_name, parser) in parsers:
	succeeded = 0
	print('testing parser "%s":' % (parser_name,))

	for i in range(len(TEST_TABLE)):
		tc = TEST_TABLE[i]

		(test_name, kas, inp, want_decomp, want_mapped) = tc

		t0 = time.time()
		(got_decomp, got_mapped, got_new) = parser.get_actions(kas, inp, clarify_hook=None)
		t1 = time.time()

		continue_outer = False

		print('(%d / %d) [%.2f secs] test "%s" ' % (i+1, len(TEST_TABLE), t1-t0, test_name), end='')

		if len(got_decomp) != len(want_decomp):
			print('failed:\n\tgot %d parsed action predicates, but wanted %d' % (len(got_decomp), len(want_decomp)))
			continue
		elif len(got_mapped) != len(want_mapped):
			print('failed:\n\tgot %d mapped action predicates, but wanted %d' % (len(got_mapped), len(want_mapped)))
			continue

		for j in range(len(got_decomp)):
			if got_decomp[j] != want_decomp[j]:
				print('failed:\n\twanted decomposed action %s, but got %s' % (want_decomp[j], got_decomp[j]))
				continue_outer = True
				break
		if continue_outer:
			continue

		for j in range(len(got_mapped)):
			if got_mapped[j] != want_mapped[j]:
				print('failed:\n\twanted mapped action %s, but got %s' % (want_mapped[j], got_mapped[j]))
				continue_outer = True
				break
		if continue_outer:
			continue

		print('passed!')

		succeeded += 1

	print('\n%d / %d test%s passed' % (succeeded, len(TEST_TABLE), 's' if len(TEST_TABLE) != 1 else ''))

	print('=================\n')
