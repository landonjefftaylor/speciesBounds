# built-in
import sys
import math

# local
from parse_model import *
from dependency_graph import *

# yices

# TODO: Set up command-line arg for dependency graph
dependency = True

print(80*"=")
print("CRN DG Gen")
print(80*"=")

# get command line arguments
# command line instructions: python3 bounds.py model.crn (bv-bound)
# where bv-bound is optional and is the upper limit on variables.
if len(sys.argv) < 2:
    print("ERROR: NEED EXACTLY ONE ARGUMENT, THE NAME OF THE DESIRED FILE.")
    exit(1)
filename = str(sys.argv[1])

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

exit()
