### Eclipse battle calculator

import numpy as np
import time
import matplotlib.pyplot as plt



import re


def listToTuple (integer_list):
    tuple = ()
    for integer in integer_list:
        tuple += (integer,)
    return (tuple)

def tupleToList (integer_tuple):
    list = []
    for integer in integer_tuple:
        list += (integer,)
    return (list)

def sortAndRemoveDuplicates (l):
    l = list(set(l))
    l.sort()
    return (l)

class Ship:
    def __init__ (self, type, number, init, hull, computer, shield, canon_array, missile_array):
        self.type = type #"int" interceptor, "cru" cruiser, "dre" dreadnought, "sba" starbase
        self.prio = 0 #the priority for ancients
        if   (type =="int"):
            self.prio = 1
        elif (type =="sba"): # we consider that a starbase is bigger than an int, but smaller than a cru based on blueprint size
            self.prio = 10 #strictly more than all ints
        elif (type =="cru"):
            self.prio = 100 #strictly more than all sbas
        elif (type =="dre"):
            self.prio = 1000 #strictly more than all crus

        self.numb = number #how many ships of that type there are
        self.init = init   #how much intiative they have
        self.hull = hull
        self.comp = computer
        self.shie = shield
        self.canon_array = np.array(canon_array  ) # [y, o, b, r, p], y = number of yellow dice, o = number of orange dice etc
        self.missi_array = np.array(missile_array) # [y, o, b, r, p], same

    def toString (self):
        response = str(self.numb)+" "
        response+= (self.type=="int")*"interceptor" +(self.type=="cru")*"cruiser" +(self.type=="dre")*"dreadnought" +(self.type=="sba")*"starbase" +(self.type=="npc")*"npc"
        response+= (self.numb>1)*"s" + " with "+str(self.init)+" initiative, "
        if (self.hull>0):
            response +=     str(self.hull)+" hull, "
        if (self.comp>0):
            response += '+'+str(self.comp)+" computer, "
        if (self.shie>0):
            response += '-'+str(self.shie)+" shield, "
        colors = ["yellow", "orange", "blue", "red", "pink"]
        for i in range (5):
            if self.canon_array[i]>0:
                response += str(self.canon_array[i])+' '+ colors[i] + " canon"    +(self.canon_array[i]>1)*"s" +", "
        for i in range (5):
            if self.missi_array[i]>0:
                response += str(self.missi_array[i])+' '+ colors[i] + " missile"  +(self.missi_array[i]>1)*"s" +", "
        if self.canon_array[4]+self.missi_array[4]>0:
            response += "**WARNING! PINK DICE NOT SUPPORTED FOR NOW!, ** "
        return (response[:-2]) #remove the last space and ,
            


