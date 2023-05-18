import os.path

from .gpt_completer import GPTCompleter

# ModularHTNParser is a parser where GPT is consulted for only the smallest,
# most focused subroutines possible, using a different prompt for each. This
# approach is meant to minimize the complexity of each task the LM performs,
# hopefully maximizing per-task accuracy at the expense of more LM passes.
#
# Examples of these modular tasks:
# 	* NL-to-predicate conversion
# 		e.g., "go back to the stove" -> go(stove)
# 	* predicate-to-known-action mapping and unknown action identification
# 		e.g., go(stove) -> MOVETO(stove) or make(soup) -> UNKNOWN
# 	* argument grounding
# 		e.g., "stove" -> game object at coordinates (3, 4)
#
# This class only handles the actions above; to use this approach to
# iteratively acquire and save generalized task knowledge from dialog,
# use the InteractiveTaskLearner class.
class ModularHTNParser:
	def __init__(self, local_model=None, action_mapper_prompt_fn='prompts/arg_action_mapper.txt', extract_actions_prompt_fn='prompts/modular_action_extractor.txt'):
		self.completer = GPTCompleter(local_model=local_model)

		extract_actions_prompt_fn = os.path.join(os.path.dirname(__file__), extract_actions_prompt_fn)
		action_mapper_prompt_fn = os.path.join(os.path.dirname(__file__), action_mapper_prompt_fn)

		self.extract_actions_prompt = None
		with open(extract_actions_prompt_fn, 'r') as f:
			self.extract_actions_prompt = f.read().strip()

		self.action_mapper_prompt = None
		with open(action_mapper_prompt_fn, 'r') as f:
			self.action_mapper_prompt = f.read().strip()

	def extract_actions(self, inp):
		resp = self.completer.get_completion(self.extract_actions_prompt % (inp,))

		spl = resp.split('Decomposed actions:')
		sents = spl[0].strip()
		acts = spl[-1].strip()

		sent_list = []
		act_list = []

		for line in sents.split('\n'):
			sent_list.append(line.strip().split('"')[1].strip())

		for line in acts.split('\n'):
			if line.strip()[-1] == ']':
				action = line.strip().split(' - ')[-1].strip().split('[')[0].strip()
				act_list.append(action)

		return [(act_list[i], sent_list[i]) for i in range(len(sent_list))]

	def has_multiple_actions(self, resp):
		if ' and ' in resp:
			return True

		in_parens = False
		for c in resp:
			if c == '(':
				in_parens = True
			elif c == ',' and not in_parens:
				return True
			elif c == ')':
				in_parens = False

		return False

	def map_actions(self, inp_actions, known, clarify_hook=lambda ua: input('What do you mean by "%s"?: ' % (ua,))):
		ret = []

		new_actions = dict()

		# actions = []
		# mapped = []
		for a in inp_actions:
			# print(a)
			actions = [a]
			# actions.append(a)

			split_act_pred_args = (a[0].split('(')[0], [x.strip() for x in a[0].split('(')[1][:-1].split(',')])

			known_action_section = '\t' + '\n\t'.join([(ka.split(' - ')[0].upper() + ' - ' + ka.split(' - ')[-1]) for ka in known]) + '\n\t'# + '\n\t'.join(['%s(%s) - A LEARNED ACTION' % (l.upper(), ', '.join(new_actions[l][1])) for l in new_actions])
			# print(known_action_section)

			input_action_section = '\t' + '\n\t'.join(['a%d. %s - ["%s"]' % ((i+1), actions[i][0], actions[i][1]) for i in range(len(actions))])
			# input_action_section = '\t' + '\n\t'.join(['a%d. %s' % ((i+1), actions[i][0]) for i in range(len(actions))])

			prompt = self.action_mapper_prompt % (known_action_section, input_action_section)
			# print(prompt)

			resp = self.completer.get_completion(prompt).strip()
			# print(resp)
			# if 'no good action found' in resp or len(resp.split(',')) > 1:
			if 'no good action found' in resp or self.has_multiple_actions(resp):
				# ret.append(('unknown', split_act_pred_args[0], split_act_pred_args[1]))

				if clarify_hook is None:
					ret.append(('unknown', split_act_pred_args[0], split_act_pred_args[1]))
				else:
					# Recursively define the unknown action
					clar_pred = '%s(%s)' % (split_act_pred_args[0], ','.join(split_act_pred_args[1]))
					# print('did not know %s' % (clar_pred,))
					# (_, mapped, rec_new_actions) = self.get_actions(known+list(new_actions.keys()), clarify_hook(split_act_pred_args[0]))
					new_known = []
					for k in new_actions:
						# defn = input('What is a good description for the action %s(%s)?' % (k, ', '.join(['<arg%d>' % (i+1) for i in range(len(new_actions[k][1]))])))
						defn = 'a learned action'
						new_known.append('%s(%s) - %s' % (k, ', '.join(['<arg%d>' % (i+1) for i in range(len(new_actions[k][1]))]), defn))
					(_, mapped, rec_new_actions) = self.get_actions(known+new_known, clarify_hook(clar_pred), clarify_hook=clarify_hook)

					# Add any actions learned in the recursion to the new action list
					# new_actions = new_actions.union(rec_new_actions)
					for k in rec_new_actions:
						new_actions[k] = rec_new_actions[k]

						# Also add the new actions to the known action list
						# known.append(k.upper())
						# mapped.append(k.upper())

					# Add the unknown action we learned, as well
					# new_actions.add(split_act_pred_args[0])
					new_actions[split_act_pred_args[0].lower()] = (mapped, split_act_pred_args[1])

					ret.append(('learned', split_act_pred_args[0], split_act_pred_args[1]))
			else:
				# print(resp)
				# print('explanation: %s' % (resp.strip().split(' ')[-1].strip().split('->')[0]))
				# action = resp.strip().split(' ')[-1].strip().split('->')[-1].strip()
				# action = resp.strip().split(' ')[-1].strip()
				action_and_new_args = ' '.join(resp.strip().split(' ')[1:]).strip()
				action = action_and_new_args.split('(')[0]
				new_args = action_and_new_args.split('(')[1][:-1]
				# print('mapped %s to %s' % (split_act_pred_args, action_and_new_args))
				if len(new_args) > 0:
					new_args = new_args.split(',')
				else:
					new_args = []
				# ret.append(('known', action, split_act_pred_args[1]))
				ret.append(('known', action, new_args))
				# mapped.append(action)

		return (ret, new_actions)

	def get_actions(self, known_actions, inp, clarify_hook=lambda ua: input('What do you mean by "%s"?: ' % (ua,))):
		extracted = self.extract_actions(inp)
		# print(extracted)
		ret_actions = [(a[0].split('(')[0], [x.strip() for x in a[0].split('(')[1][:-1].split(',')]) for a in extracted]

		(mapped, new_actions) = self.map_actions(extracted, known_actions, clarify_hook=clarify_hook)

		return (ret_actions, mapped, new_actions)
