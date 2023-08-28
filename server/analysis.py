import csv
import os
import quant
import re
import subprocess

import numpy as np

from collections import defaultdict
from scipy import stats

P_THRESH = 0.06

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
		(false_pos_rate, false_neg_rate, f1) = quant.get_paraphrase_scores(d)
		participants[pid]['paraphrase_false_pos_rate'] = false_pos_rate
		participants[pid]['paraphrase_false_neg_rate'] = false_neg_rate
		participants[pid]['paraphrase_f1'] = f1

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

		tst_fn = stats.ttest_ind
		#if 'survey' in key:
		#	tst_fn = stats.mannwhitneyu

		tst = tst_fn(group1, group2)

		if tst.pvalue <= P_THRESH:
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

		tst_fn = stats.ttest_ind
		#if 'survey' in key:
		#	tst_fn = stats.mannwhitneyu

		tst = tst_fn(group1, group2)
		if tst.pvalue > P_THRESH:
			comp = 'HIGHER' if tst.statistic < 0 else 'LOWER'
			print('%s: %s @ %.3f' % (key, comp, tst.pvalue))

	print('\n========\n')

	for key in sorted(all_keys):
		if 'survey' not in key:
			scores = [participants[i][key] for i in range(1, 13)]
			print('%s: %.2f' % (key, sum(scores)*1.0/len(scores)))

	print('\n========\n')

	for cls in [x.split('_')[0] for x in all_keys if 'GPT_succ' in x]:
		turbo_yeses = 0
		turbo_nos = 0
		for pid in range(1, 8):
			uuid = subprocess.run(['bash', '-c', 'ls session%d*'%pid], capture_output=True).stdout.decode('utf-8').strip().split('\n')[-1]
			d = 'session%d_demo_logs/%s' % (pid, uuid)
			scores = quant.get_scores(d, all_scores=True)
			turbo_yeses += sum(scores[cls])
			turbo_nos += len(scores[cls])-sum(scores[cls])

		four_yeses = 0
		four_nos = 0
		for pid in range(8, 13):
			uuid = subprocess.run(['bash', '-c', 'ls session%d*'%pid], capture_output=True).stdout.decode('utf-8').strip().split('\n')[-1]
			d = 'session%d_demo_logs/%s' % (pid, uuid)
			scores = quant.get_scores(d, all_scores=True)
			four_yeses += sum(scores[cls])
			four_nos += len(scores[cls])-sum(scores[cls])

		print('%s: %s' % (cls, stats.chi2_contingency([[turbo_yeses, four_yeses], [turbo_nos, four_nos]]).pvalue))


	print('\n========\n')

	(fp3, fn3, tp3, tn3) = (0, 0, 0, 0)
	(fp4, fn4, tp4, tn4) = (0, 0, 0, 0)

	for pid in range(1, 8):
		uuid = subprocess.run(['bash', '-c', 'ls session%d*'%pid], capture_output=True).stdout.decode('utf-8').strip().split('\n')[-1]
		d = 'session%d_demo_logs/%s' % (pid, uuid)
		(nfp3, nfn3, ntp3, ntn3) = quant.get_paraphrase_scores(d, all_scores=True)
		fp3 += nfp3
		fn3 += nfn3
		tp3 += ntp3
		tn3 += ntn3

	for pid in range(8, 13):
		uuid = subprocess.run(['bash', '-c', 'ls session%d*'%pid], capture_output=True).stdout.decode('utf-8').strip().split('\n')[-1]
		d = 'session%d_demo_logs/%s' % (pid, uuid)
		(nfp4, nfn4, ntp4, ntn4) = quant.get_paraphrase_scores(d, all_scores=True)
		fp4 += nfp4
		fn4 += nfn4
		tp4 += ntp4
		tn4 += ntn4

	print(fp3, fn3, tp3, tn3)
	print(fp4, fn4, tp4, tn4)
	print('gpt-3.5-turbo FP rate: %.2f' % (fp3*1.0/(fp3+tn3)))
	print('gpt-3.5-turbo FN rate: %.2f' % (fn3*1.0/(fn3+tp3)))
	print('gpt-4 FP rate: %.2f' % (fp4*1.0/(fp4+tn4)))
	print('gpt-4 FN rate: %.2f' % (fn4*1.0/(fn4+tp4)))

	print('total TP rate: %.2f' % ((tp3+tp4)*1.0/((tp3+tp4)+(fn3+fn4)),))
	print('total TN rate: %.2f' % ((tn3+tn4)*1.0/((tn3+tn4)+(fp3+fp4)),))

	print('FP rate: %s' % (stats.chi2_contingency([[fp3, fp4], [fp3+tn3, fp4+tn3]]),))
	print('FN rate: %s' % (stats.chi2_contingency([[fn3, fn4], [fn3+tp3, fn4+tp4]]),))
