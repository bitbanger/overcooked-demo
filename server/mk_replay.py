import os
import os.path
import re
import sys

from logdiff import read, lines

# Models used for sessions as the codebase was updated.
# It's unfortunate to have to do it like this.
models = ['gpt-3.5-turbo-0613']*1 + ['gpt-3.5-turbo-0301']*6 + ['gpt-4-0613']*2 + ['gpt-4']*10

logdir = sys.argv[1].strip()

session_num = int(re.findall('session(\d*)_', logdir)[0])

model = models[session_num-1]

print(model)

raw_log = lines(read(os.path.join(logdir, 'log.txt')))

for i in range(len(raw_log)):
	line = raw_log[i]
	determined_args = None
	if i > 0:
		last_line = raw_log[i-1]
		if 'I think these are the objects of' in last_line:
			determined_args = re.findall('<code>([^<]*)</code>', last_line)[1:]

	if len(line) >= 5 and line[:5] == 'User:':
		if determined_args is not None and line.strip() == 'User: Y':
			print(' '.join(determined_args))
		else:
			print(line[6:])
