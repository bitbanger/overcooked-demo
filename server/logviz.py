import sys

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
with open(sys.argv[1].strip(), 'r') as f:
	log = [x.strip() for x in f.read().strip().split('\n')]

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

new_log = []
for l in log:
	user_msg = ': '.join(l.split(': ')[1:]).strip()
	# Handle radio selections
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

new_log = [(x.split(': ')[0], ': '.join(x.split(': ')[1:])) for x in new_log]

new_log = [VAL_MSG%x[1] if x[0] == 'VAL' else USR_MSG%x[1] for x in new_log]

print(PAGE%('\n'.join(new_log)))