class BattleWinChances:
    def __init__ (self, attacker_ship_list, defender_ship_list, remaining_ships = True): 
        self.att_ship_list = attacker_ship_list
        self.def_ship_list = defender_ship_list
        # State of battle is one big array, with each coordinate corresponding to : 
        # 0: round initiative order 
        # 1-end-1 : remaining hit points of every single ship, starting with attacker ships
        # end : 0 for attacker, 1 for defender
        size_round = len (self.att_ship_list) + len (self.def_ship_list)
        self.att_ships = []
        ship_index = 0
        ship_types = [] # a list of id to see when two consecutive ships are of the same type
        self.ship_prios = []

        self.graph_edges = [] # a list to read the state graph


        for ship in attacker_ship_list:
            self.att_ships += [blockSize (ship.numb, ship.hull)]
            self.ship_prios += [ship.prio]

            self.graph_edges.append (makeGraph (ship.numb, ship.hull))
        
        self.def_ships = []

        self.att_index = 1            # the index at which attack  ships start
        self.def_index = 1+len(attacker_ship_list) # the index at which defense ships start
        ship_index = 0
        for ship in defender_ship_list:
            self.def_ships += [blockSize (ship.numb, ship.hull)]
            self.ship_prios += [ship.prio]

            self.graph_edges.append (makeGraph (ship.numb, ship.hull))

        dims = [2* size_round] + self.att_ships +self.def_ships #turn (with missiles), att ships hp, def ships hp
        self.state_win_chance = np.zeros ( dims ) 
        self.state_win_chance [Ellipsis] = -1000000.0 # uninitialized value, it's high so that I can detect errors

        # step 2: turn order
        #find highest initiative
        max_init = 0
        for ship in self.att_ship_list:
            max_init = max(max_init, ship.init)
        for ship in self.def_ship_list:
            max_init = max(max_init, ship.init)
        # order ships by increasing initiative, 
        self.turn_order = [] 
        for init in range (max_init+1):
            for id in range(len(self.att_ship_list)):
                if (self.att_ship_list[id].init==init):
                    self.turn_order.append ( ("att", id) )
            # range defense ship afterward so that they shoot first in case of a tie
            for id in range(len(self.def_ship_list)):
                if (self.def_ship_list[id].init==init):
                    self.turn_order.append ( ("def", id) )
        #step3: compute transition table 
        self.transitionTable()

        #step 4: propagate win chance backward (=in increasing number hit points)
        index = [-1] #initialize index at -1 0 ... 0
        for _ in range (len(self.att_ships) + len(self.def_ships)):
            index += [0]
        all_ships = self.att_ships + self.def_ships

        total_ship_states = 1 # number of hp combinations
        for ship in (self.att_ship_list+ self.def_ship_list):
            total_ship_states *= blockSize (ship.numb, ship.hull)
        
        for _ in range (total_ship_states):
            self.computeWinChance (index)

            for ship in range (len(self.att_ships) + len(self.def_ships)):
                if (all_ships[ship] - index[ship+1]>1):
                    index[ship+1]+= 1
                    break
                else:
                    index[ship+1] = 0

        # return win chance 
        start_index = []
        for d in dims:
            start_index += [d-1]
        self.initial_win_chance = self.state_win_chance[listToTuple(start_index)]

        if (remaining_ships):

            #step 5: propagate state probability forward (=in decreasing number hit points)
            self.att_win_chance = 0.0 # to check results
            self.def_win_chance = 0.0 # to check results
            self.state_expectancy = np.zeros ( [2* size_round] + self.att_ships +self.def_ships ) # array with the probability of each state

            self.state_expectancy[listToTuple(start_index)]=1.0 #initial state is guaranteed to happen
            index = start_index

            self.att_still_alive = [[0.0 for i in range (ship.numb)] for ship in self.att_ship_list]
            self.def_still_alive = [[0.0 for i in range (ship.numb)] for ship in self.def_ship_list]

            for _ in range (total_ship_states):
                self.computeExpectancy (index)

                for ship in range (len(self.att_ships) + len(self.def_ships)):
                    if (index[ship+1]>0):
                        index[ship+1]-= 1
                        break
                    else:
                        index[ship+1] = all_ships[ship]-1

            
            ship_names = [] # for legend
            xplacement = [] # place of the bar along the x axis
            bar_colors = [] # to differentiate att and def
            x_value = 1
            still_alive = []
            for ship_id in range(len(self.att_ship_list)):
                ship = self.att_ship_list[ship_id]
                still_alive += self.att_still_alive [ship_id]
                for n in range (1, ship.numb+1):
                    if (n==ship.numb):
                        ship_names += [str(n) + " "  + ship.type ]
                    else :
                        ship_names += [str(n) + "+ " + ship.type ]
                    bar_colors += ["blue"]
                    xplacement += [x_value]
                    x_value += 1
                x_value += 1
            x_value += 1
            for ship_id in range(len(self.def_ship_list)):
                ship = self.def_ship_list[ship_id]
                still_alive += self.def_still_alive [ship_id]
                for n in range (1, ship.numb+1):
                    if (n==ship.numb):
                        ship_names += [str(n) + " "  + ship.type ]
                    else :
                        ship_names += [str(n) + "+ " + ship.type ]
                    bar_colors += ["red"]
                    xplacement += [x_value]
                    x_value += 1
                x_value += 1

            fig, ax = plt.subplots()
            bars = ax.bar(xplacement, still_alive, color = bar_colors)

            ax.set_xticks (xplacement)
            ax.set_xticklabels (ship_names)
            ax.set_yticks ([])

            percentages = ["{:.2%}".format(p) for p in still_alive]

            ax.bar_label(bars, percentages)
            ax.set_title ("Survival chance")

            plt.savefig ('battle.jpg', bbox_inches = 'tight')
            print ("win chance", self.att_win_chance, self.def_win_chance)

    def computeWinChance (self, ship_index) :
        
        turn_size = len (self.att_ship_list) + len (self.def_ship_list)

        #check whether there is at least 1 ship alive
        att_hp =0
        def_hp =0
        for i in range (self.att_index, self.def_index ):
            att_hp += ship_index[i]
        for i in range (self.def_index, len(ship_index)):
            def_hp += ship_index[i]
        if   (att_hp==0) :
            #attacker lost
            for turn in range (2*turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn
                self.state_win_chance[listToTuple (cur_index)] = 0.0

        elif (def_hp==0) :
            #attacker won
            for turn in range (2*turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn
                self.state_win_chance[listToTuple (cur_index)] = 1.0

        else :
            # step 1: compute chance of canon rounds
            # because canon rounds loop back on themselves, the win chance of the entire round are defined implicitly as solution of a linear system
            A = np.zeros ((turn_size, turn_size))
            b = np.zeros ( turn_size )
            

            for turn in range (turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn
                (win_chance, proba_full_miss) = self.computeStateWinChance (cur_index)
                b[turn] = win_chance
                A[turn, turn] = 1
                
                if (turn == 0):
                    A[turn, turn_size-1] =-proba_full_miss
                else :
                    A[turn, turn     -1] =-proba_full_miss
            x = np.linalg.solve(A, b)
            #x = np.linalg.solve(np.transpose(A), b)

            for turn in range (turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn

                tuple = listToTuple (cur_index)
                tuple += (Ellipsis,) # for both attacker and defender

                self.state_win_chance[tuple] = x[turn]


            #step 2: compute missiles
            for turn in range (turn_size, 2*turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn
                (win_chance, proba_full_miss) = self.computeStateWinChance (cur_index)

                cur_index[0] = turn-1
                tuple = listToTuple (cur_index)
                win_chance += proba_full_miss*self.state_win_chance[tuple]

                cur_index[0] = turn
                tuple = listToTuple (cur_index)

                self.state_win_chance[tuple] = win_chance
                
    def readStateInfo (self, current_state):
        # reads and returns relevant information for state operations
        turn_size = len (self.att_ship_list) + len (self.def_ship_list)
        # which ship is firing ?
        after_damage_state = current_state.copy()
        turn = after_damage_state[0]

        if turn < turn_size :
            firing_ship_side = self.turn_order[turn          ][0]
            firing_ship_id   = self.turn_order[turn          ][1]
        else:
            #missile round
            firing_ship_side = self.turn_order[turn-turn_size][0]
            firing_ship_id   = self.turn_order[turn-turn_size][1]

        # how many of them are alive ?
        
        if firing_ship_side == "att":
            first_index = self.att_index #counting an attack ship
            ally_ship_list = self.att_ship_list
            enmy_ship_list = self.def_ship_list
        else:
            first_index = self.def_index #counting a defense ship
            ally_ship_list = self.def_ship_list
            enmy_ship_list = self.att_ship_list

        firing_ship = ally_ship_list [firing_ship_id]

        alive = self.graph_edges[first_index+firing_ship_id-1][0][current_state[first_index+firing_ship_id]]

        # what's next turn ?
        if turn == 0:
            after_damage_state[0] = len (self.att_ship_list) + len (self.def_ship_list) -1
        else :
            after_damage_state[0] = turn -1
        

        
        if firing_ship_side == "att":
            sign = 1
            indexes = [self.def_index, len (current_state), self.att_index, self.def_index] # canon fire on def ships, rift canons fire on att ships
        else:
            sign =-1 #attack maximize winrate, defense minimize win rate
            indexes = [self.att_index, self.def_index,self.def_index, len (current_state)] # canon fire on att ships, rift canons fire on def ships
        

        npc_flag = False # tells whether we need to use npc targeting rule
        prio_list = []
        if firing_ship.type=="npc":
            npc_flag = True
            prio_list = [ship.prio for ship in enmy_ship_list]
        prio_rift_list = []
        for ship in ally_ship_list:
            if ship.canon_array[4]>0:
                prio_rift_list.append (ship.prio)
            else:
                prio_rift_list.append (0)

        return (turn, sign, after_damage_state, indexes, alive, npc_flag, prio_list, prio_rift_list)

    def computeStateWinChance (self, current_state) :
        # Writes and solves the win chance equation for the hp state for all round 
        # round number is added at the start of the index

        turn, sign, after_damage_state, indexes, alive, npc_flag, prio_list, prio_rift_list = self.readStateInfo (current_state)

        if alive >0:
            win_chance = 0.0
            damages_per_result = self.transition_table [turn][alive-1] # list of outcomes with each a proba and all possible damage assignements
            for _ in range (len(damages_per_result)-1 ): # for each dice result (last is full miss)
                damages = damages_per_result[_]
                proba = damages[0]

                after_damage_state2 = self.applySelfHits (damages[1], after_damage_state, indexes[2], indexes[3], prio_rift_list)

                max_chance, best_next_state = self.findBestAssignment (sign, after_damage_state2, indexes[0], indexes[1], damages[2:], npc_flag, prio_list)

                win_chance += proba*sign*max_chance
            
            proba_full_miss = damages_per_result[-1][0]
        
        else:
            win_chance =0
            proba_full_miss = 1.0

        return (win_chance, proba_full_miss)

    def applySelfHits (self, self_hits, state_before_hits, first_index, last_index, prio_rift_list):

        if self_hits==0:
            return (state_before_hits) # no need to do the rest if there are no self hits

        # create a list of possible assignments
        nb_ally_ships = last_index - first_index
        damage_repartition = [0 for _ in range (nb_ally_ships-1)]
        total_possibilities = blockSize (nb_ally_ships-1, self_hits) # number of possible damage assignments
        damage_list = []
        unassigned_hits = self_hits
        for _ in range (nb_ally_ships):
            damages = [0 for _ in range (nb_ally_ships*4)]
            for i in range (nb_ally_ships-1):
                if unassigned_hits >=1:
                    damage_repartition[i]+=1
                else :
                    unassigned_hits += damage_repartition[i]
                    damage_repartition[i] = 0
            damages [(nb_ally_ships-1)*4] = unassigned_hits

            damage_list.append (listToTuple(damages))

        sign = 1 #does not matter
        npc_flag = True # rift follow the same rules as npcs
        max_chance, best_next_state = self.findBestAssignment (sign, state_before_hits, first_index, last_index, damage_list, npc_flag, prio_rift_list)

        return (best_next_state)

    def findBestAssignment (self, sign, state, first_index, last_index, assignment_list, npc_flag=False, prio_list = []):
        max_chance = -1000.0
        best_next_state = state 

        BIG = 100000 # number that is much bigger than any number encoutered in the following part

        min_kill_score = BIG # npc targeting : counts how many ships are dead, weighted by their prio
        min_hull_score = BIG # npc targeting : counts how much hull the biggest ship alive has

        for dam in assignment_list: # for each damage assignment
            # if the following two flag are True, then shot are going into the wrong ships
            wasted_shot_flag = False #tells if a shot went into a dead ship
            alive_ships_flag = False #tells if there is at least one enemy ship alive

            attainable_states = [ [i] for i in state[0:first_index]]

            target_nb = 0
            kill_score = 0
            hull_score = BIG
            max_prio = 0 # npc targeting : priority of the biggest ship
        
            for target_ship_id in range (first_index, last_index):

                possible_states_after_salva = [state[target_ship_id]] #current hp index

                if (state[target_ship_id]==0):
                    #all those ships are dead
                    for die in range (4, 0, -1): #check if they got hit regardless
                        if (dam[target_nb*4+die-1]>0):
                            wasted_shot_flag = True #tells if a shot went into a dead ship

                else:
                    alive_ships_flag = True
                    
                    for die in range (4, 0, -1): #dice type in decreasing order
                        for i in range (dam[target_nb*4+die-1]):
                            possible_states_after_salva_2 = []
                            if npc_flag:
                                for id in possible_states_after_salva:
                                    possible_states_after_salva_2 += self.graph_edges[target_ship_id-1][die][id][0:1] # neighbor list are sorted so that the first element correspond to npc targeting
                            else:
                                for id in possible_states_after_salva:
                                    possible_states_after_salva_2 += self.graph_edges[target_ship_id-1][die][id] 
                            # remove duplicates
                            possible_states_after_salva = sortAndRemoveDuplicates (possible_states_after_salva_2)
                
                attainable_states.append(possible_states_after_salva)
                if npc_flag:
                    alive_targets = self.graph_edges[target_ship_id-1][0][possible_states_after_salva[0]]
                    prio = prio_list[target_nb]
                    kill_score+= alive_targets*prio
                    hull= self.graph_edges[target_ship_id-1][5][possible_states_after_salva[0]] # hp of the most damaged ship among the alive ships of that type
                    if (hull>0)and(prio>max_prio):
                        max_prio = prio
                        hull_score = hull
                target_nb +=1

            attainable_states+= [ [i] for i in state[last_index:]]
            #chance = max (sign*self.state_win_chance[np.ix_(*attainable_states)].flatten())
            attainable_state_win_chance = self.state_win_chance[np.ix_(*attainable_states)]
            chance =     (sign*attainable_state_win_chance).max ()
            next_state = (sign*attainable_state_win_chance).argmax ()
            next_state = np.unravel_index (next_state, attainable_state_win_chance.shape)
            next_state = [attainable_states[i][next_state[i]] for i in range (len(attainable_states))]
            if (npc_flag):
                if   (kill_score < min_kill_score):
                    min_kill_score = kill_score
                    min_hull_score = hull_score
                    max_chance = chance
                    best_next_state = next_state
                elif (kill_score==min_kill_score)and(hull_score < min_hull_score):
                    min_hull_score = hull_score
                    max_chance = chance
                    best_next_state = next_state
                elif (kill_score==min_kill_score)and(hull_score==min_hull_score):
                    max_chance = chance
                    best_next_state = next_state

            elif (wasted_shot_flag==False)or(alive_ships_flag==False):
                if (chance >= max_chance):
                    max_chance = chance
                    best_next_state = next_state
                    
        return (max_chance, best_next_state)

    def computeExpectancy(self, turnless_state):
        turn_size = len (self.att_ship_list) + len (self.def_ship_list)
        
        #check whether there is at least 1 ship alive
        att_hp =0
        def_hp =0
        for i in range (self.att_index, self.def_index ):
            att_hp += turnless_state[i]
        for i in range (self.def_index, len(turnless_state)):
            def_hp += turnless_state[i]
        if   (att_hp==0) :
            #attacker lost, counting remaining def ships
            for turn in range (2*turn_size):
                state = turnless_state.copy ()
                state[0] = turn
                self.def_win_chance += self.state_expectancy[listToTuple (state)]

                # count how many ships are still alive
                for ship_id in range (len(self.def_ship_list)):
                    alive = self.graph_edges[self.def_index+ship_id-1][0][state[self.def_index+ship_id]]
                    for i in range (alive):
                        self.def_still_alive[ship_id][i]+=self.state_expectancy[listToTuple (state)]

        elif (def_hp==0) :
            #attacker won, counting remaining att ships
            for turn in range (2*turn_size):
                state = turnless_state.copy ()
                state[0] = turn
                self.att_win_chance += self.state_expectancy[listToTuple (state)]

                # count how many ships are still alive
                for ship_id in range (len(self.att_ship_list)):
                    alive = self.graph_edges[self.att_index+ship_id-1][0][state[self.att_index+ship_id]]
                    for i in range (alive):
                        self.att_still_alive[ship_id][i]+=self.state_expectancy[listToTuple (state)]

        else :
            # step 1 : propagate expectancy of missile rounds
            for turn in range (2*turn_size-1, turn_size-1, -1):
                state = turnless_state.copy()
                state[0] = turn
                self.propagateStateExpectancy(state, full_miss=True )
            # step 2 : compute expectancy of canon rounds by solving a linear system
            # because canon rounds loop back on themselves, the expectancy of the entire round are defined implicitly as solution of a linear system
            A = np.zeros ((turn_size, turn_size))
            b = np.zeros ( turn_size )
            

            for turn in range (turn_size):
                state = turnless_state.copy ()
                state[0] = turn
                (win_chance, proba_full_miss) = self.computeStateWinChance (state) # TODO upgrade
                b[turn] = self.state_expectancy[listToTuple(state)]
                A[turn, turn] = 1
                
                if (turn == 0):
                    A[turn, turn_size-1] =-proba_full_miss
                else :
                    A[turn, turn     -1] =-proba_full_miss
            #x = np.linalg.solve(A, b)
            x = np.linalg.solve(np.transpose(A), b)
            for turn in range (turn_size):
                state = turnless_state.copy ()
                state[0] = turn
                self.state_expectancy[listToTuple (state)] = x[turn]

            # step 3 : propagate expectancy of canon rounds 
            for turn in range (turn_size):
                state = turnless_state.copy()
                state[0] = turn
                self.propagateStateExpectancy(state, full_miss=False)
        return
    
    def propagateStateExpectancy (self, current_state, full_miss) :
        # Ranges all dice results and propagates expectancy through it

        turn, sign, after_damage_state, indexes, alive, npc_flag, prio_list, prio_rift_list = self.readStateInfo (current_state)

        if alive >0:
            damages_per_result = self.transition_table [turn][alive-1] # list of outcomes with each a proba and all possible damage assignements
            for _ in range (len(damages_per_result)-(full_miss==False) ): # for each dice result. Last result is full miss and only encountered with missile rounds
                damages = damages_per_result[_]
                proba = damages[0]

                after_damage_state2 = self.applySelfHits (damages[1], after_damage_state, indexes[2], indexes[3], prio_rift_list)

                max_chance, best_next_state = self.findBestAssignment (sign, after_damage_state2, indexes[0], indexes[1], damages[2:], npc_flag, prio_list)

                self.state_expectancy[listToTuple(best_next_state)]+=proba*self.state_expectancy[listToTuple(current_state)]

        return ()

    def transitionTable (self):
        # creates a transition table that represents thrown dice
        # indexes of the table : 
        #     0 turn order
        #     1 nb of alive ships
        # for each ship type, for each number of those ships, there will be a list of damage assignment
        # damage assignment is the probability of that plus a list of indexes that represent the hits being dealt

        self.transition_table = []
        transition_table_missiles = []

        turn_size = len (self.att_ship_list) + len (self.def_ship_list)


        for turn in range (turn_size):
            firing_ship_side = self.turn_order[turn][0]
            firing_ship_id   = self.turn_order[turn][1]

            if (firing_ship_side =="att"):
                target_list = self.def_ship_list
                target_hp = self.def_ships
                firing_ship = self.att_ship_list[firing_ship_id]
            else :
                target_list = self.att_ship_list
                target_hp = self.att_ships
                firing_ship = self.def_ship_list[firing_ship_id]

            nb_targets = len(target_hp)

            target_hit_chance = []
            for target_ship in target_list:
                target_hit_chance.append(hitChance (firing_ship.comp, target_ship.shie))
                
            #count how many outcomes there. At least 2 (hit or miss) but there might be different shields
            nb_outcomes = 0
            proba_outcomes = []
            last_i =0

            can_hit = [0 for i in range (nb_targets)]
            
            for i in range (1, 6):
                for hit_chance in target_hit_chance:
                    if i == hit_chance:
                        nb_outcomes += 1
                        proba_outcomes += [i - last_i]
                        last_i = i

                        for target_ship_id in range (len(target_list)):
                            if hitChance (firing_ship.comp, target_list[target_ship_id].shie) == i:
                                can_hit [target_ship_id] = nb_outcomes

                        break

            proba_outcomes += [6 - last_i] #proba of miss

            #print ("nb_outcomes =", nb_outcomes, "probas =", proba_outcomes, "can hit =", can_hit )
            proba_log_outcomes = [np.log (outcome) - np.log(6) for outcome in proba_outcomes]
            proba_log_outcomes+= [np.log (1) - np.log(6) for _ in range (4)] + [np.log (2) - np.log(6)]# outcomes of the rift canon

            damages_per_alive = [] #list where 1st element is for 1 alive ship, 2nd for 2 alive ships and so on
            damages_per_alive_missiles = []
            for alive in range (1, firing_ship.numb+1):
                # canon round
                dice = alive * firing_ship.canon_array
                damages_per_alive.append (self.possibleResultsOfDice (dice, proba_log_outcomes, target_hp, can_hit))

                # missile round
                dice = alive * firing_ship.missi_array
                damages_per_alive_missiles.append (self.possibleResultsOfDice (dice, proba_log_outcomes, target_hp, can_hit))

            self.transition_table.append (damages_per_alive)
            transition_table_missiles.append (damages_per_alive_missiles)
        
        # put missiles at the end
        self.transition_table += transition_table_missiles

    def possibleResultsOfDice (self, dice, proba_log_outcomes, target_hp, can_hit):
        nb_outcomes = len (proba_log_outcomes) -1 -5
        nb_targets = len(target_hp)

        rift_result = [(3,1), (2,0), (1,0), (0,1)] # list of pink dice possibility, (damage, self damage)


        max_dice = 0
        for i in range (5):
            max_dice = max(max_dice, dice[i])

        fct = factorialLog (max_dice)

        #print ("dice =", dice)

        total_possibilities = 1 #total results of the dice

        nb_outcomes_rift = 4 # rift canon has 4 results (blank does not count)
        for die_type in range (4): #todo rift
            total_possibilities*= blockSize (nb_outcomes, dice[die_type]-1) # the number of dices outcome follows the same formula as the number of states
        total_possibilities*= blockSize (nb_outcomes_rift, dice[4]-1) 

        # range all results 
        result = [0 for _ in range (4*nb_outcomes+nb_outcomes_rift)] # nb_outcomes for each of the 4 die type and rift

        remaining_dice = 1*dice

        total_proba = 0.0

        damages_per_result = [] #list of all damages per die results
        which_die = [0 for _ in range (nb_outcomes)] + [1 for _ in range (nb_outcomes)] + [2 for _ in range (nb_outcomes)] + [3 for _ in range (nb_outcomes)] + [4 for _ in range (nb_outcomes_rift)]# tells which dice the result i belong to

        for _ in range (total_possibilities):
            #it works like a clock, whenever one die does a full turn, the next one moves one step
            for i in range (4*nb_outcomes+nb_outcomes_rift):
                if remaining_dice[which_die[i]] >=1 : #if any dice left, increment hit value
                    result[i]+=1
                    remaining_dice[which_die[i]]-=1
                    break
                else:
                    remaining_dice[which_die[i]]+=result[i]
                    result[i]=0 #reinitialize

            #print ("result =", result)

            # compute probability
            # Each die type is independant, so the proba is the product of each die proba, hence log proba is the sum
            log_proba = 0 #using exp and log to reduce numerical errors
            for die in range (5):
                if die<4:
                    rift = False
                    nb_out = nb_outcomes
                else:
                    rift = True
                    nb_out = nb_outcomes_rift
                log_proba += fct[dice[die]] # ln(nb_dice!)
                misses = dice[die]
                for outcome in range (nb_out):
                    hits = result[nb_outcomes*die+outcome]
                    misses -= hits
                    log_proba += -fct[hits] + hits*proba_log_outcomes[   outcome +rift*(nb_outcomes+1)] #  -ln(nb_hit!) + nb_hit*ln(proba_hit)
                log_proba += -fct[misses] + misses*proba_log_outcomes[nb_outcomes+rift*(nb_outcomes_rift+1)]
                
            proba = np.exp( log_proba )
            total_proba += proba

            # assign hits 

            damages = []
            not_done = True
            

            unassigned_result = result.copy()

            assignements = [0 for i in range ((4*nb_outcomes+nb_outcomes_rift)*nb_targets)] # for each result type, there is one cell for each ship
            while (not_done):
                not_done = False
                for target in range (nb_targets):
                    for die in range (4):
                        for outcome in range (nb_outcomes):
                            i = target*(4*nb_outcomes+nb_outcomes_rift) + die*nb_outcomes + outcome
                            if (not_done==False):
                                if (unassigned_result[die*nb_outcomes + outcome] >=1)and(outcome < can_hit[target]): #if any dice left, increment hit value
                                    assignements[i]+=1
                                    unassigned_result[die*nb_outcomes + outcome]-=1
                                    not_done = True
                                else:
                                    unassigned_result[die*nb_outcomes + outcome]+=assignements[i]
                                    assignements[i]=0 #reinitialize
                    # rift canon
                    die = 4
                    for outcome in range (nb_outcomes_rift):
                        i = target*(4*nb_outcomes+nb_outcomes_rift) + die*nb_outcomes + outcome
                        if (not_done==False):
                            if (unassigned_result[die*nb_outcomes + outcome] >=1):
                                assignements[i]+=1
                                unassigned_result[die*nb_outcomes + outcome]-=1
                                not_done = True
                            else:
                                unassigned_result[die*nb_outcomes + outcome]+=assignements[i]
                                assignements[i]=0 #reinitialize

                una = 0 #number of unassigned dice
                for res in unassigned_result:
                    una += res
                if una==0:
                    #compute damage corresponding to assignement
                    damage =[0 for i in range (4*nb_targets)] # the 4 first cells are the number of 1, 2, 3 and 4 taken by the first ship and so on
                    for target in range (nb_targets):
                        for die in range (4):
                            for outcome in range (nb_outcomes):
                                damage[target*4 + die]+= assignements[target*(4*nb_outcomes+nb_outcomes_rift) + die*nb_outcomes + outcome]
                        # rift canon
                        die = 4
                        for outcome in range (nb_outcomes_rift): # the 4th outcome is the self damage
                            if rift_result[outcome][0]>0:
                                damage[target*4 + rift_result[outcome][0]-1]+= assignements[target*(4*nb_outcomes+nb_outcomes_rift) + die*nb_outcomes + outcome]

                    damage = listToTuple (damage)
                    damages.append (damage)

            # rift self hits
            self_hits = 0
            die = 4
            for outcome in range (nb_outcomes_rift):
                self_hits += rift_result[outcome][1]* result[nb_outcomes*die+outcome]


            damages = [proba] + [self_hits] + damages

            damages_per_result.append (damages)

        return (damages_per_result)
    
    def errorCheck (self):
        # checks if value function and final state are coherent
        error  = False
        precision = 0.00000001
        # test 1: value function and final state are coherent
        if (abs(self.att_win_chance-self.initial_win_chance)>precision):
            error = True 
        # test 2: do atatck and defense win chacne add up to 100%
        if (abs(self.att_win_chance+self.def_win_chance-1)>precision):
            error = True 
        return (error)
    

def blockSize (nb_ships, hull):
    #computes the size of a state block for given number of ships and hull
    block = 1
    for i in range (1, nb_ships+1):
        block = (block*(hull+1+i))//i
    return (block)

def makeGraph (nb_ships, hull, print_tables=False):
    # makes 5 table which, for each index, says how many ships are alive, 
    # 0: how many ships are alive
    # i: lists the state you can reach by taking i damages
    hp_to_id = {}
    id_to_hp = []
    #step-1: enumerate all states, build lookup tables
    hp = [0 for i in range (nb_ships)]

    for id in range (blockSize(nb_ships, hull)):
        id_to_hp.append (listToTuple ( hp ))
        hp_to_id[listToTuple ( hp )]=id
        for ship in range (nb_ships-1, -1, -1):
            if (hp[ship] < hull+1):
                hp[ship]+=1
                for ship2 in range (ship, nb_ships):
                    hp[ship2] = hp[ship]
                break
    #step 0: count how many ships are alive
    alive_ships = []
    for hp in id_to_hp:
        alive = 0
        for ship in range (nb_ships):
            alive += (hp[ship]>0)
        alive_ships.append(alive)
    #step 1-4: compute damage neighbors
    bunch_of_lists =[alive_ships]
    for die in range (1, 5):
        neighbor_list = []
        for id in range(len(id_to_hp)):
            hp = id_to_hp[id]
            neighbors = []
            for ship in range (nb_ships): #put damage to any ship
                hp2 = tupleToList(hp)
                hp2[ship]=max(hp2[ship]-die, 0)
                hp2.sort () # sort ships by increasing hp
                neighbors.append(hp_to_id[listToTuple ( hp2 )])
            neighbors = sortAndRemoveDuplicates (neighbors) 
            if (neighbors[-1]==id)and(id>0): #remove current index
                neighbors.pop ()
            neighbor_list.append (neighbors)
        bunch_of_lists.append(neighbor_list)
    #step 5: compute the hp of the most damaged ship  among the ships that are still alive (if all dead, then 0)
    damage_list = []
    for hp in id_to_hp:
        damage = 0
        for ship in range (nb_ships):
            if hp[ship]>0:
                damage = hp[ship]
                break # the most damaged ship is the first encountered
        damage_list.append(damage)
    bunch_of_lists.append(damage_list)

    if (print_tables):
        for id in range(len(id_to_hp)):
            print (id, id_to_hp[id], "alive=", bunch_of_lists[0][id], "damage=", bunch_of_lists[5][id], "neighbors 1d", bunch_of_lists[1][id], "2d", bunch_of_lists[2][id], "3d", bunch_of_lists[3][id], "4d", bunch_of_lists[4][id])

    return (bunch_of_lists)
 
def factorialLog (n):
    # returns an array contening ln(0!) to ln(n!)
    # It is a way of avoiding numerical errors from multiplying very small numbers with very large number
    factorial_log = np.zeros (n+1)
    for i in range (2, n+1):
        factorial_log[i] = factorial_log [i-1] + np.log (i)
    return (factorial_log )

def hitChance (att_computer, def_shield):
    modif = att_computer - def_shield #ship computer - enemy ship shield
    if (modif>=4):
        # 5 chance out of 6 to hit
        hit_chance = 5
    elif (modif<=0):
        # 1 chance out of 6 to hit
        hit_chance = 1
    else:
        hit_chance = 1+modif
    return (hit_chance)

if __name__ == '__main__':
    #makeGraph(3, 3, print_tables=True)

    # type, number, init, hull, computer, shield, canons, missiles
    interceptor= Ship("int", 2, 3, 0, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
    dreadnought= Ship("dre", 1, 0, 4, 2, 1, [1,3,0,0,0], [0,0,0,0,0])
    cruiser    = Ship("cru", 2, 2, 2, 2, 0, [2,0,0,0,0], [0,0,0,0,0])

    #test = BattleWinChances ([interceptor, dreadnought], [cruiser])


    if (False):
        eridan1 = Ship("cru", 2, 2, 3, 1, 0, [0,1,0,0,0], [0,0,0,0,0])
        eridan2 = Ship("cru", 2, 3, 4, 1, 0, [0,1,0,0,0], [0,0,0,0,0])
        ancient = Ship("npc", 2, 2, 1, 1, 0, [2,0,0,0,0], [0,0,0,0,0])

        test = BattleWinChances ([eridan1], [ancient]); print (test.initial_win_chance)
        test = BattleWinChances ([eridan2], [ancient]); print (test.initial_win_chance)

        #plt.show()

    eridani_test = False
    npc_dam_test = False
    missile_test = False
    riftcan_test = True
    perform_test = False


    if (eridani_test):
        eridan1 = Ship("cru", 2, 2, 3, 1, 0, [0,1,0,0,0], [0,0,0,0,0])
        eridan2 = Ship("cru", 2, 3, 4, 1, 0, [0,1,0,0,0], [0,0,0,0,0])
        ancient = Ship("npc", 2, 2, 1, 1, 0, [2,0,0,0,0], [0,0,0,0,0])

        test = BattleWinChances ([eridan1], [ancient]); print (test.initial_win_chance)
        test = BattleWinChances ([eridan2], [ancient]); print (test.initial_win_chance)

    if (npc_dam_test):
        plt.close ()

        print ("NPC damage assignment tests")

        dum_int = Ship("int", 6, 3, 0, 0, 0, [0,0,0,0,0], [0,0,0,0,0])
        cruiser = Ship("cru", 1, 2, 2, 1, 0, [1,0,0,0,0], [0,0,0,0,0])
        dum_dre = Ship("dre", 1, 3, 5, 0, 0, [0,0,0,0,0], [0,0,0,0,0])
        ancient = Ship("npc", 1, 2, 1, 1, 0, [2,0,0,0,0], [0,0,0,0,0])
        anfalse = Ship("cru", 1, 2, 1, 1, 0, [2,0,0,0,0], [0,0,0,0,0])
        print ("              1 cru VS ancient                  ")
        test = BattleWinChances ([         cruiser], [ancient]); print (test.initial_win_chance)
        print ("6 dummy int + 1 cru VS ancient OPTIMAL DAMAGE (should be equal to  above)")
        test = BattleWinChances ([dum_int, cruiser], [anfalse]); print (test.initial_win_chance)
        print ("1 dummy dre + 1 cru VS ancient OPTIMAL DAMAGE (should be equal to  above)")
        test = BattleWinChances ([dum_dre, cruiser], [anfalse]); print (test.initial_win_chance)
        print ("6 dummy int + 1 cru VS ancient WITH NPC RULE  (should be more than above)")
        test = BattleWinChances ([dum_int, cruiser], [ancient]); print (test.initial_win_chance)
        print ("1 dummy dre + 1 cru VS ancient WITH NPC RULE  (should be equal to  above)")
        test = BattleWinChances ([dum_dre, cruiser], [ancient]); print (test.initial_win_chance)
        print ("1 cru w 6 more hull VS ancient                (should be equal to  above)")
        cruiser = Ship("cru", 1, 2, 8, 1, 0, [1,0,0,0,0], [0,0,0,0,0])
        test = BattleWinChances ([         cruiser], [ancient]); print (test.initial_win_chance)



        print ("1 uber glass canon int + 3 dummy cru VS GCDS B OPTIMAL DAMAGE (should return about   1/2^4 = 0.0625)")
        int_att = Ship("int", 1, 3, 0, 4, 0, [0,0,0,8,0], [0,0,0,0,0])
        cruiser = Ship("cru", 3, 2, 0, 0, 0, [0,0,0,0,0], [0,0,0,0,0])
        gcdsmis = Ship("dre", 1, 0, 3, 2, 0, [0,0,0,1,0], [4,0,0,0,0])
        test = BattleWinChances ([int_att, cruiser], [gcdsmis]); print (test.initial_win_chance)
        print ("1 uber glass canon int + 3 dummy cru VS GCDS B WITH NPC RULE  (should return about 1-1/2^4 = 0.9375)")
        gcdsmis = Ship("npc", 1, 0, 3, 2, 0, [0,0,0,1,0], [4,0,0,0,0])
        test = BattleWinChances ([int_att, cruiser], [gcdsmis]); print (test.initial_win_chance)


        print (" ")

    if (missile_test):
        plt.close ()

        print ("Missile test (should return 0.25)")
        int_def = Ship("int", 2, 2, 0, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
        int_att = Ship("int", 1, 2, 0, 2, 0, [0,0,0,0,0], [2,0,0,0,0])

        print ("1 int with 2 ion missiles and 2 comp VS 2 int with 0 hull")
        test = BattleWinChances ([int_att], [int_def]); print (test.initial_win_chance)


        print ("Optimal missile hit assignation test (should return (5/6)^4 = 0.48225)")
        int_def = Ship("int", 2, 2, 2, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
        int_att = Ship("int", 1, 2, 0, 4, 0, [0,0,0,0,0], [2,0,0,0,0])
        dre_att = Ship("dre", 1, 0, 0, 4, 1, [0,0,0,0,0], [0,2,0,0,0])

        test = BattleWinChances ([int_att, dre_att], [int_def]); print (test.initial_win_chance)


        print ("Optimal hit assignation test (should return 0.47 both times)")
        int_def = Ship("int", 2, 2, 2, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
        int_att = Ship("int", 2, 2, 2, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
        dre_att = Ship("dre", 1, 0,10, 2, 1, [0,0,0,0,0], [0,0,0,0,0])

        print ("2 int VS 2 int")
        test = BattleWinChances ([int_att         ], [int_def]); print (test.initial_win_chance)
        print ("2 int + 1 dre with no canon VS 2 int")
        test = BattleWinChances ([int_att, dre_att], [int_def]); print (test.initial_win_chance)

        print (" ")

    if (riftcan_test):
        plt.close ()

        print ("One volley tests")
        cru_att = Ship("cru", 1, 2, 0, 0, 0, [0,0,0,0,1], [0,0,0,0,0])
        print ("ship with 1 pink VS uber glass canon with 0 hull (should return 33% and 50% chance of killing def ship)")
        glassca = Ship("cru", 1, 0, 0, 4, 0, [8,0,0,0,0], [0,0,0,0,0])
        test = BattleWinChances ([cru_att], [glassca]); print (test.initial_win_chance)
        print ("ship with 1 pink VS uber glass canon with 1 hull (should return 17% and 33% chance of killing def ship)")
        glassca = Ship("cru", 1, 0, 1, 4, 0, [8,0,0,0,0], [0,0,0,0,0])
        test = BattleWinChances ([cru_att], [glassca]); print (test.initial_win_chance)
        print ("ship with 1 pink VS uber glass canon with 2 hull (should return  0% and 17% chance of killing def ship)")
        glassca = Ship("cru", 1, 0, 2, 4, 0, [8,0,0,0,0], [0,0,0,0,0])
        test = BattleWinChances ([cru_att], [glassca]); print (test.initial_win_chance)


        cru_att = Ship("cru", 1, 2, 2, 0, 0, [0,0,0,0,1], [0,0,0,0,0])
        ancient = Ship("npc", 1, 2, 1, 1, 0, [2,0,0,0,0], [0,0,0,0,0])
        print ("early rift cruiser VS ancient")
        test = BattleWinChances ([cru_att], [ancient]); print (test.initial_win_chance)

        print (" ")


    if (perform_test):
        plt.close ()

        for i in range (1, 9):
            print ("Pain test " + str(i) + ": " + str(i) + " int VS 2 sba") 
            int_att = Ship("int", i, 3, 3, 0, 0, [2,0,0,0,0], [0,0,0,0,0])
            sba_def = Ship("sba", 2, 4, 4, 2, 0, [2,0,0,0,0], [0,2,0,0,0])


            tic = time.perf_counter()
            test = BattleWinChances ([int_att], [sba_def]) #, sba_def])
            toc = time.perf_counter()
            print(f"Solved in {toc - tic:0.4f} seconds")

        #print ("Pain test 9: 8 int + 4cru vs 4 cru + 2 dre + 4 sba") 
        #int_att = Ship("int", 8, 3, 0, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
        #cru_att = Ship("cru", 4, 2, 1, 1, 0, [1,0,0,0,0], [0,0,0,0,0])
        #sba_def = Ship("sba", 4, 4, 2, 1, 0, [1,0,0,0,0], [0,2,0,0,0])
        #cru_def = Ship("cru", 4, 2, 1, 1, 0, [1,0,0,0,0], [0,0,0,0,0])
        #dre_def = Ship("dre", 2, 1, 2, 1, 0, [2,0,0,0,0], [0,0,0,0,0])
        #tic = time.perf_counter()
        #test = BattleWinChances ([int_att, cru_att], [sba_def, cru_def, dre_def]) #, sba_def])
        #toc = time.perf_counter()
        #print(f"Solved in {toc - tic:0.4f} seconds")


    plt.show ()