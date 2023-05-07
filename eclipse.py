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
        self.canon_array = np.array(canon_array  ) # [y, o, b, r, p], y = number of pink dice, o = number of orange dice etc
        self.missi_array = np.array(missile_array) # [y, o, b, r, p], same

    def setBattleIndexes (self, side, indexes):
        # Info that we store here for convenience even though that creates double dependencies
        self.side = side # "att" or "def"
        self.indexes = indexes #should be a list with the indexes in the Chance array 

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
    def __init__ (self, attacker_ship_list, defender_ship_list, remaining_ships = False): 
        self.att_ship_list = attacker_ship_list
        self.def_ship_list = defender_ship_list
        # State of battle is one big array, with each coordinate corresponding to : 
        # 0: round initiative order 
        # 1-end-1 : remaining hit points of every single ship, starting with attacker ships
        # end : 0 for attacker, 1 for defender
        size_round = len (self.att_ship_list) + len (self.def_ship_list)
        self.att_ships = []
        att_total_hp = 0
        ship_index = 0
        ship_types = [] # a list of id to see when two consecutive ships are of the same type
        self.ship_prios = []
        id = 0
        for ship in attacker_ship_list:
            ship.setBattleIndexes ("att", [ship_index + i for i in range(ship.numb)])
            ship_index += ship.numb
            for n in range (ship.numb):
                self.att_ships += [ship.hull+2]
                att_total_hp += ship.hull+1
                ship_types += [id]
                self.ship_prios += [ship.prio]
            id += 1
        self.def_ships = []
        def_total_hp = 0

        self.att_index = 1            # the index at which attack  ships start
        self.def_index = 1+ship_index # the index at which defense ships start
        ship_index = 0
        for ship in defender_ship_list:
            ship.setBattleIndexes ("def", [ship_index + i for i in range(ship.numb)])
            ship_index += ship.numb
            for n in range (ship.numb):
                self.def_ships += [ship.hull+2]
                def_total_hp += ship.hull+1
                ship_types += [id]
                self.ship_prios += [ship.prio]
            id += 1
        ship_types += [-1] # to avoid exceeding the length of the list in the algorithm
        dims = [2* size_round] + self.att_ships +self.def_ships + [2] #turn (with missiles), att ships hp, def ships hp, attacker or defender
        self.state_win_chance = np.zeros ( dims ) 
        self.state_win_chance [Ellipsis, 1] =-2.0 # attacker chance starts below 0 (worse than attacker defeat)
        self.state_win_chance [Ellipsis, 1] = 2.0 # defender chance starts above 1 (worse than defender defeat)

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
            for ship in self.att_ship_list:
                if (ship.init==init):
                    self.turn_order.append (ship)
            # range defense ship afterward so that they shoot first in case of a tie
            for ship in self.def_ship_list:
                if (ship.init==init):
                    self.turn_order.append (ship)
        #step3: compute transition table 
        self.transitionTable()

        #step 4: propagate win chance backward (=in increasing number hit points)
        not_done = True
        index = [-1] #initialize index at -1 0 ... 0
        for _ in range (len(self.att_ships) + len(self.def_ships)):
            index += [0]
        all_ships = self.att_ships + self.def_ships
        while (not_done):
            self.computeWinChance (index)

            not_done = False
            for ship in range (len(self.att_ships) + len(self.def_ships)):
                if (ship_types[ship]==ship_types[ship+1]):
                    if (index[ship+1]<index[ship+2]):
                        index[ship+1]+= 1
                        not_done = True
                        break
                    else:
                        index[ship+1] = 0
                elif (all_ships[ship] - index[ship+1]>1):
                    index[ship+1]+= 1
                    not_done = True
                    break
                else:
                    #reset all hp of that ship
                    for prev_ship in range (ship, -1, -1):
                        if ship_types[prev_ship]==ship_types[ship]:
                            index[prev_ship+1]=0
            

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
            start_index.pop ()
            self.state_expectancy[listToTuple(start_index)]=1.0 #initial state is guaranteed to happen
            index = start_index

            self.still_alive = np.zeros (len(self.att_ships)+len(self.def_ships))

            not_done = True
            while (not_done):
                self.computeExpectancy (index)

                not_done = False
                for ship in range (len(self.att_ships) + len(self.def_ships)):
                    if (index[ship+1]>=1):
                        index[ship+1]-= 1
                        not_done = True
                        for prev_ship in range (ship-1, -1, -1):
                            #reduce hp of all previous ships of the same type
                            if ship_types[prev_ship]==ship_types[ship]:
                                index[prev_ship+1]=index[ship+1]
                        break
                    else:
                        #reset hp of that ship
                        index[ship+1] = all_ships[ship] -1

            
            ship_names = [] # for legend
            xplacement = [] # place of the bar along the x axis
            bar_colors = [] # to differentiate att and def
            x_value = 1
            for ship in attacker_ship_list:
                for n in range (ship.numb):
                    if (n==0):
                        ship_names += [str(ship.numb-n) + " "  + ship.type ]
                    else :
                        ship_names += [str(ship.numb-n) + "+ " + ship.type ]
                    bar_colors += ["blue"]
                    xplacement += [x_value]
                    x_value += 1
                x_value += 1
            x_value += 1
            for ship in defender_ship_list:
                for n in range (ship.numb):
                    if (n==0):
                        ship_names += [str(ship.numb-n) + " "  + ship.type ]
                    else :
                        ship_names += [str(ship.numb-n) + "+ " + ship.type ]
                    bar_colors += ["red"]
                    xplacement += [x_value]
                    x_value += 1
                x_value += 1

            fig, ax = plt.subplots()
            bars = ax.bar(xplacement, self.still_alive, color = bar_colors)

            ax.set_xticks (xplacement)
            ax.set_xticklabels (ship_names)
            ax.set_yticks ([])

            percentages = ["{:.2%}".format(p) for p in self.still_alive]

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

                tuple = listToTuple (cur_index)
                tuple += (Ellipsis,) # for both attacker and defender

                self.state_win_chance[tuple] = 0.0

        elif (def_hp==0) :
            #attacker won
            for turn in range (2*turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn

                tuple = listToTuple (cur_index)
                tuple += (Ellipsis,) # for both attacker and defender
                self.state_win_chance[tuple] = 1.0

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
                tuple += (0,)
                win_chance += proba_full_miss*self.state_win_chance[tuple]

                cur_index[0] = turn
                tuple = listToTuple (cur_index)
                tuple += (Ellipsis,)

                self.state_win_chance[tuple] = win_chance
                


    def computeStateWinChance (self, ship_index) :
        # Writes and solves the win chance equation for the hp state for all round 
        # round number is added at the start of the index
        #print (ship_index)

        turn_size = len (self.att_ship_list) + len (self.def_ship_list)
        # which ship is firing ?
        cur_index = ship_index.copy()
        turn = cur_index[0]
        if turn < turn_size :
            cur_ship = self.turn_order[turn]
        else:
            #missile round
            cur_ship = self.turn_order[turn-turn_size]

        # how many of them are alive ?
        first_index = self.att_index #counting an attack ship
        if cur_ship.side == "def":
            first_index = self.def_index #counting a defense ship

        alive = 0
        for ind in cur_ship.indexes:
            if ship_index[first_index+ind]>0:
                alive +=1

        # what's next turn ?
        if turn == 0:
            cur_index[0] = len (self.att_ship_list) + len (self.def_ship_list) -1
        else :
            cur_index[0] = turn -1
        

        sign = 1
        max_chance = 0.0
        first_index = self.def_index #firing on defense ships
        last_index  = len (cur_index)
        tuple_end = (0,)
        if cur_ship.side == "def":
            sign =-1 #attack maximize winrate, defense minimize win rate
            max_chance = -1.0
            first_index = self.att_index #firing on attack ships
            last_index  = self.def_index
            tuple_end = (1,)

        if alive >0:
            win_chance = 0.0
            damages_per_result = self.transition_table [turn][alive-1] # list of outcomes with each a proba and all possible damage assignements
            for _ in range (len(damages_per_result)-1 ): # for each dice result (last is full miss)
                damages = damages_per_result[_]
                proba = damages[0]

                max_chance = 0.0 # reinitialize max chance
                if cur_ship.side == "def":
                    max_chance = -1.0

                if cur_ship.type =="npc" :
                    max_kill_score = 0      # max number of ship killed times their value (which corresponds to their size)
                    min_dama_score = 100000 # min remaining HP of the biggest ship alive
                    biggest_ship_prio = 0   # how large is the biggest ship alive
                
                for assignment in range (1, len(damages)): # for each damage assignment
                    
                    dam = damages[assignment]
                    for target_ship in range (len(dam)):
                        cur_index [first_index + target_ship] = max(ship_index [first_index + target_ship] - dam[target_ship], 0)
                    tuple = listToTuple (cur_index)
                    tuple += tuple_end
                    chance = self.state_win_chance [tuple]

                    if cur_ship.type =="npc" :
                        kill_score = 0 # number of ship killed times their value (which corresponds to their size)
                        dama_score = 100000 # remaining HP of the biggest ship alive
                        for i in range (first_index, last_index):
                            if   (cur_index[i]==0): #ship dead T-T
                                kill_score += self.ship_prios[i-1]
                            elif (self.ship_prios[i-1]>=biggest_ship_prio):
                                dama_score = cur_index[i]
                                if (self.ship_prios[i-1]>biggest_ship_prio): #hit a higher priority ship, updating priority
                                    biggest_ship_prio = self.ship_prios[i-1]
                                    min_dama_score = 100000
                                
                        if   (kill_score> max_kill_score):
                            max_kill_score = kill_score
                            min_dama_score = dama_score
                            max_chance = sign*chance
                        elif (kill_score==max_kill_score)and(dama_score< min_dama_score):
                            min_dama_score = dama_score
                            max_chance = sign*chance
                        elif (kill_score==max_kill_score)and(dama_score==min_dama_score):
                            max_chance = max (max_chance, sign*chance)
                    else :
                        # just take the highest chance of winning
                        max_chance = max (max_chance, sign*chance)
                win_chance += proba*sign*max_chance
        
            #print ("win chance =", sign*win_chance)

            proba_full_miss = damages_per_result[len(damages_per_result)-1][0]
        
        else:
            win_chance =0
            proba_full_miss = 1.0

        return (win_chance, proba_full_miss)




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
            cur_ship = self.turn_order[turn]

            if (cur_ship.side =="att"):
                target_list = self.def_ship_list
                target_hp = self.def_ships
            else :
                target_list = self.att_ship_list
                target_hp = self.att_ships

            nb_targets = len(target_hp)

            target_hit_chance = []
            for target_ship in target_list:
                target_hit_chance.append(hitChance (cur_ship.comp, target_ship.shie))
                
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

                        for target_ship in target_list:
                            if hitChance (cur_ship.comp, target_ship.shie) == i:
                                for index in target_ship.indexes:
                                    can_hit [index] = nb_outcomes

                        break

            proba_outcomes += [6 - last_i] #proba of miss

            #print ("nb_outcomes =", nb_outcomes, "probas =", proba_outcomes, "can hit =", can_hit )
            proba_log_outcomes = [np.log (outcome) - np.log(6) for outcome in proba_outcomes]

            damages_per_alive = [] #list where 1st element is for 1 alive ship, 2nd for 2 alive ships and so on
            damages_per_alive_missiles = []
            for alive in range (1, cur_ship.numb+1):
                # canon round
                dice = alive * cur_ship.canon_array
                damages_per_alive.append (self.possibleResultsOfDice (dice, proba_log_outcomes, target_hp, can_hit))

                # missile round
                dice = alive * cur_ship.missi_array
                damages_per_alive_missiles.append (self.possibleResultsOfDice (dice, proba_log_outcomes, target_hp, can_hit))

            self.transition_table.append (damages_per_alive)
            transition_table_missiles.append (damages_per_alive_missiles)
        
        # put missiles at the end
        self.transition_table += transition_table_missiles

    def possibleResultsOfDice (self, dice, proba_log_outcomes, target_hp, can_hit):
        nb_outcomes = len (proba_log_outcomes) -1
        nb_targets = len(target_hp)


        max_dice = 0
        for i in range (4):
            max_dice = max(max_dice, dice[i])

        fct = factorialLog (max_dice)

        #print ("dice =", dice)

        total_possibilities = 1 #total results of the dice

        for die_type in range (4): #todo rift
            total_possibilities*= totalPossibilities (dice[die_type], nb_outcomes)
        #print ("total_possibilities =", total_possibilities)

        # range all results 
        result = [0 for _ in range (4*nb_outcomes)] # nb_outcomes for each of the 4 die type

        remaining_dice = 1*dice

        total_proba = 0.0

        damages_per_result = [] #list of all damages per die results

        for _ in range (total_possibilities):
            #it works like a clock, whenever one die does a full turn, the next one moves one step
            for i in range (4*nb_outcomes):
                if remaining_dice[i//nb_outcomes] >=1 : #if any dice left, increment hit value
                    result[i]+=1
                    remaining_dice[i//nb_outcomes]-=1
                    break
                else:
                    remaining_dice[i//nb_outcomes]+=result[i]
                    result[i]=0 #reinitialize

            #print ("result =", result)

            # compute probability
            # Each die type is independant, 
            log_proba = 0 #using exp and log to reduce numerical errors
            for die in range (4):
                log_proba += fct[dice[die]] # ln(nb_dice!)
                misses = dice[die]
                for outcome in range (nb_outcomes):
                    hits = result[nb_outcomes*die+outcome]
                    misses -= hits
                    log_proba += -fct[hits] + hits*proba_log_outcomes[outcome] #  -ln(nb_hit!) + nb_hit*ln(proba_hit)
                log_proba += -fct[misses] + misses*proba_log_outcomes[nb_outcomes]
            proba = np.exp( log_proba )
            total_proba += proba

            # assign hits 

            damages = []
            not_done = True

            unassigned_result = result.copy()


            assignements = [0 for i in range (4*nb_outcomes*nb_targets)] # for each result type, there is one cell for each ship
            while (not_done):
                not_done = False
                for i in range (4*nb_outcomes*nb_targets):
                    if (unassigned_result[i//nb_targets] >=1)and((i//nb_targets)%nb_outcomes < can_hit[i%nb_targets]): #if any dice left, increment hit value
                        assignements[i]+=1
                        unassigned_result[i//nb_targets]-=1
                        not_done = True
                        break
                    else:
                        unassigned_result[i//nb_targets]+=assignements[i]
                        assignements[i]=0 #reinitialize
                una = 0 #number of unassigned dice
                for res in unassigned_result:
                    una += res
                if una==0:
                    #print (assignements)
                    #compute damage corresponding to assignement
                    overkill = False #checks whether a ship was assigned a dice after already being dead
                    all_dead = True #checks whether all ships are dead (in which case overkill is fine)
                    damage =[0 for i in range (nb_targets)]
                    for i in range (4*nb_outcomes*nb_targets):
                        if (damage[i%nb_targets] == target_hp[i%nb_targets]-1)and(assignements[i]>0): #assigning dice to a ship that's already dead
                            overkill = True
                        damage[i%nb_targets]+= (i//(nb_outcomes*nb_targets)+1) * assignements[i]
                        if (damage[i%nb_targets] >= target_hp[i%nb_targets]-1):
                            damage[i%nb_targets] = target_hp[i%nb_targets]-1
                        else:
                            all_dead = False
                    #print (damage)
                    if (overkill==False)or(all_dead==True): #TODO remove
                        damage = listToTuple (damage)
                        damages.append (damage)
            
            #remove duplicates
            damages = list(dict.fromkeys(damages))

            damages = [proba] + damages

            damages_per_result.append (damages)

        return (damages_per_result)
    
    def computeExpectancy(self, ship_index):
        turn_size = len (self.att_ship_list) + len (self.def_ship_list)
        

        #check whether there is at least 1 ship alive
        att_hp =0
        def_hp =0
        for i in range (self.att_index, self.def_index ):
            att_hp += ship_index[i]
        for i in range (self.def_index, len(ship_index)):
            def_hp += ship_index[i]
        if   (att_hp==0) :
            #attacker lost, counting remaining def ships
            for turn in range (2*turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn

                self.def_win_chance += self.state_expectancy[listToTuple (cur_index)]

                # count how many ships are still alive
                for ship in range (len(ship_index)-1):
                    if ship_index[ship+1]>0:
                        self.still_alive[ship]+=self.state_expectancy[listToTuple (cur_index)]

        elif (def_hp==0) :
            #attacker won, counting remaining att ships
            for turn in range (2*turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn

                self.att_win_chance += self.state_expectancy[listToTuple (cur_index)]

                # count how many ships are still alive
                for ship in range (len(ship_index)-1):
                    if ship_index[ship+1]>0:
                        self.still_alive[ship]+=self.state_expectancy[listToTuple (cur_index)]

        else :
            # step 1 : propagate expectancy of missile rounds
            for turn in range (2*turn_size-1, turn_size-1, -1):
                cur_index = ship_index.copy()
                cur_index[0] = turn
                self.propagateStateExpectancy(cur_index, full_miss=True )
            # step 2 : compute expectancy of canon rounds by solving a linear system
            # because canon rounds loop back on themselves, the expectancy of the entire round are defined implicitly as solution of a linear system
            A = np.zeros ((turn_size, turn_size))
            b = np.zeros ( turn_size )
            

            for turn in range (turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn
                (win_chance, proba_full_miss) = self.computeStateWinChance (cur_index) # TODO upgrade
                b[turn] = self.state_expectancy[listToTuple(cur_index)]
                A[turn, turn] = 1
                
                if (turn == 0):
                    A[turn, turn_size-1] =-proba_full_miss
                else :
                    A[turn, turn     -1] =-proba_full_miss
            #x = np.linalg.solve(A, b)
            x = np.linalg.solve(np.transpose(A), b)
            for turn in range (turn_size):
                cur_index = ship_index.copy ()
                cur_index[0] = turn

                self.state_expectancy[listToTuple (cur_index)] = x[turn]

            # step 3 : propagate expectancy of canon rounds 
            for turn in range (turn_size):
                cur_index = ship_index.copy()
                cur_index[0] = turn
                self.propagateStateExpectancy(cur_index, full_miss=False)
        return
    
    def propagateStateExpectancy (self, ship_index, full_miss) :
        # Ranges all dice results and propagates expectancy through it

        turn_size = len (self.att_ship_list) + len (self.def_ship_list)
        # which ship is firing ?
        cur_index = ship_index.copy()
        turn = cur_index[0]
        if turn < turn_size :
            cur_ship = self.turn_order[turn]
        else:
            #missile round
            cur_ship = self.turn_order[turn-turn_size]

        # how many of them are alive ?
        first_index = self.att_index #counting an attack ship
        if cur_ship.side == "def":
            first_index = self.def_index #counting a defense ship

        alive = 0
        for ind in cur_ship.indexes:
            if ship_index[first_index+ind]>0:
                alive +=1

        # what's next turn ?
        if turn == 0:
            cur_index[0] = len (self.att_ship_list) + len (self.def_ship_list) -1
        else :
            cur_index[0] = turn -1
        

        sign = 1
        first_index = self.def_index #firing on defense ships
        last_index  = len (cur_index)
        tuple_end = (0,)
        if cur_ship.side == "def":
            sign =-1 #attack maximize winrate, defense minimize win rate
            first_index = self.att_index #firing on attack ships
            last_index  = self.def_index
            tuple_end = (1,)

        if alive >0:
            damages_per_result = self.transition_table [turn][alive-1] # list of outcomes with each a proba and all possible damage assignements
            for _ in range (len(damages_per_result)-(full_miss==False) ): # for each dice result. Last result is full miss and only encountered with missile rounds
                damages = damages_per_result[_]
                proba = damages[0]

                max_chance =-2.0 # reinitialize max chance

                if cur_ship.type =="npc" :
                    max_kill_score = 0      # max number of ship killed times their value (which corresponds to their size)
                    min_dama_score = 100000 # min remaining HP of the biggest ship alive
                    biggest_ship_prio = 0   # how large is the biggest ship alive
                
                for assignment in range (1, len(damages)): # for each damage assignment
                    
                    dam = damages[assignment]
                    for target_ship in range (len(dam)):
                        cur_index [first_index + target_ship] = max(ship_index [first_index + target_ship] - dam[target_ship], 0)
                    tuple = listToTuple (cur_index)
                    tuple += tuple_end
                    chance = self.state_win_chance [tuple]

                    if cur_ship.type =="npc" :
                        kill_score = 0 # number of ship killed times their value (which corresponds to their size)
                        dama_score = 100000 # remaining HP of the biggest ship alive
                        for i in range (first_index, last_index):
                            if   (cur_index[i]==0): #ship dead T-T
                                kill_score += self.ship_prios[i-1]
                            elif (self.ship_prios[i-1]>=biggest_ship_prio):
                                dama_score = cur_index[i]
                                if (self.ship_prios[i-1]>biggest_ship_prio): #hit a higher priority ship, updating priority
                                    biggest_ship_prio = self.ship_prios[i-1]
                                    min_dama_score = 100000
                                
                        if   (kill_score> max_kill_score):
                            max_kill_score = kill_score
                            min_dama_score = dama_score
                            max_chance = sign*chance
                            best_index = cur_index.copy()
                        elif (kill_score==max_kill_score)and(dama_score< min_dama_score):
                            min_dama_score = dama_score
                            max_chance = sign*chance
                            best_index = cur_index.copy()
                        elif (kill_score==max_kill_score)and(dama_score==min_dama_score):
                            if (sign*chance>max_chance):
                                max_chance = sign*chance
                                best_index = cur_index.copy()
                    else :
                        # just take the highest chance of winning
                        if (sign*chance>max_chance):
                            max_chance = sign*chance
                            best_index = cur_index.copy()

                self.state_expectancy[listToTuple(best_index)]+=proba*self.state_expectancy[listToTuple(ship_index)]

        return ()


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

def totalPossibilities (nb_dice, nb_outcomes):
    if   (nb_outcomes == 1):
        possibilities =  nb_dice+1
    elif (nb_outcomes == 2):
        possibilities = (nb_dice+1) * (nb_dice+2)//2
    elif (nb_outcomes == 3):
        possibilities = (nb_dice+1) * (nb_dice+2)//2 * (nb_dice+3)//3
    elif (nb_outcomes == 4):
        possibilities = (nb_dice+1) * (nb_dice+2)//2 * (nb_dice+3)//3 * (nb_dice+4)//4
    return (possibilities)
 
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

    # type, number, init, hull, computer, shield, canons, missiles
    interceptor= Ship("int", 2, 3, 0, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
    dreadnought= Ship("dre", 1, 0, 4, 2, 1, [1,3,0,0,0], [0,0,0,0,0])
    cruiser    = Ship("cru", 2, 2, 2, 2, 0, [2,0,0,0,0], [0,0,0,0,0])

    #test = BattleWinChances ([interceptor, dreadnought], [cruiser])


    if (True):
        eridan1 = Ship("cru", 2, 2, 3, 1, 0, [0,1,0,0,0], [0,0,0,0,0])
        eridan2 = Ship("cru", 2, 3, 4, 1, 0, [0,1,0,0,0], [0,0,0,0,0])
        ancient = Ship("npc", 1, 2, 1, 1, 0, [2,0,0,0,0], [0,0,0,0,0])

        test = BattleWinChances ([eridan1], [ancient], remaining_ships=True)
        test = BattleWinChances ([eridan2], [ancient], remaining_ships=True)

        #plt.show()

    npc_dam_test = True
    missile_test = True
    perform_test = True

    if (npc_dam_test):

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
        print ("2 int + 1 cru with no canon VS 2 int")
        test = BattleWinChances ([int_att, dre_att], [int_def]); print (test.initial_win_chance)

        print (" ")

    if (perform_test):

        for i in range (1, 9):
            print ("Pain test " + str(i) + ": " + str(i) + " int VS 2 sba") 
            int_att = Ship("int", i, 3, 3, 0, 0, [2,0,0,0,0], [0,0,0,0,0])
            sba_def = Ship("sba", 2, 4, 4, 2, 0, [2,0,0,0,0], [0,2,0,0,0])


            tic = time.perf_counter()
            test = BattleWinChances ([int_att], [sba_def]) #, sba_def])
            toc = time.perf_counter()
            print(f"Solved in {toc - tic:0.4f} seconds")


    plt.show ()