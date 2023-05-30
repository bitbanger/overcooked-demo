import os.path
import select
import sys

if __name__ == '__main__':
	from gpt_completer import GPTCompleter
else:
	from .gpt_completer import GPTCompleter

ACT_FN = 'prompts/convo2.txt'
SEG_FN = 'prompts/chat_segmenter.txt'
NAME_FN = 'prompts/chat_namer.txt'
GROUND_FN = 'prompts/chat_grounder.txt'
PARA_FN = 'prompts/chat_paraphrase_ider.txt'
VERB_FN = 'prompts/chat_verbalizer.txt'

def indent(s, n):
	return '\t'*n + s.replace('\n', '\n'+'\t'*n)

class ChatParser:
	def __init__(self, act_prompt_fn=ACT_FN, segment_prompt_fn=SEG_FN, name_prompt_fn=NAME_FN, ground_prompt_fn=GROUND_FN, para_fn=PARA_FN, verb_fn=VERB_FN, in_stream=sys.stdin):
		self.act_prompt = self.load_prompt(act_prompt_fn)
		self.segment_prompt = self.load_prompt(segment_prompt_fn)
		self.name_prompt = self.load_prompt(name_prompt_fn)
		self.ground_prompt = self.load_prompt(ground_prompt_fn)
		self.para_prompt = self.load_prompt(para_fn)
		self.verb_prompt = self.load_prompt(verb_fn)

		self.in_stream = in_stream

		self.life_depends_prompt = self.load_prompt('prompts/life_depends.txt')
		self.preselect_prompt = self.load_prompt('prompts/preselect_grounder.txt')

		self.gpt = GPTCompleter()

	def wait_input(self, prompt):
		print(prompt, end='')
		inp = None
		while not inp:
			inp, onp, enp = select.select([self.in_stream._reader], [], [], 5)
			# print('pre-"if inp" inp is %s' % (inp,))
			if inp:
				# print('got raw inp %s (type %s)' % (inp, type(inp)))
				# inp = self.in_stream.readline().strip()
				inp = self.in_stream.get().strip()
				# print('read val %s' % (inp,))

		# print('returning "%s" (type %s)' % (inp, type(inp)))

		return inp

	@staticmethod
	def load_prompt(prompt_fn):
		new_fn = os.path.join(os.path.dirname(__file__), prompt_fn)
		try:
			with open(new_fn, 'r') as f:
				return f.read().strip()
		except:
			print('error loading prompt from filename %s' % (new_fn,))
			return None

	# segment_text splits a raw input potentially containing
	# multiple actions and returns a list of individual actions
	# with pronouns resolved for standalone interpretation, e.g.,
	# segment_text("find an onion and go to it")
	# ==
	# ["find an onion", "go to the onion"]
	def segment_text(self, text):
		# SEGMENTS: 1. "cook an onion" (resolved pronouns: "cook an onion")
		resp = self.gpt.get_chat_gpt_completion(self.segment_prompt%text)
		print('I think these are the individual actions of "%s":\n%s' % (text, indent(resp, 1)))
		segs = []
		for line in resp.split('\n'):
			segs.append(line.split('"')[5])

		return segs

	# name_action takes a single action description of the sort
	# returned by segment_text and produces a predicate name for
	# it, e.g.,
	# name_action("put an onion in the pot")
	# ==
	# "put"
	def name_action(self, action):
		return self.gpt.get_chat_gpt_completion(self.name_prompt%action)

	def verbalize_pred(self, pred):
		return self.gpt.get_chat_gpt_completion(self.verb_prompt%pred).strip()

	def is_paraphrase(self, action, pred):
		# return self.gpt.get_chat_gpt_completion(self.para_prompt%('"%s" and %s' % (action, pred)))[0] == 'Y'
		return 'yes' in self.gpt.get_chat_gpt_completion('Do "%s" and "%s" mean the same thing? Please answer either "yes" or "no".' % (action, self.verbalize_pred(pred))).lower()

	def ground_new_args(self, action, objects):
		name = self.name_action(action)
		inp = 'OBJECTS: [%s]' % ', '.join([x for x in objects if len(x.strip()) > 0])
		inp = inp + '\nPHRASE: "%s"' % action
		inp = inp + '\nVERB: %s' % name.split('(')[0]

		resp = self.gpt.get_chat_gpt_completion(self.ground_prompt%inp)

		if ': ' in resp:
			resp = resp.split(': ')[1]

		if '(' not in resp:
			return resp + '()'
		else:
			return resp

	def choose_action_pred(self, known_actions, world_state, action):
		# Encode all inputs into the prompt
		new_ka_lst = [('[%s] %s' % (chr(ord('a')+i), known_actions[i].split('-')[0].strip())) for i in range(len(known_actions))]
		obj_str = '[pot, onion, tomato, dropoff, plate]'
		first_ka_str = ', '.join(new_ka_lst)

		second_ka_lst = [x.split('(')[0] for x in new_ka_lst]
		second_ka_lst.append('[%s] None of the above; "%s" would require a combination of actions.' % (chr(ord('a')+len(known_actions)), action))
		second_ka_str = '\n'.join(second_ka_lst)

		prompt = self.life_depends_prompt % (first_ka_str, obj_str, action, second_ka_str)
		resp = self.gpt.get_chat_gpt_completion(prompt)
		choice = None
		for i in range(len(resp)):
			if resp[i] == '[':
				choice = resp[i+1]
				break
		choice = ord(choice)-ord('a')
		chosen_ka = 'noGoodAction'
		if choice < len(known_actions):
			# chosen_ka = known_actions[choice].split('(')[0]
			chosen_ka = known_actions[choice].split('-')[0].strip()

		return chosen_ka

	def choose_action_args(self, chosen_action, world_state, action):
		if '()' in chosen_action:
			# print('RETURNING %s' % (chosen_action,))
			return chosen_action

		obj_str = '[pot, onion, tomato, dropoff, plate]'

		num_args = len(chosen_action.split(','))

		num_args_str = '%d argument%s' % (num_args, '' if num_args==1 else 's')
		num_objs_str = '%d object%s' % (num_args, '' if num_args==1 else 's')

		pred_name = chosen_action.split('(')[0]

		o_list = ', '.join([('o%d' % (i+1)) for i in range(num_args)])

		prompt = self.preselect_prompt % (chosen_action, action, obj_str, chosen_action, num_args_str, num_objs_str, pred_name, o_list)

		resp = self.gpt.get_chat_gpt_completion(prompt).strip()

		if '"' in resp:
			resp = resp.replace('"', '').strip()

		return resp

		# prompt_inp = '1. %s\n2. %s\n3. "%s"' % (ka_str, obj_str, action)
		# prompt = self.act_prompt % prompt_inp

	def ground_action(self, known_actions, world_state, action):
		chosen_action_pred = self.choose_action_pred(known_actions, world_state, action)
		if chosen_action_pred == 'noGoodAction':
			return 'noGoodAction'

		chosen_action_args = self.choose_action_args(chosen_action_pred, world_state, action)

		if not self.is_paraphrase(action, chosen_action_args):
			return 'noGoodAction'

		return chosen_action_args

	# ground_action takes a single action description of the sort
	# returned by segment_text, along with a world state and a list
	# of known actions, and tries to choose an appropriate known
	# action and set of arguments. If it determines no known action
	# is suitable, it will return the string "noGoodAction". Because
	# the underlying ChatGPT model often tries to string multiple
	# actions together to define unknown actions, ground_action may
	# perform "programmatic scolding" by asking ChatGPT to try again.
	def old_ground_action(self, known_actions, world_state, action):
		# Encode all inputs into the prompt
		ka_str = ', '.join(known_actions)
		obj_str = 'objects: [pot, onion, tomato, dropoff, plate] & mental values: []'
		prompt_inp = '1. %s\n2. %s\n3. "%s"' % (ka_str, obj_str, action)
		prompt = self.act_prompt % prompt_inp

		# Call ChatGPT
		resp = self.gpt.get_chat_gpt_completion(prompt)
		# print('INITIAL RESP: %s' % (resp,))

		# Programmatically scold, if applicable
		# if len(resp.split('),')) > 1:
			# new_prompt = prompt + '\n***\n%s\n***\nNo, you may not include multiple actions. Either pick one known action, or start your response with "noGoodAction".' % resp.strip()
			# resp = self.gpt.get_chat_gpt_completion(new_prompt)

		if len(resp.split('),')) > 1:
			resp = 'noGoodAction'

		# Check the paraphrase one last time
		if not self.is_paraphrase(action, resp):
			resp = 'noGoodAction'

		return resp.strip()

	def get_subtree_objs(self, action_seq, new_action_defs):
		lowercase_args = set()
		args = set()

		# Add all args from direct children in the subtree
		for action in action_seq:
			for arg in action[2]:
				if arg.lower() not in lowercase_args:
					args.add(arg)
				lowercase_args.add(arg.lower())

			# If the child was learned, recurse
			if action[0] == 'learned':
				rec_args = self.get_subtree_objs(new_action_defs[action[1].lower()][0], new_action_defs)
				for rec_arg in rec_args:
					if rec_arg.lower() not in lowercase_args:
						args.add(rec_arg)
					lowercase_args.add(rec_arg.lower())

		return list(args)

	# get_actions takes a list of known actions, a world state,
	# and a textual description of an action sequence, and returns
	# two things:
	# 1. a corresponding sequence of valid actions to execute in the world
	# 2. a dictionary tree defining all "new" actions (i.e., those not in
	#    the input known_actions) as sequences of either new or known actions
	# The idea is that get_actions will identify known actions when
	# appropriate, or decide to introduce a new action otherwise,
	# which it then seeks a natural language definition for by making
	# a recursive call to itself on new input. When the process concludes,
	# all new actions will be groundable in terms of actions known prior
	# to the call.
	def get_actions(self, known_actions, world_state, text, clarify_hook=None):
		if clarify_hook is None:
			clarify_hook = lambda a: self.wait_input('\nWhat do you mean by "%s"?: ' % (a,))

		action_seq = []
		new_action_defs = {}

		# First, segment the actions
		action_segments = self.segment_text(text)
		# print('SEGMENTS: %s' % action_segments)

		# Now try to ground out each one. If it works,
		# we can just be done with it.
		# grounded = []
		# for action in action_segments:
			# grounded.append(self.ground_action(known_actions, action))

		new_known_actions = known_actions[::]

		# Add the succesfully identified actions and
		# recursively define the unknown "noGoodAction"s.
		for i in range(len(action_segments)):
			action = action_segments[i]
			grounded = self.ground_action(new_known_actions, world_state, action)
			# print('new_known_actions: %s' % (new_known_actions,))
			# print('"%s" GROUNDED TO %s' % (action, grounded))
			is_unknown = False
			if grounded == 'noGoodAction':
				is_unknown = True
			else: # Known action?
				pred = grounded.split('(')[0]
				# print('pred is %s, new_known_actions are %s' % (pred, [x.split('(')[0] for x in new_known_actions]))
				if pred not in [x.split('(')[0] for x in new_known_actions]:
					# Nope, not a known action
					is_unknown = True
				else:
					# Yep, it's known!
					while True:
						print('I think that "%s" is the action %s' % (action, grounded))
						right = self.wait_input('Is that right? (Y/N): ').strip().lower()
						if 'y' not in right:
							new_action = self.wait_input('Could you please rephrase "%s", then?: ' % (action,)).strip()
							grounded = self.ground_action(new_known_actions, world_state, new_action)
						else:
							break
					args = [x.strip() for x in grounded.split('(')[1][:-1].split(',')]
					learned_or_known = 'known' if pred in [x.split('(')[0] for x in known_actions] else 'learned'
					action_seq.append(('known', pred, args))
			# print('known? %s' % ('no' if is_unknown else 'yes'))
			if is_unknown: # New, unknown action
				# Get a name for it.
				new_name = self.name_action(action)

				# Get a full task definition for it.
				new_explanation = clarify_hook(action)
				while True:
					done = 'n' in self.wait_input('Are there any other steps for "%s"? (Y/N): ' % (action)).lower()
					if done:
						break
					next_inp = self.wait_input('What comes next?: ')
					new_explanation = new_explanation + '. %s' % (next_inp)
				print('OK, got it!')
				(_, rec_action_seq, rec_new_action_defs) = self.get_actions(new_known_actions, world_state, new_explanation, clarify_hook=clarify_hook)

				# Extract the set of all argument objects in the subtree for
				# the next step, described immediately below.
				subtree_objects = self.get_subtree_objs(rec_action_seq, rec_new_action_defs)

				# Ground its text argument(s) into a set of world objects.
				# This step deserves a bit of extra explanation:
				# In cases like "multiply the numerators", the sole text
				# argument---"the numerators"---actually represents
				# multiple world objects, and the parameterization of the
				# learned action should reflect that. So, we extract the
				# set of all referred-to objects in the newly-obtained
				# decomposition of the new action, and then offer it to
				# ChatGPT alongside the original text ("multiply the
				# numerators"), allowing the LM to select the object(s)
				# best suited to appear in the predicate of the learned
				# action. The hope is that the LM also uses its intuitions
				# about verbalization to make the parameterization roughly
				# reflect the order of arguments used in invoking language,
				# e.g., to output put(onion, pot) instead of put(pot, onion).
				new_pred_and_args = self.ground_new_args(action, subtree_objects)
				new_pred = new_pred_and_args.split('(')[0]
				new_args = [x.strip() for x in new_pred_and_args.split('(')[1][:-1].split(',')]
				print('I think that these are the arguments of "%s": %s' % (action, new_args))
				new_pred_and_args_gen = '%s(%s)' % (new_pred, ', '.join([('<arg%d>' % (i+1)) for i in range(len(new_args))]))

				# print('NEW ACTION LEARNED: %s' % (new_pred_and_args))

				# Add all new, learned actions in the decomposition
				# to the known actions list and the task definition
				# dict.
				for rec_new_pred in rec_new_action_defs.keys():
					if rec_new_pred not in new_action_defs:
						new_action_defs[rec_new_pred] = rec_new_action_defs[rec_new_pred]

						new_known_actions.append('%s(%s) - a learned action' % (rec_new_pred, ', '.join([('<arg%d>' % (i+1)) for i in range(len(rec_new_action_defs[rec_new_pred][1]))])))

				# Catalog it all: update the "known actions" list for
				# future calls, update the task definition dict, and
				# add the new predicate to the action sequence.
				new_known_actions.append(new_pred_and_args_gen + ' - a learned action')
				action_seq.append(['learned', new_pred, new_args])
				new_action_defs[new_pred.lower()] = (rec_action_seq, new_args)

		# Since child calls in the recursion will see the "new known actions"
		# simply as "known actions", they may improperly label actions in
		# sequences as "known". We'll correct that here.
		# print(new_action_defs[rec_new_pred])
		for new_pred in new_action_defs.keys():
			seq = new_action_defs[new_pred][0]
			new_seq = []
			for nest in seq:
				if nest[1] not in [x.split('(')[0] for x in known_actions]:
					new_seq.append(('learned', nest[1], nest[2]))
				else:
					new_seq.append(nest)
			new_action_defs[new_pred] = (new_seq, new_action_defs[new_pred][1])

		return (None, action_seq, new_action_defs)

if __name__ == '__main__':
	parser = ChatParser()

	known_actions = ['moveToObject(<location>)', 'pressSpace()']
	world_state = None
	inp = sys.argv[1].strip()

	print(parser.get_actions(known_actions, world_state, inp))
