import random

old = None

print(r'''
***
We're going to do an iterative process together. At each iteration, I'll give you three things: 1. a list of actions you may take and their arguments; 2. a list of objects in the environment, including mental/conceptual items; and 3. a snippet of text provided by a user.

Your job will be to analyze the snippet of text and determine two things: a single action from the list of actions in input item 1, and a set of arguments to the action taken from input item 2. You should never pick more than one action, and you should always produce the correct number of arguments to that action, even if the user's text snippet doesn't have the correct number of arguments itself.

If you don't think there is a suitable item from the list of actions in input item 1, you may use the action "noGoodAction" instead. Please only pick actions if they really, truly mean the EXACT same thing. For example, "delete an email" and "clickEmail" do NOT mean the same thing.

There's no need to respond to me with any other words. Let's start right away with the following input:
''')

with open('arg_action_mapper.txt', 'r') as f:
	old = f.read().strip()

chunks = [x.strip() for x in old.split('=======')][:-1]
random.shuffle(chunks)

for chunk in chunks:
	sections = [[y.strip() for y in x.strip().split('\n')[1:]] for x in chunk.split('\n\n')]

	(known_actions, snippets, mappeds) = sections

	ka_str = '1. ' + ', '.join(known_actions).lower()
	objs = set()
	for mapped in mappeds:
		if 'no good action' in mapped:
			continue
		os = mapped.split('(')[1].strip()[:-1]
		os = [x.strip() for x in os.split(',')]
		for o in os:
			objs.add(o)
	world_state = '2. objects: [%s] & mental values: []' % (', '.join(list(objs)))

	for i in range(len(snippets)):
		snippet = snippets[i].split('"')[1].strip()
		mapped = mappeds[i].strip()
		snip_txt = '3. "%s"' % (snippet.strip())
		resp = 'noGoodAction'
		if 'no good action' not in mapped:
			resp = ' '.join(mapped.split(' ')[1:]).strip().lower()

		print('%s\n%s\n%s\n***\n%s' % (ka_str, world_state, snip_txt, resp))
		print('***')
print('%s')
