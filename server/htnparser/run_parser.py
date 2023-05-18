import argparse
import pickle
import sys

from copy import deepcopy
from modular_parser import ModularHTNParser

argparser = argparse.ArgumentParser(
	prog='HTNParser',
	description='GPT-based semantic parser for HTNs')

argparser.add_argument('-m', '--model')
argparser.add_argument('-i', '--input')
argparser.add_argument('-p', '--parser', default='modular')
argparser.add_argument('-s', '--save')
argparser.add_argument('-l', '--load')
argparser.add_argument('-f', '--freeform', action='store_true')

args = argparser.parse_args()

PRINT_DIALOG = True

def old_print_plan(m, new, depth=0):
	for s in m:
		print('\t'*depth + str(s))
		if s[0] == 'learned' or s[1].lower() in new:
			print_plan(new[s[1].lower()][0], new, depth=depth+1)

def print_plan(plan, learned_actions, depth=0, in_bindings=dict(), only_leaves=False):
	for step in plan:
		bindings = deepcopy(in_bindings)
		(status, name, args) = step

		# If any of our args have been bound, use the values instead
		args = [bindings[arg].strip() if arg in bindings else arg.strip() for arg in args]

		if only_leaves:
			if name.lower() not in learned_actions:
				print('%s %s' % (name, ','.join(args)))
				with open('out', 'a+') as f:
					f.write('%s %s\n' % (name, ','.join(args)))
		else:
			print('\t'*depth + '%s(%s)' % (name, ', '.join(args)))

		# Recurse for composite/learned actions
		if name.lower() in learned_actions:
			# Get the generalized arg names for this action
			gen_args = learned_actions[name.lower()][1]

			# Make the binding dict
			for i in range(len(args)):
				if gen_args[i] in bindings and bindings[gen_args[i]] != args[i]:
					print("BINDING CONFLICT: %s in method %s can't bind to both %s and %s" % (gen_args[i], name, bindings[gen_args[i]], args[i]))
					quit()
				bindings[gen_args[i]] = args[i]

			# Recurse
			print_plan(learned_actions[name.lower()][0], learned_actions, depth=depth+1, in_bindings=deepcopy(bindings), only_leaves=only_leaves)

def linearize_plan(plan, learned_actions, in_bindings=dict()):
	leaves = []
	for step in plan:
		bindings = deepcopy(in_bindings)
		(status, name, args) = step

		# If any of our args have been bound, use the values instead
		args = [bindings[arg].strip() if arg in bindings else arg.strip() for arg in args]

		# Add leaf actions to the linearization
		if name.lower() not in learned_actions:
			leaves.append('%s %s' % (name, ','.join(args)))

		# Recurse for composite/learned actions
		if name.lower() in learned_actions:
			# Get the generalized arg names for this action
			gen_args = learned_actions[name.lower()][1]

			# Make the binding dict
			for i in range(len(args)):
				if gen_args[i] in bindings and bindings[gen_args[i]] != args[i]:
					print("BINDING CONFLICT: %s in method %s can't bind to both %s and %s" % (gen_args[i], name, bindings[gen_args[i]], args[i]))
					quit()
				bindings[gen_args[i]] = args[i]

			# Recurse
			leaves += linearize_plan(learned_actions[name.lower()][0], learned_actions, in_bindings=deepcopy(bindings))

	return leaves

class ExtrasClarifier:
	def __init__(self, extras, print_dialog=False):
		self.extras = extras
		self.counter = 0
		self.print_dialog = print_dialog

	def __call__(self, inp_str):
		if self.counter < len(self.extras):
			self.counter += 1
			if self.print_dialog:
				# print('What do you mean by "%s"?: %s' % (inp_str, self.extras[self.counter-1]))
				print('VAL: What do you mean by "%s"?' % (inp_str,))
				print('Human: %s' % (self.extras[self.counter-1],))
			return self.extras[self.counter-1]
		else:
			return input('What do you mean by "%s"?: ' % (inp_str,))

