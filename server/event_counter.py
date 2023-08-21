import os
import re
import subprocess

from collections import defaultdict

new_event_names = {
	'pickUp onion': '1. pickUp',
	'put onion pot': '2. put',
	'turnOn pot': '3. turnOn',
	'plate soup': '4. plate',
	'bring soup dropoff': '5. deliver',
}

lines = subprocess.run(['/usr/bin/env', 'bash', '-c', 'grep EVENT session*/*/replay*'], capture_output=True).stdout.decode('utf-8').strip().split('\n')

user_count_lines = [int(x.strip()) for x in subprocess.run(['/usr/bin/env', 'bash', '-c', 'for i in $(seq 1 12); do grep "User:" session${i}*/*/log.txt | wc -l; done'], capture_output=True).stdout.decode('utf-8').strip().split('\n')]

counts = defaultdict(set)

for line in lines:
	session = int(re.findall('session(\d*)_', line.strip())[0])
	event = re.findall('EVENT: (.*)$', line.strip())[0]

	if event in new_event_names.keys():
		# counts[session][new_event_names[event]] += 1
		counts[new_event_names[event]].add(session)

for event in sorted(counts.keys()):
	print('\t%s: %d' % (event[3:], len(counts[event])))

furthest = defaultdict(int)
for line in lines:
	session = int(re.findall('session(\d*)_', line.strip())[0])
	event = re.findall('EVENT: (.*)$', line.strip())[0]
	if event not in new_event_names.keys():
		continue
	event_num = int(new_event_names[event].split('.')[0])

	furthest[session] = max(furthest[session], event_num)

sep = False
for sid in sorted(furthest.keys()):
	if not sep and sid > 7:
		print('--------')
		sep = True
	print('%d: %d' % (sid, furthest[sid]))
	if furthest[sid] == 5:
		print('\t%d' % (user_count_lines[sid-1],))
