
import math
import sys
from xmlrpc.client import MAXINT
from parse_model import *

DEBUG = False

class DepNode:
    def __init__(self, reaction):
        self.reaction = reaction # type Reaction
        self.dependencies = {}
        self.executions = 0
        self.parents = [] # array of DepNodes
        self.enabled = False
        self.species_desired = []

    def __str__(self) -> str:
        return self.to_string()
    
    def to_string(self, depth=0):
        spaces = depth*"|"
        s = ""

        if self.reaction == None:
            s = s + spaces + "target"
            s = s + " " + str(self.executions) + " times"
        else:
            s = s + spaces + str(self.reaction)
            s = s + " " + str(self.executions) + " times to produce " + str(self.species_desired)

        s = s + "\n"
        
        for d in self.dependencies:
            s = s + self.dependencies[d].to_string(depth+1)

        return s
    
    # returns the strictly-necessary reactions to include in the bmc
    def to_list(self):
        s = []

        if self.reaction and self.enabled:
            s.append(self.reaction.name)

        for d in self.dependencies:
            s = s + (self.dependencies[d].to_list())

        return s
        

# init: species counts as if they were the initial state
# target: target tuple (limited to one target for now)
# reactions: parsed list of availble reactions
# node: current working node

def make_dependency_graph(init, target, reactions, inputNode=None, parents=[], depth=0):
    
    lineStart = depth*" "

    if DEBUG:
        print(lineStart, 50*"=")

    # figure out how far away we are from the targets
    target_species = {}
    target_relation = {}
    target_count = {}
    init_count = {}
    for t in target:
        target_species[t] = target[t][0]
        target_relation[t] = target[t][1]
        target_count[t] = int(target[t][2])
        init_count[t] = init[target_species[t]]

    decreasing = False

    # make the target node on first run
    if inputNode == None:
        node = DepNode(reaction=None)

    
        for t in target:
            if init_count[t] == target_count[t]:
                print(lineStart, "Target satisfied in the initial state!")
                node.enabled = True
                node.executions = 0
            elif target_relation[t] == "=" or target_relation[t] == "==":
                node.executions = target_count[t] - init_count[t]
            elif target_relation[t] == ">=":
                if init_count[t] >= target_count[t]:
                    print(lineStart, "Target satisfied in the initial state!")
                    node.enabled = True
                    node.executions = 0
                else:
                    node.executions = target_count[t] - init_count[t]
            elif target_relation[t] == "<=":
                if init_count[t] <= target_count[t]:
                    print(lineStart, "Target satisfied in the initial state!")
                    node.enabled = True
                    node.executions = 0
                else:
                    node.executions = target_count[t] - init_count[t]
            else:
                print(lineStart, "ERROR: Target incorrectly defined.")
            
            if target_count[t] < init_count[t]:
                decreasing = True
            break # only consider one target in the initial node (csl rule???)


    else:
        node = inputNode

    if DEBUG:
        print(lineStart, "desired", node.species_desired)
        if node.reaction:
            print(lineStart, str(node.reaction), ".executions", node.executions)
        else:
            print(lineStart, "target.executions", node.executions)

    # figure out if this reaction is enabled enough times in the initial/current state
    if DEBUG:
        print(lineStart, "init", init)

    modified_init = {}
    for i in init:
        modified_init[i] = init[i]
    modified_target = {}

    if node.reaction:
        # create a modified initial state based on this node's executions
        node.enabled = True
        for s in init:
            for c in node.reaction.consume:
                if c[0] == s:
                    modified_init[s] = modified_init[s] - (node.executions * int(c[1]))
                    # added catalyst check here for better efficiency
                    if modified_init[s] < 0:
                        node.enabled = False
                        if DEBUG:
                            print(lineStart, "node not enabled at consume check on species", s)
                        modified_target[s] = (s, ">=", "0")
                        # modified_target[s] = (s, ">=", "1" if node.reaction.is_catalyst() else "0")
            for c in node.reaction.produce:
                if modified_init[s] == 0 and node.reaction.is_catalyst():
                    modified_init[s] = -1
                elif c[0] == s:
                    modified_init[s] = modified_init[s] + (node.executions * int(c[1]))
            # if modified_init[s] < 0:
                # modified_target[s] = (s, ">=", "0")

        # The following code was removed because it was reduntant; we have 
        # already checked the executions against the initial state at this point.
        # for c in node.reaction.consume:
        #     if (node.reaction.dep_executions * int(c[1])) > int(modified_init[c[0]]):
        #         node.enabled = False
        #         if DEBUG:
        #             print(lineStart, "node not enabled at point 1")
        #             print(lineStart, "with dep_executions", node.reaction.dep_executions)
        #             print(lineStart, "and c =", c[0], c[1])
        #             print(lineStart, "and modified_init[c[0]] =", modified_init[c[0]])
        #         break
        # the following check was moved up for efficiency and accuracy:
        # for s in modified_init:
        #     if modified_init[s] < 0:
        #         node.enabled = False
        #         if DEBUG:
        #             print(lineStart, "node not enabled at point 2")
        #         break
        # Check for guard requirement in catalyst reactions 
        # (may need to generalize to all guards, not just catalysts, but I don't think so)
        # if node.reaction.is_catalyst():
        #     for c in node.reaction.consume:



    if DEBUG:
            print(lineStart, "modified_init", modified_init)
            print(lineStart, "modified_target 1", modified_target)

    # base case
    if node.enabled:
        if DEBUG:
            if node.reaction:
                print(lineStart, "Initially enabled:", node.reaction.name, "with", node.executions, "executions")
            else:
                print(lineStart, "Initially enabled: target")
            print(lineStart, 50*"=")
            print(lineStart, "returning at point 1")
        return node

    # prevent cycles
    if node.reaction:
        modified_parents = parents + [node.reaction.name]
        if DEBUG:
            print(lineStart, "modified_parents", modified_parents)
            print(lineStart, "node.reaction", node.reaction)
    else:
        modified_parents = parents

    
    # figure out what reactions we need for each target
    # modified_target 2
    if node.reaction == None:
        for t in target:
            # delta_target = int(target[t][2]) - modified_init[target_species[t]]
            delta_target = int(target[t][2])
            if DEBUG:
                print(lineStart, "working on target", target[t])
                print(lineStart, "delta_target", delta_target)
            if delta_target == 0:
                if DEBUG:
                    print(lineStart, "Found reactions to meet the target, now looking for their dependencies")
            else:
                if t in modified_target.keys():
                    modified_target[t] = (modified_target[t][0], modified_target[t][1], str(int(modified_target[t][2]) + delta_target))
                else:
                    modified_target[t] = (target[t][0], target[t][1], str(delta_target))
            if DEBUG:
                print(lineStart, "modified_target 2", modified_target)

    for t in modified_target:
        if DEBUG:
            print(lineStart, "working on modified_target", modified_target[t])
        delta_target = int(modified_target[t][2]) - modified_init[modified_target[t][0]]
        # delta_target = int(modified_target[t][2])
        if DEBUG:
            print(lineStart, "modified_target[t][2]", modified_target[t][2])
            print(lineStart, "modified_init[modified_target[t][0]]", modified_init[modified_target[t][0]])
            print(lineStart, "delta_target", delta_target)
        for r in reactions:
            add_execs = False

            # if we need to generate a species
            if delta_target > 0: 
                needed_execs = {}
                for s in reactions[r].produce:
                    if modified_target[t][0] == s[0]:
                        if r not in node.dependencies.keys():
                            node.dependencies[r] = DepNode(reactions[r])
                        needed_execs[s] = int(math.ceil(float(delta_target) / float(s[1])))
                        add_execs = True
                            # s[1] is the stoichiometric constant for the species
            # if we need to consume a species
            elif decreasing: 
                for s in reactions[r].consume:
                    if modified_target[t][0] == s[0]:
                        if r not in node.dependencies.keys():
                            node.dependencies[r] = DepNode(reactions[r])
                        if reaction[r].is_catalyst():
                            needed_execs[s] = 1
                        else:
                            needed_execs[s] = int(math.ceil(float(0-delta_target) / float(s[1])))
                        add_execs = True
                            # s[1] is the stoichiometric constant for the species
            
            if add_execs:
                # find the species that needs the most executions
                max_execs = 0
                max_exec_key = ""
                for s in needed_execs.keys():
                    if needed_execs[s] > max_execs:
                        max_execs = needed_execs[s]
                        max_exec_key = s
                
                if DEBUG:
                    print(lineStart, "needed_execs", needed_execs)
                    print(lineStart, "max_execs", max_execs)

                node.dependencies[r].executions = max(max_execs, node.dependencies[r].executions)
                # node.dependencies[r].reaction.dep_executions += max_execs
                node.dependencies[r].parents += modified_parents
                node.dependencies[r].species_desired.append(tuple([s[0], delta_target]))

                if DEBUG:
                    print(lineStart, "Reaction", r, "gen/con", node.dependencies[r].species_desired)
                    print(lineStart, "Added dependency", node.dependencies[r].reaction.name)
                    print(lineStart, "with executions", node.dependencies[r].executions)
                    print(lineStart, "with max exec", max_exec_key, "at", max_execs)


    if DEBUG:
        for d in node.dependencies:
            print(lineStart, "DEP", node.dependencies[d].reaction.name)
    
    # RECURSE
    
    targets_met = []
    keys = list(node.dependencies.keys())
    for d in keys:
        temp_target = {}
        for t in modified_target:
            for s in node.dependencies[d].species_desired:
                if modified_target[t][0] == s:
                    temp_target[t] = modified_target[t]
                elif modified_init[t] < 0:
                    modified_init[t] = 0
        if DEBUG:
            print(lineStart, "Recursing into dependency", node.dependencies[d].reaction.name, "with target", temp_target)
        # else:
        #     print(lineStart, "Recursing into dependency", node.dependencies[d].reaction.name)
        
        # only recurse if there is no cycle formation
        if DEBUG:
            print(lineStart, "node.dependencies[d].reaction.name in modified_parents", node.dependencies[d].reaction.name in modified_parents)
        if str(node.dependencies[d].reaction.name) in modified_parents:
            if DEBUG:
                print(lineStart, "THERE WAS A CYCLIC DEPENDENCY")
                print(lineStart, "deleting node.dependencies[d], or", str(node.dependencies[d]).strip())
            del node.dependencies[d]
            continue


        child_node = make_dependency_graph(modified_init, temp_target, reactions, node.dependencies[d], modified_parents, depth+1)
        
        if child_node.enabled:
            for sd in child_node.species_desired:
                targets_met.append(sd[0])

            # targets_met.append(child_node.species_desired[0])
            if DEBUG:
                print(lineStart, "targets_met", targets_met)
        else:
            node.dependencies.pop(d)

    if len(modified_target) > 0:
        node.enabled = True

    for mt in modified_target:
        if DEBUG:
            print(lineStart, modified_target[mt])
        if mt not in targets_met:
            node.enabled = False
            if DEBUG:
                print(lineStart, "MOD TARGET NOT ENABLED:", mt, targets_met)


    if DEBUG:
        print(lineStart, "returning at end", node.enabled)
        print(lineStart, 50*"=")
    return node
