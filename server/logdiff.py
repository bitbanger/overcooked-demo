import os
import os.path
import sys

def read(fn):
	ret = None
	with open(fn, 'r') as f:
		ret = f.read().strip()

	return ret

def lines(f):
	return [x.strip() for x in f.strip().split('\n')]

# assumption: fn2 comes chronologically later
def diff(fn1, fn2):
	(f1, f2) = (read(fn1), read(fn2))
	(l1, l2) = (lines(f1), lines(f2))

	dif = []
	started_diff = False
	for i in range(len(l1)):
		if len(l2) <= i or l1[i] != l2[i]:
			if not started_diff and i > 0:
				if '<option value' in l1[i-1] or '<radio' in l1[i-1] or '<button' in l1[i-1]:
					dif.append(l1[i-1])
			started_diff = True
			dif.append(l1[i])

	return dif

def take_diffs(dir_name, verbose=False):
	files = os.listdir(dir_name.strip())

	undos = [fn for fn in files if 'undo' in fn and fn[0] != '.']
	undo_nums = sorted([int(fn[9:-4]) for fn in undos])
	# undos = ['%s/log_undo_%d.txt'%('/'.join(dir_name.split('/')[:-1]), n) for n in undo_nums]
	undos = [os.path.join(dir_name, 'log_undo_%d.txt'%n) for n in undo_nums]

	# undos.append('%s/log.txt'%('/'.join(dir_name.split('/')[:-1])))
	undos.append(os.path.join(dir_name, 'log.txt'))

	undo_txts = []
	for undo in undos:
		undo_txts.append(lines(read(undo)))

	indexed_diffs = []

	if len(undo_txts) > 1:
		undo_base = 0
		for i in range(len(undo_txts)-1):
			if read(undos[i+1]) in read(undos[undo_base]):
				if verbose:
					print('SQUASH')
				continue
			if verbose:
				print(undo_base, i+1)
			d = diff(undos[undo_base], undos[i+1])
			# print('\n\nDIFF at line %d:' % (len(lines(read(undos[undo_base])))-len(d)))
			diff_line_num = len(lines(read(undos[undo_base])))-len(d)
			if verbose:
				for dl in d:
					print('\t---%s'%dl)
			indexed_diffs.append((diff_line_num, '\n'.join(d)))

			new_ids = []
			for idd in indexed_diffs:
				if idd[0] > diff_line_num:
					continue
				new_ids.append(idd)
			indexed_diffs = new_ids

			# for line in d:
				# print('\t%s' % (line,))
			# print('\n\n')
			if verbose:
				print('\t%s' % (diff_line_num))
				print('\t%s %s' % (undos[undo_base], undos[i+1]))
			# if len(d) > 6:
				# print(read(undos[undo_base]))
				# quit()
			undo_base = i+1

	return indexed_diffs

if __name__ == '__main__':
	take_diffs(sys.argv[1], verbose=True)
