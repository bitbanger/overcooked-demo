import os
import os.path
import sys

from collections import defaultdict
from logdiff import read, lines

def classify_modal(line):
	d = {
		'I wasn\'t able to identify a known action for the command': 'confirm_no_good_action',
		'These are the individual steps of your command, right?': 'segmentGPT',
		'Sorry, but I wasn\'t able to figure out what object': 'args_too_hard1',
		'is the action': 'mapGPT',
		'OK, and the object': 'groundGPT',
		'I\'m not sure what to put in them': 'args_too_hard2',
		'I think these are the objects of': 'argChoiceGPT',
	}

	for snippet in d.keys():
		if snippet in line:
			return d[snippet]

	return None

def msg_points(log, msg_idx):
	msg = log[msg_idx]
	cls = classify_modal(msg)
	if cls is None:
		return 0

	if cls == 'mapGPT':
		print(log[msg_idx+1])
		

def is_modal(line):
	return '"radio' in line or '<button' in line or '<select' in line

def get_scores(d):
	# log_lines = lines(read(os.path.join(sys.argv[1], 'log.txt')))
	log_lines = lines(read(os.path.join(d, 'log.txt')))

	scores = defaultdict(int)
	totals = defaultdict(int)

	for i in range(len(log_lines)):
		line = log_lines[i]
		if i > 0 and line[:4] == 'User' and is_modal(log_lines[i-1]):
			cls = classify_modal(log_lines[i-1])
			if cls is not None:
				# print(classify_modal(log_lines[i-1]), line)
				if 'args_too_hard' in cls:
					totals['groundGPT'] += 1
				elif cls == 'confirm_no_good_action':
					totals['mapGPT'] += 1
					if line == 'User: N':
						scores['mapGPT'] += 1
				elif line == 'User: Y':
					scores[cls] += 1
					totals[cls] += 1
				else:
					totals[cls] += 1

	res = dict()
	for cls in sorted(scores.keys()):
		res[cls] = scores[cls]*1.0/totals[cls]

	return res
