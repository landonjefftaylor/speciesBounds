# built-in
import sys
import math

# local
from parse_model import *
from dependency_graph import *
from unroller import *
from yices_utils import *

# yices
from yices import *

# TODO: Set up command-line arg for dependency graph
dependency = True

print(80*"=")
print("CRN Variable Bound Calculator")
print(80*"=")

# types for yices
real_t = Types.real_type()
int_t = Types.int_type()
bool_t = Types.bool_type()

# get command line arguments
# command line instructions: python3 bounds.py model.crn (bv-bound)
# where bv-bound is optional and is the upper limit on variables.
if len(sys.argv) < 2:
    print("ERROR: NEED EXACTLY ONE ARGUMENT, THE NAME OF THE DESIRED FILE.")
    exit(1)
filename = str(sys.argv[1])

# find out how many bits if we added another command
BITS = 8
if len(sys.argv) == 3:
    BITS = math.ceil(math.log2(int(sys.argv[2])))
print("Using", BITS, "bit vectors")

def val_term(v):
    #return Terms.integer(v)
    return Terms.bvconst_integer(BITS, v)

zero = val_term(0)
one = val_term(1)

# define the bitvector type
bv_t = Types.bv_type(BITS)

# start parsing the model
print(80*"-")
print("Parsing the model from", filename)
print(80*"-")

# parse the model, parse_model.py
init, target, reaction = parse_model(filename)
print("Parsed model. Results as follows.")
print(init)
print(target)
for r in reaction:
    print(reaction[r])

if dependency:
    print(80*"-")
    print("Building the dependency graph")
    print(80*"-")
    target_dict = {}
    target_dict[target[0]] = target
    depnode = dependency_graph.make_dependency_graph(init, target_dict, reaction)
    reachable = depnode.enabled
    print("Reachable?", reachable)
    print("Dep Graph:")
    print(depnode)
    if not reachable:
        print("TARGET NOT REACHABLE. TERMINATING EARLY.")
        exit(0)
    reaction_list = depnode.to_list()
    k = list(reaction.keys())
    for r in k:
        if r not in reaction_list:
            reaction.pop(r)

# exit()

print(80*"-")
print("Building the yices model")
print(80*"-")

# leave our type as a bit vector
ty = bv_t

# build our vars and nexts,
# and fill initial values
state_vars = dict()
nexts = dict()
init_yand = []
for s in init:
    state_vars[s] = Terms.new_uninterpreted_term(ty, s)
    nexts[s] = Terms.new_uninterpreted_term(ty, s + "_next")
    init_yand.append(eq_term(state_vars[s], val_term(init[s])))

# now define our frame condition
def frame_cond(vars):
    res = Terms.true()
    for v in vars:
        res = Terms.yand([res, eq_term(nexts[v], state_vars[v])])
    return res

INIT = Terms.yand(init_yand)

encoded_reactions = []

for r in reaction:
    print("reaction", r)
    terms = []
    used_species = []
    catalysts = []
    # handle consumption
    for c in reaction[r].consume:
        terms.append(geq_term(state_vars[c[0]], one))
        # identify catalysts
        is_catalyst = False
        for p in reaction[r].produce:
            if c[0] == p[0]:
                print("is_catalyst", c[0], p[0])
                is_catalyst = True
                catalysts.append(c[0])
                if p[1] < c[1]:
                    # only subtract the net difference
                    print("sub net", p[1], c[1])
                    terms.append(eq_term(nexts[p[0]], sub_term(state_vars[p[0]],val_term(c[1] - p[1]))))
                    used_species.append(c[0])
                elif p[1] > c[1]:
                    # only add the net sum
                    print("add net", p[1], c[1])
                    terms.append(eq_term(nexts[p[0]], add_term(state_vars[p[0]],val_term(p[1] - c[1]))))
                    used_species.append(c[0])
                else:
                    print("net zero", p[1], c[1])
        if not is_catalyst:
            print("sub", c[0], c[1])
            terms.append(eq_term(nexts[c[0]], sub_term(state_vars[c[0]],val_term(c[1]))))
            used_species.append(c[0])
    # handle production
    for p in reaction[r].produce:
        if p[0] not in catalysts:
            print("add", p[0], p[1])
            terms.append(eq_term(nexts[p[0]], add_term(state_vars[p[0]],val_term(p[1]))))
            used_species.append(p[0])
    # handle unused species
    frame_cond_list = []
    for s in init:
        if s not in used_species:
            frame_cond_list.append(s)
    terms.append(frame_cond(frame_cond_list))
    # add the final reaction to the encoded reactions
    encoded_reactions.append((Terms.yand(terms)))
    
# TODO: Eventually this should be able to reduce down to our strictly necessary,
# using the dependency graph?
TRANS = Terms.yor(encoded_reactions)

