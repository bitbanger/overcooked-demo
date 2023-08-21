import os
import os.path
import re
import sys

from collections import defaultdict
from logdiff import read, lines

from htnparser.chat_parser import ChatParser

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

def get_paraphrase_scores(d):
	false_pos = 0
	false_neg = 0
	paraphrase_count = 0

	log_lines = lines(read(os.path.join(d, 'log.txt')))

	session_num = int(re.findall('session(\d*)_', d)[0])

	gpt_model = 'gpt-3.5-turbo'
	if session_num > 7:
		gpt_model = 'gpt-4'
	chat_parser = ChatParser(gpt_model_override=gpt_model, confirm_gpt=False)

	known_actions = ['moveTo(<arg1>) - a learned action', 'pressSpace() - a learned action']

	for i in range(len(log_lines)):
		line = log_lines[i]

		# First, add any known actions that may be learned here
		if line == 'User: N':
			if 'I think these are the objects of' in log_lines[i-1]:
				codes = re.findall('<code>(.*?)</code>', log_lines[i-1])
				pred = codes[0]
				args = log_lines[i+2].split(' ')[1:]
				known_actions.append('%s(%s) - a learned action' % (pred, ', '.join(['<arg%d>'%j for j in range(1,len(args)+1)])))
		elif line == 'User: Y':
			if 'I think these are the objects of' in log_lines[i-1]:
				codes = re.findall('<code>([^<]*)</code>', log_lines[i-1])
				pred = codes[0]
				args = codes[1:]
				known_actions.append('%s(%s) - a learned action' % (pred, ', '.join(['arg%d'%j for j in range(1,len(args)+1)])))

		# Then, check to see if mapGPT was invoked, pick args, and check the paraphrase
		try:
			if 'is the action' in line:
				phrase = re.findall('<i>(.*?)</i>', line)[0]
				action = re.findall('<code>(.*?)</code>', line)[0]
				grounded = chat_parser.ground_action(known_actions, [], phrase)
				paraphrase = (grounded != 'noGoodAction')
				user_oks = (log_lines[i+1] == 'User: Y')
				paraphrase_count += 1
				if paraphrase and (not user_oks):
					false_pos += 1
				if (not paraphrase) and user_oks:
					false_neg += 1
		except TypeError:
			# the parser tried to ask for a correction, but
			# we're just trying to figure out if the paraphraser
			# works, and we know that it won't even run now
			pass

	false_pos_rate = false_pos*1.0/paraphrase_count
	false_neg_rate = false_neg*1.0/paraphrase_count

	return (false_pos_rate, false_neg_rate)

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

	for i in range(len(log_lines)):
		line = log_lines[i]

	res = dict()
	for cls in sorted(scores.keys()):
		res[cls] = scores[cls]*1.0/totals[cls]

	return res
