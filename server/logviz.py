import sys

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

new_log = []
for l in log:
	# Handle radio selections
	if len(new_log) > 0 and 'radio' in new_log[-1] and 'checked' not in new_log[-1]:
		choice = ': '.join(l.split(': ')[1:]).strip()

		# Disable all options
		new_log[-1] = new_log[-1].replace('value="', 'disabled="true" value="')
		# Select and un-disable the right option
		new_log[-1] = new_log[-1].replace('disabled="true" value="%s"'%choice, 'value="%s" checked="true"'%choice)
	else:
		new_log.append(l)

new_log = [(x.split(': ')[0], ': '.join(x.split(': ')[1:])) for x in new_log]

new_log = [VAL_MSG%x[1] if x[0] == 'VAL' else USR_MSG%x[1] for x in new_log]

print(PAGE%('\n'.join(new_log)))
