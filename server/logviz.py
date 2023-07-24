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
	log = [(x.split(': ')[0], ': '.join(x.split(': ')[1:])) for x in log]

	log = [VAL_MSG%x[1] if x[0] == 'VAL' else USR_MSG%x[1] for x in log]

print(PAGE%('\n'.join(log)))
