import os
import os.path
import re
import sys

from logdiff import read, lines

logdir = sys.argv[1].strip()

raw_log = lines(read(os.path.join(logdir, 'log.txt')))

for i in range(len(raw_log)):
	line = raw_log[i]
	determined_args = None
	if i > 0:
		last_line = raw_log[i-1]
		if 'I think these are the objects of' in last_line:
			determined_args = re.findall('<code>([^<]*)</code>', last_line)[1:]

	if len(line) >= 5 and line[:5] == 'User:':
		if determined_args is not None:
			print(' '.join(determined_args))
		else:
			print(line[6:])
			
