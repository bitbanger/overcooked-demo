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

def merge_diffs(dir_name):
	files = os.listdir(dir_name.strip())
	undos = [fn for fn in files if 'undo' in fn and fn[0] != '.']
	undo_nums = sorted([int(fn[9:-4]) for fn in undos])
	undo_fns = [os.path.join(dir_name, 'log_undo_%d.txt'%n) for n in undo_nums]
	# print(undo_fns)
	undo_fns.append(os.path.join(dir_name, 'log.txt'))

	if len(undo_fns) == 1:
		return lines(read(undo_fns[0]))

	undo_files = [lines(read(fn)) for fn in undo_fns]
	final_file = [(-1, line) for line in undo_files[0]]

	r_idx = 0
	# print(undo_fns[1:])
	for f_idx in range(len(undo_files[1:])):
		f = undo_files[1:][f_idx]
		# print('file has %d lines' % (len(f)))

		# Get the lines in the current file that were removed
		curr_lines = [l[1] for l in final_file if l[0] == -1]
		# print('%d curr lines' % (len(curr_lines)))
		curr_line_real_idcs = [i for i in range(len(final_file)) if final_file[i][0] == -1]
		diverged_idx = None
		removed_lines = []
		removed_this_iter = 0
		for i in range(len(curr_lines)):
			if (len(f) <= i or f[i] != curr_lines[i]) and diverged_idx is None:
				diverged_idx = i
			if diverged_idx is not None:
				removed_this_iter += 1
				removed_lines.append(curr_lines[i])
				# Set the line as having been removed by this index
				final_file[curr_line_real_idcs[i]] = (r_idx, curr_lines[i])
		# print('diff removed %d lines' % removed_this_iter)

		# Add the lines in the new file that came afterward
		if len(f) > len(curr_lines) and diverged_idx is None:
			diverged_idx = len(curr_lines)
		if diverged_idx is not None:
			# print('adding %d new lines from %s' % (len(f[diverged_idx:]), undo_fns[1:][f_idx]))
			if len(f[diverged_idx:]) > 0:
				for new_line in f[diverged_idx:]:
					final_file.append((-1, new_line))
				# Increment the removal index, as adding
				# lines ends any "squashing" of removals
				r_idx += 1

	return final_file

if __name__ == '__main__':
	# take_diffs(sys.argv[1], verbose=True)
	for line in merge_diffs(sys.argv[1]):
		if line[0] != -1:
			print('%s\tREMOVED BY %d' % (line[1], line[0]))
			pass
		else:
			print('%s' % (line[1],))
			pass
