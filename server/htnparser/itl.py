import pickle
import sys

from copy import deepcopy
# from .modular_parser import ModularHTNParser
from .chat_parser import ChatParser

REQUEST = '#REQUEST#'
INSTRUCTION = '#INSTRUCTION#'
EXPLANATION = '#EXPLANATION#'

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
	def __init__(self, primitive_actions, in_stream=sys.stdin, out_fn=print, chatlog=[], gameid=None, socketio=None, app=None, premove_sender=None):
		self.premove_sender = premove_sender
		self.app = app
		self.socketio = socketio
		self.gen_task_knowledge = dict()

		self.gameid = gameid

		self.arg_num = 0

		self.chatlog = chatlog
		self.out_fn = out_fn

		# self.parser = ModularHTNParser()
		self.parser = ChatParser(in_stream=in_stream, out_fn=out_fn, chatlog=chatlog, gameid=gameid, socketio=socketio, app=app, premove_sender=premove_sender)

		self.primitive_actions = [x.strip() for x in primitive_actions.split(', ')]

	def wait_input(self, prompt=''):
		return self.parser.wait_input(prompt)

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
	def parse(self, instruction, clarify_hook=None, clarify_unknowns=True):
		if clarify_hook:
			for elem in self.parser.get_actions(self.known_actions(), None, instruction, clarify_hook=clarify_hook, clarify_unknowns=clarify_unknowns):
				yield elem
		else:
			for elem in self.parser.get_actions(self.known_actions(), None, instruction, clarify_unknowns=clarify_unknowns):
				yield elem

	def linearize_plan(self, plan, in_bindings=dict(), only_depth=None, depth=0):
		leaves = []
		print('plan steps are %s' % (plan,))
		for step in plan:
			bindings = deepcopy(in_bindings)
			try:
				(status, name, args) = step
			except:
				print('step was %s' % (step,))
			(status, name, args) = step

			# If any of our args have been bound, use the values instead
			args = [bindings[arg].strip() if arg in bindings else arg.strip() for arg in args]
			args = [arg for arg in args if len(arg) > 0]

			# Add leaf actions to the linearization
			if only_depth is not None:
				if depth == only_depth:
					leaves.append('%s %s' % (name, ','.join(args)))
			else:
				if name.lower() not in self.gen_task_knowledge:
					leaves.append('%s %s' % (name, ','.join(args)))

			if only_depth is None or depth < only_depth:
				# Recurse for composite/learned actions
				if name.lower() in self.gen_task_knowledge:
					# Get the generalized arg names for this action
					gen_args = self.gen_task_knowledge[name.lower()][1]

					print('definition for %s is %s' % (name.lower(), self.gen_task_knowledge[name.lower()][0]))

					# Make the binding dict
					for i in range(len(args)):
						if gen_args[i] in bindings and bindings[gen_args[i]] != args[i]:
							# print("BINDING CONFLICT: %s in method %s can't bind to both %s and %s" % (gen_args[i], name, bindings[gen_args[i]], args[i]))
							quit()
						bindings[gen_args[i]] = args[i]

					# Recurse
					leaves += self.linearize_plan(self.gen_task_knowledge[name.lower()][0], in_bindings=deepcopy(bindings), only_depth=only_depth, depth=depth+1)

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

	def extract_instruct_action(self, utterance):
		prompt1 = self.parser.load_prompt('prompts/chat_instruct_extractor_pt1.txt')
		prompt2 = self.parser.load_prompt('prompts/chat_instruct_extractor_pt2.txt')

		r1 = self.parser.gpt.get_chat_gpt_completion(prompt1%utterance.strip())
		r2 = self.parser.gpt.get_chat_gpt_completion(prompt2%(utterance.strip(), r1.strip()))

		return r2.split('"')[1].strip()

	def extract_explain_action(self, utterance):
		prompt = self.parser.load_prompt('prompts/chat_explain_extractor.txt')

		r1 = self.parser.gpt.get_chat_gpt_completion(prompt%utterance.strip())

		return r1.split('"')[1].strip()

	def classify_intent(self, utterance):
		prompt = self.parser.load_prompt('prompts/chat_intent.txt')

		cls = self.parser.gpt.get_chat_gpt_completion(prompt%utterance.strip())

		intent = REQUEST
		if "1" in cls:
			intent = REQUEST
		elif "2" in cls:
			intent = INSTRUCTION
		elif "3" in cls:
			intent = EXPLANATION

		if intent == REQUEST:
			return (intent,)
		elif intent == INSTRUCTION:
			# get the name of the task they're teaching
			try:
				return (intent, self.extract_instruct_action(utterance))
			except:
				return (REQUEST,)
		elif intent == EXPLANATION:
			# get the name of the task they want explained
			try:
				return (intent, self.extract_explain_action(utterance))
			except:
				return (REQUEST,)

	def process_instruction(self, instruction, clarify_hook=None, clarify_unknowns=True, only_depth=None):
		# Call the parser with the instruction.
		# This will convert it into a full task
		# tree, represented as a list of possibly
		# non-terminal actions (action_seq) and a
		# dictionary mapping all non-terminal actions
		# to their definitions (new_actions), grounding
		# out with entirely terminal (primitive) actions.
		for elem in self.parse(instruction, clarify_hook=clarify_hook, clarify_unknowns=clarify_unknowns):
			if type(elem) == dict and clarify_unknowns:
				print('got dict %s' % elem)
				new_actions = elem
				# Generalize the learned actions, abstracting
				# out specific arguments.
				for learned_name in new_actions:
					# print("\nOK, I've learned how to '%s'!" % (learned_name))
					(substeps, arg_names) = new_actions[learned_name]
					self.generalize_learned_action((learned_name, substeps, arg_names))
				learned_fmt = ''
				learned_names = sorted([x for x in new_actions])
				if len(learned_names) > 0:
					for i in range(len(learned_names)):
						if i == len(learned_names)-1:
							learned_fmt = learned_fmt + ', and '
						elif i != 0:
							learned_fmt = learned_fmt + ', '
						learned_fmt = learned_fmt + '<code>%s</code>'%(learned_names[i],)
					self.out_fn("OK, from your explanation of how to \"<i>%s</i>\", I've learned how to %s!" % (instruction, learned_fmt))
					
			else:
				# Linearize the plan by applying the argument-binding
				# action sequence from the parser to the generalized
				# task knowledge and extracting the sequence of all
				# primitive actions.
				# return self.linearize_plan(action_seq)
				# for step in self.linearize_plan([elem]):
					# yield step

				if only_depth is not None:
					if elem[0] == 'action_stream':
						continue
					for step in self.linearize_plan([elem], only_depth=only_depth):
						yield step
				else:
					if elem[0] == 'action_stream':
						print('got action stream %s' % (elem[1],))
						for step in self.linearize_plan([elem[1]]):
							print('as step is %s' % (step,))
							yield ['action_stream', step]
					else:
						for step in self.linearize_plan([elem]):
							yield step

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