# figure out the target
if target[1] == "=" or target[1] == "==":
    TARGET = eq_term(state_vars[target[0]], val_term(target[2]))
elif target[1] == ">=":
    TARGET = geq_term(state_vars[target[0]], val_term(target[2]))
elif target[1] == "<=":
    TARGET = geq_term(val_term(target[2]), state_vars[target[0]])

# print for debugging purposes
# print("INIT := " + Terms.to_string(INIT))
# print("TRANS := " + Terms.to_string(TRANS))
# print("TARGET := " + Terms.to_string(TARGET))

# make the unroller
unroller = Unroller(state_vars, nexts)

# initialize yices context
cfg = Config()
yices_ctx = Context(cfg)

# initial formula
formula = unroller.at_time(INIT, 0)

# assert formula in the yices context
yices_ctx.assert_formula(formula)
status = yices_ctx.check_context()

# print current status to debug
# if status == Status.ERROR:
#     print("Status 1: ERROR")
# if status == Status.UNKNOWN:
#     print("Status 1: UNKNOWN")
# if status == Status.UNSAT:
#     print("Status 1: UNSAT")
# if status == Status.SAT:
#     print("Status 1: SAT")

# start the interesting bmc business
k = 0

while True:
    print("-- TIME %3d --" % (k))
    # for assuming a goal at time k
    assump = Terms.new_uninterpreted_term(bool_t)
    #yices_ctx.push()
    yices_ctx.assert_formula(Terms.implies(assump,
                                           unroller.at_time(TARGET, k)))
    # check
    status = yices_ctx.check_context_with_assumptions(None, [assump])
    #yices_ctx.assert_formula(assump)
    #status = yices_ctx.check_context()
    if status == Status.SAT:
        # remember the whole formula
        formula = Terms.yand([formula, unroller.at_time(TARGET, k)])
        model = Model.from_context(yices_ctx, True)
        model_string = model.to_string(80, k * 4, 0)
        #print(model_string)
        #print(Terms.to_string(formula))
        break
    else:
        #yices_ctx.pop()
        # forgetting goal at time k
        yices_ctx.assert_formula(Terms.ynot(assump))
        yices_ctx.assert_formula(unroller.at_time(TRANS, k))
        formula = Terms.yand([formula, unroller.at_time(TRANS, k)])
        k = k + 1

print()

# now find the bounds for each variable
print(80*"-")
print("Bounding the species counts")
print(80*"-")

def timed_looseub_state(k, bound, state):
    # k is positive
    bound_term = val_term(bound)
    res = []
    for i in range(k+1):
        r = geq_term(unroller.at_time(state, i), bound_term)
        res.append(r)
    return Terms.yor(res)

def timed_tightub_state(k, bound, state):
    # k is positive
    bound_term = val_term(bound)
    res = []
    for i in range(k+1):
        r = geq_term(bound_term, unroller.at_time(state, i))
        res.append(r)
    return Terms.yand(res)

def timed_looselb_state(k, bound, state):
    # k is positive
    bound_term = val_term(bound)
    res = []
    for i in range(k+1):
        r = leq_term(unroller.at_time(state, i), bound_term)
        res.append(r)
    return Terms.yor(res)

def timed_tightlb_state(k, bound, state):
    # k is positive
    bound_term = val_term(bound)
    res = []
    for i in range(k+1):
        r = leq_term(bound_term, unroller.at_time(state, i))
        res.append(r)
    return Terms.yand(res)

ub_tight = dict()
ub_loose = dict()
lb_tight = dict()
lb_loose = dict()

print(30*".")

# step 1: loosest upper bounds
for s in init:
    yices_ctx.push()
    min_bound = 0
    bound = 0
    max_bound = 2**BITS - 1
    while True:
        yices_ctx.push()
        yices_ctx.assert_formula(timed_looseub_state(k, bound, state_vars[s]))
        status = yices_ctx.check_context_with_assumptions(None, [assump])
        if status == Status.SAT:
            if bound == max_bound:
                ub_loose[s] = bound
                break
            min_bound = bound
            bound = bound + int((max_bound-bound) / 2)
        elif status == Status.UNSAT:
            if bound == max_bound:
                ub_loose[s] = bound - 1
                break
            else:
                max_bound = bound
                if bound == 2**BITS-1:
                    bound = 2**BITS-2
                else:
                    bound = bound - int((bound-min_bound) / 2)
        else:
            print("THIS SHOULDN'T HAVE HAPPENED")
            break
        yices_ctx.pop()
    yices_ctx.pop()
    print(str(s) + "\tloose upper bound is:\t" + str(ub_loose[s]))
    yices_ctx.pop()


print(30*".")

