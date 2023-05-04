from copy import deepcopy
from json import dumps
from select import select
from threading import Thread
from time import sleep

from overcooked_ai_py.mdp.actions import Action, Direction

# from tutorenvs.overcooked import OvercookedTutorEnv

# from HTNAgent.htn_overcooked_operators import overcooked_methods, overcooked_actions
# from HTNAgent.tact_agent import TACTAgent

import importlib
import sys
import select
import nltk

import openai
import logging
openai.util.logger.setLevel(logging.WARNING)

import random

PRINT_TERRAIN = False
SESS_ID = 'demo_logs/' + str(random.randint(1,10000000))
PRINT_STATE = False

def wait_input():
	inp, onp, enp = select.select([sys.stdin], [], [], 5)
	if inp:
		inp = sys.stdin.readline().strip()
		return inp
	else:
		return None

class ValAI():
	def __init__(self, game):
		self.dirty_bit_ss = False
		self.dirty_bit_ihtn = False

		# self.itl = importlib.import_module('htn-parser.itl').InteractiveTaskLearner("moveToObject(<object>) - move over to an object,interactWithObject() - press the space button to interact with whatever you're facing")
		# self.itl = importlib.import_module('htn-parser.itl').InteractiveTaskLearner("moveToObject(<object>) - move over to an object,pressSpace() - press the space button to interact with whatever you're facing")
		# self.itl = importlib.import_module('htn-parser.itl').InteractiveTaskLearner.load('val_model.pkl')
		self.itl = importlib.import_module('htn-parser.itl').InteractiveTaskLearner("moveTo(<object>) - move to an object, pressSpace() - press the space bar")
		self.inp_queue = []

		self.have_acted = False
		self.game = game
		self.action_tick = 0
		self.state = None
		# self.env = OvercookedTutorEnv()
		# self.agent = TACTAgent(actions=overcooked_actions, methods=overcooked_methods, relations=[], env=self.env)

		self.waiting_player_pos = None

		self.collect_state_after_action = False
		self.state_snapshots = []
		self.last_inp_queue_size = 0

		self.state_dirty_bit = False
		self.state_hash = None

		self.block_htn = False

		self.first_action = True

		self.need_inp = True

		self.last_timestep = -1

		# self.target_pos = (1, 2)
		self.target_pos = None

		self.pathing_to_obj = False
		self.turning_to_target_obj = False

		# Send an initial state, including a target pos
		# self.env.state_queue_w.send({"pos": "1,1"})

		# Run the HTN planner in the background, iterating
		# with the same task over and over
		# Thread(target=self.iterate_htn).start()
		# Thread(target=self.send_state).start()

		self.pause_ticks = 0

		# self.target_pos

		# self.env.state_queue_w.send({})

	def ai_player_pos(self):
		return self.state.players[1].position

	def active_terrain(self, tries=10):
		nones = 0
		t = None
		for _ in range(tries):
			t = self.active_terrain_helper()
			if t is None:
				nones += 1
				sleep(0.5)
				continue
			else:
				break
		if nones > 0:
			print('in active_terrain, game state was inactive %d / %d times' % (nones, tries))

		return t

	# Returns the game terrain grid, populated with
	# current player positions (and, maybe one day,
	# other "dynamic obstacles"?)
	def active_terrain_helper(self):
		if not self.game._is_active:
			return None

		terrain = deepcopy(self.game.mdp.terrain_mtx)
		# transpose the terrain
		terrain_T = []
		for c in range(len(terrain[0])):
			col = []
			for r in range(len(terrain)):
				col.append(terrain[r][c])
			terrain_T.append(col)

		terrain = terrain_T

		for player in self.state.players:
			(x, y) = player.position
			terrain[x][y] = 'i' # "i" for players

		return terrain

	def ground_object(self, obj_name, tries=10):
		nones = 0
		t = None
		for _ in range(tries):
			t = self.ground_object_helper(obj_name)
			if t is None:
				nones += 1
				sleep(0.5)
				continue
			else:
				break
		if nones > 0:
			print('in ground_object, game state was inactive %d / %d times' % (nones, tries))

		return t

	# Takes an object name and returns a list of coordinates
	# for all matching objects in the game world
	def ground_object_helper(self, obj_name):
		if not self.game._is_active:
			return []

		ground_dict = {
			'onion': 'O',
			'onions': 'O',
			'tomato': 'T',
			'tomatoes': 'T',
			'tomatos': 'T',
			'plate': 'D',
			'plates': 'D',
			'pot': 'P',
			'pots': 'P',
			'stove': 'P',
			'stoves': 'P',
			'oven': 'P',
			'ovens': 'P',
			'dropoff': 'S',
			'dropoffs': 'S',
			'drop-off': 'S',
			'drop-offs': 'S',
		}

		final_name = obj_name.lower()
		if obj_name.lower() not in ground_dict:
			# print('%s not in ground_dict' % (obj_name.lower()))
			names = [k for k in obj_name.keys()]
			best_name = min(names, key=lambda k: nltk.edit_distance(k, obj_name.lower()))
			if nltk.edit_distance(best_name, obj_name.lower()) < 3:
				final_name = best_name
			else:
				return []

		# print('final name: %s' % (final_name,))

		coords = []
		terr = self.active_terrain()
		for i in range(len(terr)):
			for j in range(len(terr[0])):
				if ground_dict[final_name] == terr[i][j]:
					coords.append((i, j))

		return coords

	# BFS for a path from (x, y) coordinates src to dst.
	# src and dst coordinates are within the transposed terrain space.
	# Returns the list of coordinates along the path, including src and dst.
	def get_path(self, src, dst, allow_dynamic_obstacles=True, allow_dst_adjacency=False):
		obstacles = [' ']
		if allow_dynamic_obstacles:
			obstacles.append('i')

		terrain = self.active_terrain()
		if terrain is None:
			return []

		# if allow_dst_adjacency:
			# print('adding dst type %s to OK tile list' % (terrain[dst[0]][dst[1]],))
			# obstacles.append(terrain[dst[0]][dst[1]])

		seen = set()
		queue = [src]
		trace = dict()

		while len(queue) > 0:
			pop = queue[0]
			seen.add(pop)
			queue = queue[1:]
			neighbors = []
			if pop[0] > 0:
				neighbors.append((pop[0]-1, pop[1]))
			if pop[0] < len(terrain):
				neighbors.append((pop[0]+1, pop[1]))
			if pop[1] > 0:
				neighbors.append((pop[0], pop[1]-1))
			if pop[1] < len(terrain[0]):
				neighbors.append((pop[0], pop[1]+1))
			neighbors = [n for n in neighbors if n not in seen]
			neighbors = [n for n in neighbors if (terrain[n[0]][n[1]] in obstacles) or (n==dst and allow_dst_adjacency)]

			for n in neighbors:
				trace[n] = pop

			if dst in neighbors:
				break

			# Enqueue each neighbor
			queue = queue + neighbors

		if dst not in trace:
			return []

		# Build the path from the traces
		cursor = dst
		path = []
		while True:
			if cursor != dst or (terrain[dst[0]][dst[1]] in obstacles):
				path.append(cursor)
			if cursor not in trace:
				break
			cursor = trace[cursor]

		return path[::-1]

	# Transforms a set of path coordinates, including
	# src and dst coordinates, into directional move actions.
	def path_to_move_actions(self, path):
		moves = []
		for i in range(1, len(path)):
			coord = path[i]
			last = path[i-1]
			if coord[0] > last[0]:
				moves.append(Direction.EAST)
			elif coord[0] < last[0]:
				moves.append(Direction.WEST)
			elif coord[1] < last[1]:
				moves.append(Direction.NORTH)
			else:
				moves.append(Direction.SOUTH)

		return moves

	def build_state_dict(self):
		state = dict()

		nones = 0
		t = self.active_terrain()
		if PRINT_TERRAIN:
			for l in t:
				print(''.join(l))
			print('')

		# Mark all stoves with cooked soup
		game_state = self.state.to_dict()
		if 'objects' in game_state:
			for obj in game_state['objects']:
				(x, y) = obj['position']
				if obj['name'] == 'soup' and obj['is_ready']:
					t[x][y] = '^'

		# Add full ovens
		for obj in self.state.to_dict()['objects']:
			if obj['name'] == 'soup' and len(obj['_ingredients']) == 3:
				(x, y) = obj['position']
				if obj['is_ready']:
					t[x][y] = 'R'
				else:
					t[x][y] = 'r'

		# Add pos predicates for both players
		for i in range(len(game_state['players'])):
			state['p%d_pos' % i] = {'player': 'p%d' % i, 'pos': '%d,%d' % game_state['players'][i]['position']}

		# Add targeted-square predicates for both players
		for i in range(len(game_state['players'])):
			player = game_state['players'][i]
			(x, y) = player['position']
			(dx, dy) = player['orientation']
			(tx, ty) = (x+dx, y+dy)
			# print('player %d is at (%d, %d) and is facing (%d, %d)' % (i, x, y, dx, dy))
			state['p%d_targeting' % i] = {'player': 'p%d' % i, 'targeted': '%d,%d' % (tx, ty)}

		# Add holding predicates for both players
		for i in range(len(game_state['players'])):
			player = game_state['players'][i]
			holding = 'nothing'
			if player['held_object'] is not None:
				holding = player['held_object']['name']
			# print('setting p%d held item to %s' % (i, holding))
			state['p%d_holding' % i] = {'player': 'p%d' % i, 'pred': 'holding', 'obj': holding}

		for x in range(len(t)):
			for y in range(len(t[0])):
				cell = t[x][y]
				if cell == ' ' or cell == 'i':
					# Mark all cell neighbors of all open cells
					neighbors = []
					# EAST
					if x > 0:
						neighbors.append(t[x-1][y])
					else:
						neighbors.append('$')
					# WEST
					if x < len(t)-1:
						neighbors.append(t[x+1][y])
					else:
						neighbors.append('$')
					# NORTH
					if y > 0:
						neighbors.append(t[x][y-1])
					else:
						neighbors.append('$')
					# SOUTH
					if y < len(t[0])-1:
						neighbors.append(t[x][y+1])
					else:
						neighbors.append('$')

					cell_id = 'cell_%d_%d' % (x, y)
					cell_dict = {'cell_id': cell_id, 'neighbors': ''.join(neighbors), "pos": "%d,%d" % (x, y)}
					state[cell_id] = cell_dict

		return state

	def send_state(self):
		while True:
			# print('send_state looped')
			sleep(0.1)
			# if self.action_tick > 0:
				# continue
			if not self.dirty_bit_ss:
				continue
			else:
				self.dirty_bit_ss = False

			if self.block_htn:
				continue
			state_dict = {}
			if self.state is not None:
				# state_dict = {'p1_pos': {'id': 'p1_pos', 'value': ','.join([str(e) for e in self.state.players[0].position])}}
				# print('building')
				state_dict = self.build_state_dict()
				# print('done')
			# print('sending state %s' % (state_dict,))
			# self.env.state_queue_w.send(state_dict)
			# print('sent')

	def iterate_htn(self):
		while True:
			# print('iterate looped')
			task = 'make_onion_soup'
			sleep(0.1)

			if not self.dirty_bit_ihtn:
				continue
			else:
				self.dirty_bit_ihtn = False

			if self.block_htn:
				continue
			# task = "nothin"
			# print('ticking HTN')
			# self.agent.request({"pos": "1,1"}, task)
			# self.env.state_queue_w.send({})
			state_dict = {}
			if self.state is not None:
				# state_dict = {'p1_pos': {'id': 'p1_pos', 'value': ','.join([str(e) for e in self.state.players[0].position])}}
				state_dict = self.build_state_dict()
			self.agent.request(state_dict, task)

	def pos_dist(self, pos1, pos2):
		return abs(pos1[0]-pos2[0]) + abs(pos1[1]-pos2[1])

	def state_diff(self, state1, state2):
		for k in state1.keys():
			if state1[k] != state2[k]:
				# print('%s differs: %s -> %s' % (k, state1[k], state2[k]))
				pass

	def handle_pathing(self):
		if self.target_pos is None:
			return None
		if self.ai_player_pos() == self.target_pos or (self.pos_dist(self.ai_player_pos(), self.target_pos) <= 1 and self.pathing_to_obj):
			# print('done')
			if self.pathing_to_obj:
				if not self.turning_to_target_obj:
					self.turning_to_target_obj = True
					face_movement = (self.target_pos[0]-self.ai_player_pos()[0], self.target_pos[1]-self.ai_player_pos()[1])
					return face_movement
				else:
					self.turning_to_target_obj = False
					# print('next to target pos of %s' % (self.target_pos,))
			# else:
				# print('at target pos of %s' % (self.target_pos,))
			self.have_acted = False
			block_htn = False
			self.target_pos = None
			self.pathing_to_obj = False
			return None
		else:
			# print('still pathing to %s' % (self.target_pos,))
			# print('	 currently at %s' % (self.ai_player_pos(),))

			# Check to see if we just moved for the other
			# player. If we did, and they haven't moved
			# again yet, we'll keep waiting.
			if self.waiting_player_pos is not None:
				if self.waiting_player_pos == self.state.players[0].position:
					# print('just got out of your way; waiting for you to move')
					return Action.STAY
				else:
					# print("good, you moved! I'm gonna keep going now")
					self.waiting_player_pos = None

			# Path to the target and take the first step

			# First, try pathing around the other player
			moves = self.path_to_move_actions(self.get_path(self.ai_player_pos(), self.target_pos, allow_dynamic_obstacles=False, allow_dst_adjacency=self.pathing_to_obj))
			# print('got moves: %s' % moves)
			if len(moves) == 0:
				# If there's a path through another player, we can
				# try to shove them out of the way...
				moves = self.path_to_move_actions(self.get_path(self.ai_player_pos(), self.target_pos, allow_dynamic_obstacles=True, allow_dst_adjacency=self.pathing_to_obj))
				if len(moves) == 0:
					self.target_pos = None
					return None

			# Check that the next step is possible
			move = moves[0]
			# print('move is %s' % (move,))
			terrain = self.active_terrain()
			(x, y) = self.ai_player_pos()
			(dx, dy) = move
			target = (x+dx, y+dy)
			# print('	 trying to go to %s' % (target,))
			if terrain[target[0]][target[1]] == ' ':
				return move
			else:
				# There's probably a player in the way. If they're looking at us,
				# assume they're trying to shove us out of the way, and
				# step back one.
				their_pos = self.state.players[0].position
				if their_pos == target:
					(their_x, their_y) = their_pos
					(face_x, face_y) = self.state.players[0].orientation
					their_target = (their_x+face_x, their_y+face_y)
					if their_target == self.ai_player_pos():
						# print('moving out of your way')
						self.waiting_player_pos = (their_x, their_y)
						return (face_x, face_y)

				# print('next location blocked; waiting')
				return Action.STAY

	def action(self, state):
		# print('action called')
		if self.first_action:
			self.first_action = False
			return Action.STAY, None

		'''
		if state.timestep <= self.last_timestep:
			print('timestep %s is BEFORE last timestep %s!' % (state.timestep, self.last_timestep))
			return Action.STAY, None
		else:
			self.last_timestep = state.timestep
		'''

		# Let the ticks stabilize out to guarantee a fresh state
		self.action_tick = (self.action_tick+1)%2
		if self.action_tick > 0:
			return Action.STAY, None

		# print('htn_ai setting state to %s' % state.to_dict())
		self.state = state.deepcopy()
		self.dirty_bit_ss = True
		self.dirty_bit_ihtn = True

		# print(state.to_dict())
		if PRINT_STATE:
			print(dumps(state.to_dict(), sort_keys=True, indent=4))

		# sleep(0.5)
		# print('timestep is %s' % (state.to_dict()['timestep']))
		# print('got state p1 pos %s' % (state.players[1].position,))
		self.block_htn = True
		# return Action.STAY, None

		move = self.handle_pathing()
		if move is not None:
			# print('in 1, got move %s' % (move,))
			self.have_acted = True
			return move, None

		# Send a state, unblocking the HTN
		# self.env.state_queue_w.send({"pos": "1,1"})
		self.block_htn = False

		# t = self.active_terrain()
		# for l in t:
			# print(''.join(l))
		# print('')

		# print('coords: %s' % (self.ground_object('onion')))

		# Don't wait on a SAI if we know the HTN is blocked from
		# producing one
		if self.block_htn:
			return Action.STAY, None
		# sigs, _, _ = select([self.env.sai_queue_r], [], [])
		# Block on the SAI queue in the env to get the
		# next action
		'''
		print('waiting on a sai')
		sig = select([self.env.sai_queue_r], [], [], timeout=0.5)
		if all([(len(x)==0) for x in sig]):
			print('timed out')
			return Action.STAY, None
		(s, a, i) = sig[0][0].recv()
		'''

		sleep(1)
		if self.collect_state_after_action:
			# print('adding state %s' % (self.build_state_dict(),))
			# print('diff: ', end='')
			# self.state_diff(self.state_snapshots[-1], self.build_state_dict())
			self.collect_state_after_action = False
			self.state_snapshots.append(self.build_state_dict())

		# inp = input('Enter action: ').strip()
		if len(self.inp_queue) == 1 and self.inp_queue[0] == 'SENTINEL':
			# print('%d states for %d actions' % (len(self.state_snapshots), self.last_inp_queue_size))
			# for i in range(len(self.old_inp_queue)-1):
				# print('ACTION: %s' % (self.old_inp_queue[i],))
				# print('\tSTATE: %s' % (self.state_snapshots[i+1],))
				# self.state_diff(self.state_snapshots[i], self.state_snapshots[i+1])
			self.inp_queue = []
			self.old_inp_queue = []
			self.state_snapshots = []
		if len(self.inp_queue) == 0:
			# inp = input('Enter action: ').strip()
			if self.need_inp:
				# self.itl.save('val_model.pkl')
				print('VAL: What should I do?')
				print('User: ', end='')
				self.need_inp = False
			# inp, onp, enp = select.select([sys.stdin], [], [], 5)
			# if inp:
				# self.need_inp = True
				# inp = sys.stdin.readline().strip()
			# else:
				# return Action.STAY, None
			inp = wait_input()
			sleep(0.5)
			if inp:
				self.need_inp = True
			else:
				# print('staying')
				return Action.STAY, None
			with open(SESS_ID, 'a+') as f:
				# f.write('Enter action: ')
				f.write('VAL: What should I do?\n')
			with open(SESS_ID, 'a+') as f:
				f.write('User: ' + inp + '\n')

			def clarify_hook2(ua):
				# inp = input('What do you mean by "%s"?: ' % (ua,))
				print('VAL: What do you mean by "%s"?' % (ua,))
				print('User: ', end='')
				inp = wait_input()
				while True:
					if inp is None:
						inp = wait_input()
					else:
						break
				with open(SESS_ID, 'a+') as f:
					f.write('VAL: What do you mean by "%s"?\n' % (ua,))
					f.write('User: ' + inp + '\n')
				with open('speech_outf', 'a+') as f:
					f.write('What do you mean by "%s"?\n' % (ua,))

				return inp

			self.inp_queue = self.itl.process_instruction(inp, clarify_hook=clarify_hook2) + ['SENTINEL']
			self.old_inp_queue = self.inp_queue[:]
			self.last_inp_queue_size = len(self.inp_queue)-1
			self.state_snapshots.append(self.build_state_dict())

		sleep(1.5)
		inp = self.inp_queue[0]
		self.inp_queue = self.inp_queue[1:]
		# print('PULLING %s from inp_queue' % (inp,))


		s = None
		a = inp.split(' ')[0].strip()
		i = {'value': ','.join([x.strip() for x in inp.split(' ')[1:]])}

		# print('got the sai')
		a = a.lower()
		self.collect_state_after_action = True
		if a == "moveup":
			return Direction.NORTH, None
		elif a == "movedown":
			self.pause_ticks = 5
			return Direction.SOUTH, None
		elif a == "movetoloc":
			# print('GAME TAKING ACTION: moveto %s' % (i,))
			(x, y) = [int(e) for e in i['value'].split(',')]
			self.target_pos = (x, y)
			self.block_htn = True
			'''
			move = self.handle_pathing()
			if move is not None:
				print('in 2, got move %s' % (move,))
				return move, None
			else:
				# block_htn = False
				return Action.STAY, None
			'''
			return Action.STAY, None
		elif a == 'moveto':
			obj = i['value']
			# print('GAME TAKING ACTION: movetoobject %s' % (obj,))

			# Find all the places with matching objects
			possible_spots = self.ground_object(obj)

			# Iterate through until we find one we can path to

			# Re-iterate, if there are no spots, allowing
			# dynamic obstacles
			found = False
			for spot in possible_spots:
				path = self.get_path(self.ai_player_pos(), spot, allow_dynamic_obstacles=False, allow_dst_adjacency=True)
				if len(path) > 0:
					# print('chose %s at spot %s' % (obj, spot))
					found = True
					self.target_pos = spot
					self.pathing_to_obj = True
					self.block_htn = True
					break
			if not found:
				for spot in possible_spots:
					path = self.get_path(self.ai_player_pos(), spot, allow_dynamic_obstacles=True, allow_dst_adjacency=True)
					if len(path) > 0:
						# print('chose %s at spot %s' % (obj, spot))
						found = True
						self.target_pos = spot
						self.pathing_to_obj = True
						self.block_htn = True
						break
			if not found:
				print("couldn't find an '%s' object" % (obj))

			return Action.STAY, None
			
		elif a == "move":
			# print('GAME TAKING ACTION: move %s' % (i,))
			# print('moving %s' % i['value'])
			(x, y) = [int(e) for e in i['value'].split(',')]
			self.have_acted = True
			return (x, y), None
		elif a == "interactwithobject" or a == "pressspace":
			# print('GAME TAKING ACTION: interact')
			self.have_acted = True
			return Action.INTERACT, None
		elif a == "wait":
			# print('GAME TAKING ACTION: wait')
			return Action.STAY, None
		else:
			# print("unknown SAI %s, %s, %s" % (s, a, i))
			self.collect_state_after_action = False
			return Action.STAY, None

	def reset(self):
		pass
