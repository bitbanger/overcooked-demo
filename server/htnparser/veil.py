import argparse
import sys

from modular_parser import ModularHTNParser

argparser = argparse.ArgumentParser(
	prog='HTNParser',
	description='GPT-based semantic parser for HTNs')

argparser.add_argument('-m', '--model')
argparser.add_argument('-i', '--input')
argparser.add_argument('-p', '--parser', default='modular')

args = argparser.parse_args()

def print_plan(m, new, depth=0):
	for s in m:
		print('\t'*depth + str(s))
		if s[0] == 'learned':
			print_plan(new[s[1]], new, depth=depth+1)

if __name__ == '__main__':
	if args.parser == 'modular':
		parser_class = ModularHTNParser
	else:
		print('unknown value "%s" for --parser; please use one of {"modular"}' % args.parser)
		quit()

	parser = parser_class(local_model=args.model)
	
	inp = None
	if args.input:
		with open(args.input, 'r') as f:
			inp = f.read().strip()
	else:
		inp = sys.stdin.read().strip()
	# known_actions = inp.split('\n')[0].strip().split(',')
	known_actions = 'moveTo,grasp,release,keep,turn,open,close,wait,scoop,place,add,pour,squeeze,press,insert'.split(',')
	# inp = '\n'.join(inp.split('\n')[1:])

	(decomps, mapped, new) = parser.get_actions(known_actions, inp)

	# print('decomposed:')
	# for d in decomps:
		# print('\t%s' % (d,))
	# print('')
	print('plan:')
	print_plan(mapped, new)
	# for m in mapped:
		# print('\t%s' % (m,))

	'''
	print('new:')
	for k in new:
		print('\t%s:' % k)
		for e in new[k]:
			print('\t\t%s' % (e,))
	'''
