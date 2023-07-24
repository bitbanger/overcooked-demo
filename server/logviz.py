import os
import os.path
import sys

from collections import defaultdict

from logdiff import take_diffs

letter_to_class = {
	'Y': 'msger-yes-btn',
	'N': 'msger-no-btn',
	'M': 'msger-maybe-btn',
}

VAL_MSG = ''
with open('leftmsgtemplate.html', 'r') as f:
	VAL_MSG = f.read().strip()

USR_MSG = ''
with open('rightmsgtemplate.html', 'r') as f:
	USR_MSG = f.read().strip()

PAGE = ''
with open('logtemplate.html', 'r') as f:
	PAGE = f.read().strip()

log = []
with open(os.path.join(sys.argv[1].strip(), 'log.txt'), 'r') as f:
	log = [x.strip() for x in f.read().strip().split('\n')]

idiffs = take_diffs(sys.argv[1])
# print(idiffs)

idiff_map = defaultdict(list)
for (ln, diff) in idiffs:
	idiff_map[ln].append(diff.split('\n'))
	# print(ln, diff.split('\n'))
# quit()

augmented_log = []
for i in range(len(log)):
	augmented_log.append(log[i])
	if i in idiff_map:
		for d in idiff_map[i]:
			for dl in d:
				augmented_log.append(dl + ' (DIFF)')
# log = augmented_log

# source: https://stackoverflow.com/questions/35091557/replace-nth-occurrence-of-substring-in-string
def n_repl(s, sub, repl, n=1):
	find = s.find(sub)
	i = find != -1
	while find != -1 and i != n:
		find = s.find(sub, find+1)
		i += 1
	if i == n and i <= len(s.split(sub))-1:
		return s[:find] + repl + s[find+len(sub):]
	return s

diff_insert_map = dict()

def process_modals(log):
	new_log = []
	for l in log:
		user_msg = ': '.join(l.split(': ')[1:]).strip()
		if len(new_log) > 0 and 'radio' in new_log[-1] and 'checked' not in new_log[-1]:
			user_msg = ': '.join(l.split(': ')[1:]).strip()

			# Disable all options
			new_log[-1] = new_log[-1].replace('value="', 'disabled="true" value="')
			# Select and un-disable the right option
			new_log[-1] = new_log[-1].replace('disabled="true" value="%s"'%user_msg, 'value="%s" checked="true"'%user_msg)
		elif user_msg in letter_to_class.keys():
			cls = letter_to_class[user_msg]
			# Disable all buttons
			new_log[-1] = new_log[-1].replace('button class', 'button style="background: gray;" disabled="true" class')
			# Un-disable the right button
			new_log[-1] = new_log[-1].replace('button style="background: gray;" disabled="true" class="%s"'%cls, 'button class="%s"'%cls)
		elif len(new_log) > 0 and 'option value' in new_log[-1] and 'disabled' not in new_log[-1]:
			n = 1
			for opt in user_msg.split():
				new_log[-1] = n_repl(new_log[-1], 'option value="%s"'%opt, 'option value="%s" selected="true"'%opt, n=n)
				new_log[-1] = n_repl(new_log[-1], 'select ', 'select disabled="true"', n=n)
				n += 1
		else:
			if len(user_msg) > 0:
				new_log.append(l)

	return new_log

new_log = []
for i in range(len(log)):
	l = log[i]

	# if 'DIFF' in l:
		# diff_insert_map[len(new_log)-1] = l
		# continue

	user_msg = ': '.join(l.split(': ')[1:]).strip()
	# Handle radio selections
	if len(new_log) > 0 and 'radio' in new_log[-1] and 'checked' not in new_log[-1]:
		# Disable all options
		new_log[-1] = new_log[-1].replace('value="', 'disabled="true" value="')
		# Select and un-disable the right option
		new_log[-1] = new_log[-1].replace('disabled="true" value="%s"'%user_msg, 'value="%s" checked="true"'%user_msg)
	elif user_msg in letter_to_class.keys():
		cls = letter_to_class[user_msg]
		# Disable all buttons
		new_log[-1] = new_log[-1].replace('button class', 'button style="background: gray;" disabled="true" class')
		# Un-disable the right button
		new_log[-1] = new_log[-1].replace('button style="background: gray;" disabled="true" class="%s"'%cls, 'button class="%s"'%cls)
	elif len(new_log) > 0 and 'option value' in new_log[-1] and 'disabled' not in new_log[-1]:
		n = 1
		for opt in user_msg.split():
			new_log[-1] = n_repl(new_log[-1], 'option value="%s"'%opt, 'option value="%s" selected="true"'%opt, n=n)
			new_log[-1] = n_repl(new_log[-1], 'select ', 'select disabled="true"', n=n)
			n += 1
	else:
		if len(user_msg) > 0:
			new_log.append(l)

	diff_insert_map[i] = len(new_log)-1

# for didx in sorted(diff_insert_map.keys(), reverse=True):
	# new_log = new_log[:didx] + [diff_insert_map[didx]] + new_log[didx:]
for didx in sorted(idiff_map.keys(), reverse=True):
	dlines = idiff_map[didx]
	nlidx = diff_insert_map[didx]
	add_chunk = []
	for dlgroup in dlines:
		add_chunk.append('User: START DIFF')
		for l in dlgroup:
			add_chunk.append(l)
		add_chunk.append('User: END DIFF')
	# for dlgroup in dlines:
	new_log = new_log[:nlidx] + add_chunk + new_log[nlidx:]

new_new_log = []
chunk_buf = []
in_diff = False
for l in new_log:
	if 'START DIFF' in l:
		# CSS adapted from: https://stackoverflow.com/questions/53814625/adding-transparent-overlay-to-div
		new_new_log.append('<center><small><strong>REMOVED:</strong></small></center><div style="position:relative; margin-bottom: 10px; padding-top: 5px; padding-bottom: 5px;"><div style="position:absolute; top:0px; left:0px; background: repeating-linear-gradient( 45deg, rgba(176, 190, 197, 0.3), rgba(176, 190, 197, 0.3) 5px, rgba(120, 144, 156, 0.3) 5px, rgba(120, 144, 156, 0.3) 10px ); width: 100%; height: 100%; z-index: 2; border-radius: 5px;"></div>')
		in_diff = True
	elif 'END DIFF' in l:
		# new_new_log.append('\n'.join(process_modals(chunk_buf)))
		for nl in process_modals(chunk_buf):
			new_new_log.append(nl)
		chunk_buf = []
		new_new_log.append('</div>')
		in_diff = False
	else:
		if in_diff:
			chunk_buf.append(l)
		else:
			new_new_log.append(l)
# new_log = new_new_log
# new_log = [(x.split(': ')[0], ': '.join(x.split(': ')[1:])) for x in new_log]
# new_log = [VAL_MSG%x[1] if x[0] == 'VAL' else USR_MSG%x[1] for x in new_log]
new_log = []
for line in new_new_log:
	if line[0] == '<':
		new_log.append(line)
		continue

	tag = line.split(': ')[0].strip()
	line = ': '.join(line.split(': ')[1:])
	if tag == 'VAL':
		line = VAL_MSG%line
	else:
		line = USR_MSG%line

	new_log.append(line)

print(PAGE%('\n'.join(new_log)))
