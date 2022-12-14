from copy import deepcopy
from json import dumps
from select import select
from threading import Thread
from time import sleep

from overcooked_ai_py.mdp.actions import Action, Direction

from tutorenvs.overcooked import OvercookedTutorEnv

from HTNAgent.htn_overcooked_operators import overcooked_methods, overcooked_actions
from HTNAgent.tact_agent import TACTAgent

PRINT_TERRAIN = False
PRINT_STATE = False

class HTNAI():
    def __init__(self, game):
        self.dirty_bit_ss = False
        self.dirty_bit_ihtn = False

        self.have_acted = False
        self.game = game
        self.action_tick = 0
        self.state = None
        self.env = OvercookedTutorEnv()
        self.agent = TACTAgent(actions=overcooked_actions, methods=overcooked_methods, relations=[], env=self.env)

        self.waiting_player_pos = None

        self.state_dirty_bit = False
        self.state_hash = None

        self.block_htn = False

        self.last_timestep = -1

        # self.target_pos = (1, 2)
        self.target_pos = None

        # Send an initial state, including a target pos
        # self.env.state_queue_w.send({"pos": "1,1"})

        # Run the HTN planner in the background, iterating
        # with the same task over and over
        Thread(target=self.iterate_htn).start()
        Thread(target=self.send_state).start()

        self.pause_ticks = 0

        self.target_pos

        # self.env.state_queue_w.send({})

    def ai_player_pos(self):
        return self.state.players[1].position

    # Returns the game terrain grid, populated with
    # current player positions (and, maybe one day,
    # other "dynamic obstacles"?)
    def active_terrain(self):
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

    # BFS for a path from (x, y) coordinates src to dst.
    # src and dst coordinates are within the transposed terrain space.
    # Returns the list of coordinates along the path, including src and dst.
    def get_path(self, src, dst, allow_dynamic_obstacles=True):
        obstacles = [' ']
        if allow_dynamic_obstacles:
            obstacles.append('i')

        terrain = self.active_terrain()
        if terrain is None:
            return []

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
            neighbors = [n for n in neighbors if terrain[n[0]][n[1]] in obstacles]

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
            print('player %d is at (%d, %d) and is facing (%d, %d)' % (i, x, y, dx, dy))
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
            print('send_state looped')
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
                print('building')
                state_dict = self.build_state_dict()
                print('done')
            print('sending state %s' % (state_dict,))
            self.env.state_queue_w.send(state_dict)
            print('sent')

    def iterate_htn(self):
        while True:
            print('iterate looped')
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

    def handle_pathing(self):
        if self.target_pos is None:
            return None
        if self.ai_player_pos() == self.target_pos:
            # print('done')
            print('at target pos of %s' % (self.target_pos,))
            self.have_acted = False
            block_htn = False
            self.target_pos = None
            return None
        else:
            print('still pathing to %s' % (self.target_pos,))
            print('     currently at %s' % (self.ai_player_pos(),))

            # Check to see if we just moved for the other
            # player. If we did, and they haven't moved
            # again yet, we'll keep waiting.
            if self.waiting_player_pos is not None:
                if self.waiting_player_pos == self.state.players[0].position:
                    print('just got out of your way; waiting for you to move')
                    return Action.STAY
                else:
                    print("good, you moved! I'm gonna keep going now")
                    self.waiting_player_pos = None

            # Path to the target and take the first step

            # First, try pathing around the other player
            moves = self.path_to_move_actions(self.get_path(self.ai_player_pos(), self.target_pos, allow_dynamic_obstacles=False))
            if len(moves) == 0:
                # If there's a path through another player, we can
                # try to shove them out of the way...
                moves = self.path_to_move_actions(self.get_path(self.ai_player_pos(), self.target_pos, allow_dynamic_obstacles=True))
                if len(moves) == 0:
                    self.target_pos = None
                    return None

            # Check that the next step is possible
            move = moves[0]
            print('move is %s' % (move,))
            terrain = self.active_terrain()
            (x, y) = self.ai_player_pos()
            (dx, dy) = move
            target = (x+dx, y+dy)
            print('     trying to go to %s' % (target,))
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
                        print('moving out of your way')
                        self.waiting_player_pos = (their_x, their_y)
                        return (face_x, face_y)

                # print('next location blocked; waiting')
                return Action.STAY

    def action(self, state):
        print('action called')

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

        print('htn_ai setting state to %s' % state.to_dict())
        self.state = state.deepcopy()
        self.dirty_bit_ss = True
        self.dirty_bit_ihtn = True

        # print(state.to_dict())
        if PRINT_STATE:
            print(dumps(state.to_dict(), sort_keys=True, indent=4))

        # sleep(0.5)
        # print('timestep is %s' % (state.to_dict()['timestep']))
        print('got state p1 pos %s' % (state.players[1].position,))
        self.block_htn = True
        # return Action.STAY, None

        move = self.handle_pathing()
        if move is not None:
            print('in 1, got move %s' % (move,))
            self.have_acted = True
            return move, None

        # Send a state, unblocking the HTN
        # self.env.state_queue_w.send({"pos": "1,1"})
        self.block_htn = False

        t = self.active_terrain()
        '''
        for l in t:
            print(''.join(l))
        print('')
        '''

        # Don't wait on a SAI if we know the HTN is blocked from
        # producing one
        if self.block_htn:
            return Action.STAY, None
        # sigs, _, _ = select([self.env.sai_queue_r], [], [])
        # Block on the SAI queue in the env to get the
        # next action
        print('waiting on a sai')
        sig = select([self.env.sai_queue_r], [], [], timeout=0.5)
        if all([(len(x)==0) for x in sig]):
            print('timed out')
            return Action.STAY, None
        (s, a, i) = sig[0][0].recv()
        print('got the sai')
        if a == "MoveUp":
            return Direction.NORTH, None
        elif a == "MoveDown":
            self.pause_ticks = 5
            return Direction.SOUTH, None
        elif a == "MoveTo":
            print('GAME TAKING ACTION: moveto %s' % (i,))
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
        elif a == "Move":
            print('GAME TAKING ACTION: move %s' % (i,))
            print('moving %s' % i['value'])
            (x, y) = [int(e) for e in i['value'].split(',')]
            self.have_acted = True
            return (x, y), None
        elif a == "Interact":
            print('GAME TAKING ACTION: interact')
            self.have_acted = True
            return Action.INTERACT, None
        elif a == "Wait":
            print('GAME TAKING ACTION: wait')
            return Action.STAY, None
        else:
            print("unknown SAI %s, %s, %s" % (s, a, i))
            return Action.STAY, None

    def reset(self):
        pass