# step 2: tightest upper bounds
for s in init:
    yices_ctx.push()
    max_bound = 2**BITS - 1
    bound = 2**BITS - 1
    min_bound = 0
    while True:
        yices_ctx.push()
        yices_ctx.assert_formula(timed_tightub_state(k, bound, state_vars[s]))
        status = yices_ctx.check_context_with_assumptions(None, [assump])
        if status == Status.SAT:
            if bound == min_bound:
                ub_tight[s] = bound
                break
            max_bound = bound
            if bound == 1:
                bound = 0
            else:
                bound = bound - int((bound-min_bound) / 2)
        elif status == Status.UNSAT:
            if bound == min_bound:
                ub_tight[s] = bound + 1
                break
            else:
                min_bound = bound
                bound = bound + int((max_bound-bound) / 2)
        else:
            print("THIS SHOULDN'T HAVE HAPPENED")
            break
        yices_ctx.pop()
    yices_ctx.pop()
    print(str(s) + "\ttight upper bound is:\t" + str(ub_tight[s]))
    yices_ctx.pop()

print(30*".")

# step 3: loosest lower bounds
for s in init:
    if init[s] == 0:
        lb_loose[s] = 0
        print(str(s) + "\tloose lower bound is:\t" + str(lb_loose[s]))
        continue
    yices_ctx.push()
    max_bound = 2**BITS - 1
    bound = 2**BITS - 1
    min_bound = 0
    while True:
        yices_ctx.push()
        yices_ctx.assert_formula(timed_looselb_state(k, bound, state_vars[s]))
        status = yices_ctx.check_context_with_assumptions(None, [assump])
        if status == Status.SAT:
            if bound == min_bound:
                lb_loose[s] = bound
                break
            max_bound = bound
            if bound == 1:
                bound = 0
            else:
                bound = bound - int((bound-min_bound) / 2)
        elif status == Status.UNSAT:
            if bound == min_bound:
                lb_loose[s] = bound + 1
                break
            else:
                min_bound = bound
                bound = bound + int((max_bound-bound) / 2)
        else:
            print("THIS SHOULDN'T HAVE HAPPENED")
            break
        yices_ctx.pop()
    yices_ctx.pop()
    print(str(s) + "\tloose lower bound is:\t" + str(lb_loose[s]))
    yices_ctx.pop()

print(30*".")

# step 4: tightest lower bounds
for s in init:
    yices_ctx.push()
    bound = 0
    max_bound = 2**BITS - 1
    while True:
        yices_ctx.push()
        yices_ctx.assert_formula(timed_tightlb_state(k, bound, state_vars[s]))
        status = yices_ctx.check_context_with_assumptions(None, [assump])
        if status == Status.SAT:
            if bound == max_bound:
                lb_tight[s] = bound
                break
            min_bound = bound
            bound = bound + int((max_bound-bound) / 2)
        elif status == Status.UNSAT:
            if bound == max_bound:
                lb_tight[s] = bound - 1
                break
            else:
                max_bound = bound
                if bound == 2**BITS-1:
                    bound = 2**BITS-2
                else:
                    bound = bound - int((bound-min_bound) / 2)
        else:
            print("THIS SHOULDN'T HAVE HAPPENED")
            break
        yices_ctx.pop()
    yices_ctx.pop()
    print(str(s) + "\ttight lower bound is:\t" + str(lb_tight[s]))
    yices_ctx.pop()

print()
print(80*"-")
print("Final Bounds for Trace Length", k)
print(80*"-")

for s in init:
    print("Species", s)
    print("    Lower bound [ %4d, %4d ]" % (lb_loose[s],lb_tight[s]))
    print("    Upper bound [ %4d, %4d ]" % (ub_tight[s],ub_loose[s]))
    # print("    Upper bound [", ub_tight[s], ",", ub_loose[s], "]")

    #TODO: BOUNDS STORED IN REACTION OBJECT

#TODO: TEST ON WORK PC
def species_gt(s1, s2):
    s1_loose = ub_loose[s1] - lb_loose[s1]
    s2_loose = ub_loose[s2] - lb_loose[s2]
    if s1_loose < s2_loose:
        return False
    elif s1_loose > s2_loose:
        return True
    s1_tight = ub_tight[s1] - lb_tight[s1]
    s2_tight = ub_tight[s2] - lb_tight[s2]
    if s1_tight < s2_tight:
        return False
    elif s1_tight > s2_tight:
        return True
    return True #TODO: EVENTUALLY MAKE NONDETERMINISTIC

def sort_species(unordered):
    # First, copy the species into a new array
    species = []
    for s in unordered:
        species.append(s)

    # simple insertion sort
    for i in range(1,len(species)):
        species_in_question = species[i]
        j = i - 1
        while j >= 0 and species_gt(species[j], species_in_question):
            species[j + 1] = species[j]
            j = j - 1
        species[j + 1] = species_in_question

    return species

sorted_species = sort_species(init)
print("Sorted Species:", sorted_species)