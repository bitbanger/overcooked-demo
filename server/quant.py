import os
import os.path
import sys

from logdiff import read, lines

def classify_modal(line):
	d = {
		'I wasn\'t able to identify a known action for the command': 'confirm_no_good_action',
		'These are the individual steps of your command, right?': 'confirm_segments',
		'Sorry, but I wasn\'t able to figure out what object': 'args_too_hard1',
		'is the action': 'confirm_guessed_action',
		'OK, and the object': 'confirm_guessed_args',
		'I\'m not sure what to put in them': 'args_too_hard2',
		'I think these are the objects of': 'confirm_new_args',
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

	if cls == 'confirm_guessed_action':
		print(log[msg_idx+1])
		

def is_modal(line):
	return '"radio' in line or '<button' in line or '<select' in line

if __name__ == '__main__':
	log_lines = lines(read(os.path.join(sys.argv[1], 'log.txt')))

	for i in range(len(log_lines)):
		line = log_lines[i]
		if i > 0 and line[:4] == 'User' and is_modal(log_lines[i-1]):
			print(line)
