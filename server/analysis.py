import csv
import os
import quant
import re
import subprocess

import numpy as np

from collections import defaultdict
from scipy import stats

def count_undos(participants):
	undo_counts = [int(x.strip()) for x in subprocess.run(['/usr/bin/env', 'bash', '-c', 'for i in $(seq 1 12); do ls session${i}*/*/*undo* | wc -l; done'], capture_output=True).stdout.decode('utf-8').strip().split('\n')]
	for i in range(len(undo_counts)):
		participants[i+1]['undo_count'] = int(undo_counts[i])

def count_scolds(participants):
	scold_counts = [int(x.strip()) for x in subprocess.run(['/usr/bin/env', 'bash', '-c', 'for i in $(seq 1 12); do grep "EVENT: scold" session${i}*/*/replay_events | wc -l; done'], capture_output=True).stdout.decode('utf-8').strip().split('\n')]
	for i in range(len(scold_counts)):
		participants[i+1]['scold_count'] = int(scold_counts[i])

def count_crashes(participants):
	crash_counts = [int(x.strip()) for x in subprocess.run(['/usr/bin/env', 'bash', '-c', 'for i in $(seq 1 12); do grep "EVENT: crash" session${i}*/*/replay_events | wc -l; done'], capture_output=True).stdout.decode('utf-8').strip().split('\n')]
	for i in range(len(crash_counts)):
		participants[i+1]['crash_count'] = int(crash_counts[i])

def count_messages(participants):
	msg_counts = [int(x.strip()) for x in subprocess.run(['/usr/bin/env', 'bash', '-c', 'for i in $(seq 1 12); do grep "User:" session${i}*/*/log.txt | wc -l; done'], capture_output=True).stdout.decode('utf-8').strip().split('\n')]
	for i in range(len(msg_counts)):
		participants[i+1]['msg_count'] = int(msg_counts[i])

def count_milestones(participants):
	new_event_names = {
		'pickUp onion': '1. pickUp',
		'put onion pot': '2. put',
		'turnOn pot': '3. turnOn',
		'plate soup': '4. plate',
		'bring soup dropoff': '5. deliver',
	}

	lines = subprocess.run(['/usr/bin/env', 'bash', '-c', 'grep EVENT session*/*/replay*'], capture_output=True).stdout.decode('utf-8').strip().split('\n')

	for line in lines:
		session = int(re.findall('session(\d*)_', line.strip())[0])
		event = re.findall('EVENT: (.*)$', line.strip())[0]
		if event not in new_event_names.keys():
			continue
		event_num = int(new_event_names[event].split('.')[0])

		participants[session]['furthest'] = max(participants[session]['furthest'], event_num)

def count_survey(participants):
	reader = None
	with open('val.csv', 'r') as f:
		reader = csv.reader(f)
		labels = next(reader)
		q_txt = [x.split(' - ')[-1] for x in next(reader)[20:30]]
		next(reader) # Skip JSON stuff
		next(reader) # Skip pilot session with participant 1
		pid = 0
		for row in reader:
			pid += 1
			for i in range(len(row)):
				if labels[i][:2] == 'Q4':
					qnum = labels[i].split('_')[1]
					if row[i] != 'N/A':
						participants[pid]['survey_q4_p%s'%qnum] = int(row[i])

		return q_txt

def count_norm_msgs(participants):
	for pid in participants.keys():
		if participants[pid]['furthest'] > 0:
			participants[pid]['norm_msg_count'] = participants[pid]['msg_count']*1.0/participants[pid]['furthest']

def count_gpt_success_rates(participants):
	for pid in participants.keys():
		uuid = subprocess.run(['bash', '-c', 'ls session%d*'%pid], capture_output=True).stdout.decode('utf-8').strip().split('\n')[-1]
		d = 'session%d_demo_logs/%s' % (pid, uuid)
		scores = quant.get_scores(d)
		for comp in scores:
			participants[pid]['%s_success_rate'%comp] = scores[comp]

def count_paraphrase_error_rates(participants):
	for pid in participants.keys():
		uuid = subprocess.run(['bash', '-c', 'ls session%d*'%pid], capture_output=True).stdout.decode('utf-8').strip().split('\n')[-1]
		d = 'session%d_demo_logs/%s' % (pid, uuid)
		(false_pos_rate, false_neg_rate) = quant.get_paraphrase_scores(d)
		participants[pid]['paraphrase_false_pos_rate'] = false_pos_rate
		participants[pid]['paraphrase_false_neg_rate'] = false_neg_rate

if __name__ == '__main__':
	participants = defaultdict(lambda: defaultdict(int))

	q_txt = count_survey(participants)
	count_milestones(participants)
	count_messages(participants)
	count_undos(participants)
	count_scolds(participants)
	count_crashes(participants)
	count_gpt_success_rates(participants)
	count_paraphrase_error_rates(participants)

	# pass 2
	count_norm_msgs(participants)

	all_keys = set()

	for pid in sorted(participants.keys()):
		# print(pid)
		for key in sorted(participants[pid].keys()):
			all_keys.add(key)
			# print('\t%s: %s' % (key, participants[pid][key]))

	first = True
	for key in all_keys:
		group1 = [participants[i][key] for i in range(1, 8)]
		group2 = [participants[i][key] for i in range(8, 13)]

		tst = stats.ttest_ind(group1, group2)
		if tst.pvalue <= 0.052:
			if not first:
				print('')
			else:
				first = False
			if 'q4' in key:
				q_num = int(key.split('p')[-1])
				key = 'question "%s"' % (q_txt[q_num-1],)
			key = '%s\n\t'%key
			comp = 'HIGHER' if tst.statistic < 0 else 'LOWER'
			print('%s is significantly %s when using GPT-4 (p=%.3f)' % (key, comp, tst.pvalue))

	print('\n========\n')

	for key in all_keys:
		group1 = [participants[i][key] for i in range(1, 8)]
		group2 = [participants[i][key] for i in range(8, 13)]

		tst = stats.ttest_ind(group1, group2)
		if tst.pvalue > 0.052:
			comp = 'HIGHER' if tst.statistic < 0 else 'LOWER'
			print('%s: %s @ %.3f' % (key, comp, tst.pvalue))

	print('\n========\n')

	for key in sorted(all_keys):
		if 'survey' not in key:
			scores = [participants[i][key] for i in range(1, 13)]
			print('%s: %s' % (key, sum(scores)*1.0/len(scores)))
