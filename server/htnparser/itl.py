import pickle
import sys

from copy import deepcopy
# from .modular_parser import ModularHTNParser
from .chat_parser import ChatParser

# InteractiveTaskLearner (ITL) is a stateful class meant to
# contain and manage the lifetime knowledge of an interactive
# agent whose task knowledge is acquired by the clarification
# of commands given by an instructor.
#
# The instructor interacts with the ITL by providing commands
# in natural language which ITL converts into a sequence of
# atomic actions to be taken. Any unknown commands are recursively
# clarified according to the logic in ModularHTNParser. Whenever
# commands are clarified, they are also generalized and added
# to the ITL's permanent task memory.
#
# As the ITL class is meant to be a permanent knowledge store, it
# includes serialization and deserialization methods for easy
# storage and loading across individual sessions.
class InteractiveTaskLearner:
	# primitive_actions is passed in as a comma-separated string
	# of actions in the following format (excluding quotes):
	# "PRED(<arg1>, <arg2>, ...) - an action description"
	def __init__(self, primitive_actions, in_stream=sys.stdin):
		self.gen_task_knowledge = dict()

		self.arg_num = 0

		# self.parser = ModularHTNParser()
		self.parser = ChatParser(in_stream=in_stream)

		self.primitive_actions = [x.strip() for x in primitive_actions.split(',')]

	def known_actions(self):
		learned_actions = []
		for learned_action in self.gen_task_knowledge.keys():
			(_, arg_names) = self.gen_task_knowledge[learned_action]
			learned_actions.append('%s(%s) - a learned action' % (learned_action, ', '.join(arg_names)))

		return self.primitive_actions + learned_actions

	def chat_known_actions(self):
		learned_actions = []
		for learned_action in self.gen_task_knowledge.keys():
			(_, arg_names) = self.gen_task_knowledge[learned_action]
			learned_actions.append('%s(%s)' % (learned_action, ', '.join(arg_names)))

		return [x.split('-')[0].strip() for x in self.primitive_actions] + learned_actions

	# Because of the way clarify_hook handles a None value in
	# the parser, and just for terseness, we're abstracting the
	# parser call into this member method.
	def parse(self, instruction, clarify_hook=None):
		(action_seq, new_actions) = (None, None)
		if clarify_hook:
			(_, action_seq, new_actions) = self.parser.get_actions(self.known_actions(), None, instruction, clarify_hook=clarify_hook)
		else:
			(_, action_seq, new_actions) = self.parser.get_actions(self.known_actions(), None, instruction)

		return (action_seq, new_actions)

	def linearize_plan(self, plan, in_bindings=dict()):
		leaves = []
		for step in plan:
			bindings = deepcopy(in_bindings)
			(status, name, args) = step

			# If any of our args have been bound, use the values instead
			args = [bindings[arg].strip() if arg in bindings else arg.strip() for arg in args]

			# Add leaf actions to the linearization
			if name.lower() not in self.gen_task_knowledge:
				leaves.append('%s %s' % (name, ','.join(args)))

			# Recurse for composite/learned actions
			if name.lower() in self.gen_task_knowledge:
				# Get the generalized arg names for this action
				gen_args = self.gen_task_knowledge[name.lower()][1]

				# Make the binding dict
				for i in range(len(args)):
					if gen_args[i] in bindings and bindings[gen_args[i]] != args[i]:
						# print("BINDING CONFLICT: %s in method %s can't bind to both %s and %s" % (gen_args[i], name, bindings[gen_args[i]], args[i]))
						quit()
					bindings[gen_args[i]] = args[i]

				# Recurse
				leaves += self.linearize_plan(self.gen_task_knowledge[name.lower()][0], in_bindings=deepcopy(bindings))

		return leaves

	def generalize_learned_action(self, learned_action):
		(learned_name, substeps, arg_names) = learned_action
		generalized_steps = []

		new_arg_names = dict()
		gen_arg_names = []
		# Find out which args occur in substeps
		# TODO: recursively expand the substep tree first?
		# TODO: how will we deal with multiple args of same type, or non-exact matches?
		for i in range(len(arg_names)):
			# TODO: needs to work with duplicate arg names in two methods (scope it!)
			arg_name = arg_names[i]
			self.arg_num += 1
			if True or any([arg_name in substep[2] for substep in substeps]):
				gen_arg_names.append('<arg%d>' % (self.arg_num))
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

		# Store the generalized task representation
		# in the internal knowledge base
		self.gen_task_knowledge[learned_name] = (new_substeps, gen_arg_names)

	def process_instruction(self, instruction, clarify_hook=None):
		# Call the parser with the instruction.
		# This will convert it into a full task
		# tree, represented as a list of possibly
		# non-terminal actions (action_seq) and a
		# dictionary mapping all non-terminal actions
		# to their definitions (new_actions), grounding
		# out with entirely terminal (primitive) actions.
		(action_seq, new_actions) = self.parse(instruction, clarify_hook=clarify_hook)

		# Generalize the learned actions, abstracting
		# out specific arguments.
		for learned_name in new_actions:
			print("\nOK, I've learned how to '%s'!" % (learned_name))
			(substeps, arg_names) = new_actions[learned_name]
			self.generalize_learned_action((learned_name, substeps, arg_names))

		# Linearize the plan by applying the argument-binding
		# action sequence from the parser to the generalized
		# task knowledge and extracting the sequence of all
		# primitive actions.
		return self.linearize_plan(action_seq)

	def save(self, filename):
		with open(filename, 'wb+') as f:
			pickle.dump(self, f)

	@staticmethod
	def load(filename):
		with open(filename, 'rb') as f:
			ret = pickle.load(f)
			# ret.parser.completer.init_openai_api()
			ret.parser.completer.__init__()
			return ret
