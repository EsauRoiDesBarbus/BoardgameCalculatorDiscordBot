### Eclipse battle calculator

import numpy as np
import time

def listToTuple (integer_list):
    tuple = ()
    for integer in integer_list:
        tuple += (integer,)
    return (tuple)

class Ship:
    def __init__ (self, type, number, init, hull, computer, shield, canon_array, missile_array):
        self.type = type #0 interceptor, 1 cruiser, 2 dreadnought, 3 starbase
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
            


class BattleWinChances:
    def __init__ (self, attacker_ship_list, defender_ship_list): 
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
        id = 0
        for ship in attacker_ship_list:
            ship.setBattleIndexes ("att", [ship_index + i for i in range(ship.numb)])
            ship_index += ship.numb
            for n in range (ship.numb):
                self.att_ships += [ship.hull+2]
                att_total_hp += ship.hull+1
                ship_types += [id]
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
            id += 1
        ship_types += [-1] # to avoid exceeding the length of the list in the algorithm
        dims = [2* size_round] + self.att_ships +self.def_ships + [2] #turn (with missiles), att ships hp, def ships hp, attacker or defender
        self.state_win_chance = np.zeros ( dims ) # attacker chance starts at 0 (attacker defeat)
        self.state_win_chance [Ellipsis, 1] = 1.0 # defender chance starts at 1 (defender defeat)

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

        #step 3: propagate win chance backward (=in increasing number of total hit points)
        #print ("att_hp=", att_hp, "def_hp=", def_hp)
        not_done = True
        index = [-1] #initialize index at -1 0 ... 0
        for _ in range (len(self.att_ships) + len(self.def_ships)):
            index += [0]
        all_ships = self.att_ships + self.def_ships
        while (not_done):
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

            #print (index)
            
            self.computeWinChance (index)

        #print (self.stateWinChance)
        start_index = ()
        for d in dims:
            start_index += (d-1,)
        print ("attacker win chance =", self.state_win_chance[start_index])

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
        tuple_end = (0,)
        if cur_ship.side == "def":
            sign =-1 #attack maximize winrate, defense minimize win rate
            max_chance = -1.0
            first_index = self.att_index #firing on attack ships
            tuple_end = (1,)

        if alive >0:
            total_proba = 0.0
            win_chance = 0.0
            damages_per_result = self.transition_table [turn][alive-1] # list of outcomes with each a proba and all possible damage assignements
            for _ in range (len(damages_per_result)-1 ): #last is full miss
                damages = damages_per_result[_]
                proba = damages[0]
                
                
                for result in range (1, len(damages)):
                    
                    dam = damages[result]
                    for target_ship in range (len(dam)):
                        cur_index [first_index + target_ship] = max(ship_index [first_index + target_ship] - dam[target_ship], 0)
                    tuple = listToTuple (cur_index)
                    tuple += tuple_end
                    chance = self.state_win_chance [tuple]

                    max_chance = max (max_chance, sign*chance)
                total_proba += proba
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


    def displayStateWinChance (self, att_ship, def_ship):
        # displays the array for 2 specific ships TODO
        return

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


# type, number, init, hull, computer, shield, canons, missiles
interceptor= Ship("int", 2, 3, 0, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
dreadnought= Ship("dre", 1, 0, 4, 2, 1, [1,3,0,0,0], [0,0,0,0,0])
cruiser    = Ship("cru", 2, 2, 2, 2, 0, [2,0,0,0,0], [0,0,0,0,0])

#test = BattleWinChances ([interceptor, dreadnought], [cruiser])

eridani = Ship("cru", 1, 3, 4, 1, 0, [0,1,0,0,0], [0,0,0,0,0])
ancient = Ship("cru", 1, 2, 1, 1, 0, [2,0,0,0,0], [0,0,0,0,0])

#test = BattleWinChances ([eridani], [ancient])

print ("Optimal missile hit assignation test (should return (5/6)^4 )")
int_def = Ship("int", 2, 2, 2, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
int_att = Ship("int", 1, 2, 0, 4, 0, [0,0,0,0,0], [2,0,0,0,0])
dre_att = Ship("dre", 1, 0, 0, 4, 1, [0,0,0,0,0], [0,2,0,0,0])

test = BattleWinChances ([int_att, dre_att], [int_def])


print ("Optimal hit assignation test (should return 0.47 both times)")
int_def = Ship("int", 2, 2, 2, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
int_att = Ship("int", 2, 2, 2, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
dre_att = Ship("dre", 1, 0,10, 2, 1, [0,0,0,0,0], [0,0,0,0,0])

print ("2 int VS 2 int")
test = BattleWinChances ([int_att         ], [int_def])
print ("2 int + 1 cru with no canon VS 2 int")
test = BattleWinChances ([int_att, dre_att], [int_def])



print ("Missile test (should return 0.25)")

int_def = Ship("int", 2, 2, 0, 0, 0, [1,0,0,0,0], [0,0,0,0,0])
int_att = Ship("int", 1, 2, 0, 2, 0, [0,0,0,0,0], [2,0,0,0,0])

print ("1 int with 2 ion missiles and 2 comp VS 2 int with 0 hull")
test = BattleWinChances ([int_att], [int_def])





for i in range (1, 9):
    print ("Pain test " + str(i) + ": " + str(i) + " int VS 2 sba") 
    int_att = Ship("int", i, 3, 3, 0, 0, [2,0,0,0,0], [0,0,0,0,0])
    sba_def = Ship("sba", 2, 4, 4, 2, 0, [2,0,0,0,0], [0,2,0,0,0])


    tic = time.perf_counter()
    test = BattleWinChances ([int_att], [sba_def]) #, sba_def])
    toc = time.perf_counter()
    print(f"Solved in {toc - tic:0.4f} seconds")