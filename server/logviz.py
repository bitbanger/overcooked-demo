import os
import os.path
import sys

from collections import defaultdict

from logdiff import take_diffs, merge_diffs

ACTUALLY_PROC_MODALS = False

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
md_lines = merge_diffs(sys.argv[1])
md_kept = [l[1] for l in md_lines if l[0] == -1]
log = [l[1] for l in md_lines]
removal_idcs = [l[0] for l in md_lines]
removal_idx_bounds = dict()
for idx in removal_idcs:
	if idx == -1:
		continue
	idx_occurrences = [i for i in range(len(md_lines)) if md_lines[i][0] == idx]
	if len(idx_occurrences) > 0:
		removal_idx_bounds[idx] = (idx_occurrences[0], idx_occurrences[-1])

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

def process_modals(log):
	new_log = []
	for l in log:
		user_msg = ': '.join(l.split(': ')[1:]).strip()
		if ACTUALLY_PROC_MODALS and len(new_log) > 0 and 'radio' in new_log[-1] and 'checked' not in new_log[-1]:
			user_msg = ': '.join(l.split(': ')[1:]).strip()

			# Disable all options
			new_log[-1] = new_log[-1].replace('value="', 'disabled="true" value="')
			# Select and un-disable the right option
			new_log[-1] = new_log[-1].replace('disabled="true" value="%s"'%user_msg, 'value="%s" checked="true"'%user_msg)
		elif ACTUALLY_PROC_MODALS and user_msg in letter_to_class.keys():
			cls = letter_to_class[user_msg]
			# Disable all buttons
			new_log[-1] = new_log[-1].replace('button class', 'button style="background: gray;" disabled="true" class')
			# Un-disable the right button
			new_log[-1] = new_log[-1].replace('button style="background: gray;" disabled="true" class="%s"'%cls, 'button class="%s"'%cls)
		elif ACTUALLY_PROC_MODALS and len(new_log) > 0 and 'option value' in new_log[-1] and 'disabled' not in new_log[-1]:
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
	if ACTUALLY_PROC_MODALS and len(new_log) > 0 and 'radio' in new_log[-1] and 'checked' not in new_log[-1]:
		# Disable all options
		new_log[-1] = new_log[-1].replace('value="', 'disabled="true" value="')
		# Select and un-disable the right option
		new_log[-1] = new_log[-1].replace('disabled="true" value="%s"'%user_msg, 'value="%s" checked="true"'%user_msg)
	elif ACTUALLY_PROC_MODALS and user_msg in letter_to_class.keys():
		cls = letter_to_class[user_msg]
		# Disable all buttons
		new_log[-1] = new_log[-1].replace('button class', 'button style="background: gray;" disabled="true" class')
		# Un-disable the right button
		new_log[-1] = new_log[-1].replace('button style="background: gray;" disabled="true" class="%s"'%cls, 'button class="%s"'%cls)
	elif ACTUALLY_PROC_MODALS and len(new_log) > 0 and 'option value' in new_log[-1] and 'disabled' not in new_log[-1]:
		n = 1
		for opt in user_msg.split():
			new_log[-1] = n_repl(new_log[-1], 'option value="%s"'%opt, 'option value="%s" selected="true"'%opt, n=n)
			new_log[-1] = n_repl(new_log[-1], 'select ', 'select disabled="true"', n=n)
			n += 1
	else:
		if len(user_msg) > 0:
			new_log.append(l)

'''
new_new_log = []
chunk_buf = []
in_diff = False
for l in new_log:
	if 'START DIFF' in l:
		# CSS adapted from: https://stackoverflow.com/questions/53814625/adding-transparent-overlay-to-div
		# new_new_log.append('<center><small><strong>REMOVED:</strong></small></center><div style="position:relative; margin-bottom: 10px; padding-top: 5px; padding-bottom: 5px;"><div style="position:absolute; top:0px; left:0px; background: repeating-linear-gradient( 45deg, rgba(176, 190, 197, 0.3), rgba(176, 190, 197, 0.3) 5px, rgba(120, 144, 156, 0.3) 5px, rgba(120, 144, 156, 0.3) 10px ); width: 100%; height: 100%; z-index: 2; border-radius: 5px;"></div>')
		new_new_log.append('<div style="display: inline-block; position:relative; margin-bottom: 10px; padding: 5px 5px 5px 5px;"><div style="position:absolute; top:0px; left:0px; background: repeating-linear-gradient( 45deg, rgba(176, 190, 197, 0.3), rgba(176, 190, 197, 0.3) 5px, rgba(120, 144, 156, 0.3) 5px, rgba(120, 144, 156, 0.3) 10px ); width: 100%; height: 100%; z-index: 2; border-radius: 5px;"></div>')
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
'''
new_log = []
removal_depth = 0
for i in range(len(log)):
	line = log[i]

	if line[0] == '<':
		new_log.append(line)
		continue

	tag = line.split(': ')[0].strip()
	line = ': '.join(line.split(': ')[1:])
	if tag == 'VAL':
		line = VAL_MSG%line
	else:
		line = USR_MSG%line

	rgb_str = 'rgba(%d, %d, %d, %.1f)'

	gray0 = rgb_str % (176, 190, 197, 0.3)
	gray1 = rgb_str % (120, 144, 156, 0.3)

	blu0 = rgb_str % (209, 230, 255, 0.3)
	blu1 = rgb_str % (163, 192, 227, 0.3)

	yel0 = rgb_str % (245, 239, 181, 0.3)
	yel1 = rgb_str % (204, 197, 131, 0.3)

	red0 = rgb_str % (240, 186, 182, 0.3)
	red1 = rgb_str % (214, 156, 152, 0.3)

	grn0 = rgb_str % (192, 245, 191, 0.3)
	grn1 = rgb_str % (157, 214, 156, 0.3)

	cols = [(red0, red1), (blu0, blu1), (yel0, yel1)]

	if removal_idcs[i] != -1:
		if removal_idx_bounds[removal_idcs[i]][0] == i:
			(col0, col1) = cols[removal_depth%len(cols)]
			new_log.append('<div style="box-shadow: 0 10px 10px -5px rgba(0, 0, 0, 0.2); display: inline-block; position:relative; margin: 10px 10px 10px 10px; padding: 5px 5px 5px 5px;"><div style="position:absolute; top:0px; left:0px; background: repeating-linear-gradient( 45deg, %s, %s 5px, %s 5px, %s 10px ); width: 100%%; height: 100%%; z-index: 2; border-radius: 5px;"><p style="font-weight: bold; margin: 5px 5px 5px 5px;">Removal %d of %d (depth %d)</p></div>' % (col0, col0, col1, col1, removal_idcs[i]+1, len(removal_idx_bounds.keys()), removal_depth))
			removal_depth += 1
	new_log.append(line)
	if removal_idcs[i] != -1:
		if removal_idx_bounds[removal_idcs[i]][1] == i:
			new_log.append('</div>')
			removal_depth -= 1

# print(len(md_kept))
# print(merge_diffs(sys.argv[1])[:-10])
# print('\n\n\n\n\n')
# print(len(new_log))



print(PAGE%('\n'.join(new_log)))
