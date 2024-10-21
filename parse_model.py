
class Reaction:
    def __init__(self, name):
        self.name = name
        self.consume = []
        self.produce = []
        self.const = 0.00
        self.dep_executions = 0

    def __str__(self) -> str:
        # s = ""
        # s = s+("Reaction " + self.name)
        # s = s+("\n")
        # for c in self.consume:
        #     s = s+"CON "+str(c)
        #     s = s+("\n")
        # for p in self.produce:
        #     s = s+"GEN "+str(p)
        #     s = s+("\n")
        # s = s+str(self.const)
        # s = s+("\n")
        return self.name
    

def parse_model(filename):
    init = dict()
    target = tuple()
    last_reaction = ""
    reaction = dict()
    with open(filename, "r") as model:
        for line in model:
            ls = line.strip().split()
            # species results in dictionary with species names as keys
            # and initial counts as values
            if "species" in line:
                if len(ls) != 4:
                    print("Length of species declaration not four tokens.")
                    print("Please match format: `species X init Y`.")
                    print("I read", " ".join(ls))
                    print("\nERROR: INVALID INPUT FORMAT")
                    exit(1)
                species_name = ls[1]
                species_count = int(ls[3])
                if species_name in init:
                    print("Species", species_name, "declared twice. Overwriting.")
                init[species_name] = species_count
            # target creates an array of strings,
            # each representing a single target property.
            # properties should be evaluated in (conjunction/disjunction?)
            elif "target" in line:
                if len(ls) != 4:
                    print("Length of target declaration not four tokens.")
                    print("Please match format: `species X <=> Y`.")
                    print("I read", " ".join(ls))
                    print("\nERROR: INVALID INPUT FORMAT")
                    exit(1)
                target = (ls[1], ls[2], ls[3])
            # reaction tells us what reaction we're looking at and
            # starts building a tuple
            elif "reaction" in line:
                if len(ls) != 2:
                    print("Length of reaction declaration not two tokens.")
                    print("Please match format: `reaction RX`.")
                    print("I read", " ".join(ls))
                    print("\nERROR: INVALID INPUT FORMAT")
                    exit(1)
                last_reaction = ls[1]
                reaction[last_reaction] = Reaction(last_reaction)
            # consume tells us what we're consuming. data gets stored in a
            # list of tuples like [(species, qty), (species, qty), ...]
            elif "consume" in line:
                if len(ls) != 2 and len(ls) != 3:
                    print("Length of consume declaration not two or three tokens.")
                    print("Please match format: `consume SX 1` or `consume SX`.")
                    print("I read", " ".join(ls))
                    print("\nERROR: INVALID INPUT FORMAT")
                    exit(1)
                if last_reaction == "":
                    print("Consume declared before reaction.")
                    print("I read", " ".join(ls))
                    print("\nERROR: INVALID INPUT FORMAT")
                    exit(1)
                if len(ls) == 3:
                    reaction[last_reaction].consume.append((ls[1],ls[2]))
                else: # default to consuming one
                    reaction[last_reaction].consume.append((ls[1],1))
            # produce tells us what we're consuming. data gets stored in a
            # list of tuples like [(species, qty), (species, qty), ...]
            elif "produce" in line:
                if len(ls) != 2 and len(ls) != 3:
                    print("Length of produce declaration not two or three tokens.")
                    print("Please match format: `produce SX 1` or `produce SX`.")
                    print("I read", " ".join(ls))
                    print("\nERROR: INVALID INPUT FORMAT")
                    exit(1)
                if last_reaction == "":
                    print("produce declared before reaction.")
                    print("I read", " ".join(ls))
                    print("\nERROR: INVALID INPUT FORMAT")
                    exit(1)
                if len(ls) == 3:
                    reaction[last_reaction].produce.append((ls[1],ls[2]))
                else: # default to consuming one
                    reaction[last_reaction].produce.append((ls[1],1))
            # const tells us the reaction constant.
            elif "const" in line:
                if len(ls) != 2:
                    print("Length of const declaration not two tokens.")
                    print("Please match format: `const 1.00`.")
                    print("I read", " ".join(ls))
                    print("\nERROR: INVALID INPUT FORMAT")
                    exit(1)
                if last_reaction == "":
                    print("const declared before reaction.")
                    print("I read", " ".join(ls))
                    print("\nERROR: INVALID INPUT FORMAT")
                    exit(1)
                reaction[last_reaction].const = float(ls[1])
    
    return init, target, reaction

import dependency_graph

if __name__ == "__main__":


    model = "6react.crn"

    print("Testing parser on", model)
    
    # init, target, reaction = parse_model("ypm.crn")
    init, target, reaction = parse_model(model)

    print(init)
    print(target)
    for r in reaction:
        print(r)
        print(reaction[r])

    target_dict = {}
    target_dict[target[0]] = target
    depnode, reachable = dependency_graph.make_dependency_graph(init, target_dict, reaction)
    print("Reachable?", reachable)
    print("Dep Graph:")
    print(depnode)