def print_learned(learned):
	for name in learned:
		(substeps, args) = learned[name]
		print('%s(%s):' % (name, ', '.join(args)))
		for step in substeps:
			(_, sub_name, sub_args) = step
			print('\t%s(%s)' % (sub_name, ', '.join(sub_args)))

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

	known_actions = inp.split('\n')[0].strip().split(',')

	loaded_learned = None
	if args.load:
		with open(args.load, 'rb') as f:
			loaded_learned = pickle.load(f)
			for name in loaded_learned:
				num_args = len(loaded_learned[name][-1])
				new_args = ['<arg%d>' % (i+1) for i in range(num_args)]
				known_actions.append('%s(%s) - a learned action' % (name, ', '.join(new_args)))

	# inp = input('Human: ').strip()
	# inp = '\n'.join(inp.split('\n')[1:])
	if not args.freeform:
		extras = []
		if len(inp.split('\n')) > 2:
			extras = [x.strip() for x in inp.split('\n')[2:]]
		inp = inp.split('\n')[1].strip()

		if PRINT_DIALOG:
			print('Human: %s' % (inp,))

		(decomps, mapped, new) = parser.get_actions(known_actions, inp, clarify_hook=ExtrasClarifier(extras, print_dialog=PRINT_DIALOG))
	else:
		inp = input('Human: ').strip()
		(decomps, mapped, new) = parser.get_actions(known_actions, inp)
	# print(new.keys())

	new_gen = dict()
	arg_num = 0
	for k in loaded_learned:
		new_gen[k] = loaded_learned[k]
		for arg in loaded_learned[k][-1]:
			this_arg_num = int(arg.split('arg')[-1][:-1])
			if this_arg_num > arg_num:
				arg_num = this_arg_num
	for learned_name in new:
		(substeps, arg_names) = new[learned_name]
		new_steps = []

		new_arg_names = dict()
		gen_arg_names = []
		# Find out which args occur in substeps
		# TODO: recursively expand the substep tree first?
		# TODO: how will we deal with multiple args of same type, or non-exact matches?
		for i in range(len(arg_names)):
			# TODO: needs to work with duplicate arg names in two methods (scope it!)
			arg_name = arg_names[i]
			arg_num += 1
			if True or any([arg_name in substep[2] for substep in substeps]):
				gen_arg_names.append('<arg%d>' % (arg_num))
				new_arg_names[arg_name] = gen_arg_names[-1]
			else:
				gen_arg_names.append(arg_name)

		# Replace the generalized args in the substeps
		new_substeps = []
		for step in substeps:
			new_step_args = []
			for step_arg in step[2]:
				if step_arg in new_arg_names:
					new_step_args.append(new_arg_names[step_arg])
				else:
					new_step_args.append(step_arg)
			new_substeps.append((step[0], step[1], new_step_args))

		new_gen[learned_name] = (new_substeps, gen_arg_names)

		if args.save:
			with open(args.save, 'wb') as f:
				pickle.dump(new_gen, f)

	'''
	print('\n')

	print('BUILT-IN ACTIONS:')
	for ka in known_actions:
			print(ka)
	print('')

	print('LEARNED ACTIONS (SPECIFIC):')
	print_learned(new)
	print('')

	print('LEARNED ACTIONS (GENERALIZED):')
	print_learned(new_gen)
	print('')

	print('decomposed:')
	for d in decomps:
		print('\t%s' % (d,))
	print('')
	print('PLAN:')
	print_plan(mapped, new_gen)
	print('')
	for m in mapped:
		print('\t%s' % (m,))

	'''



	# print('INPUT TO GAME:')
	# print_plan(mapped, new_gen, only_leaves=True)

	actions = linearize_plan(mapped, new_gen)

	# Clear the output file
	with open('out', 'w+') as f:
		f.write('')

	# Output actions to the output file
	with open('out', 'a+') as f:
		for i in range(len(actions)):
			action = actions[i]
			f.write(action + '\n')


	'''
	print('new:')
	for k in new:
		print('\t%s:' % k)
		for e in new[k]:
			print('\t\t%s' % (e,))
	'''
