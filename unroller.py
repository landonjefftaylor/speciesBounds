# Ahmed's unroller class

from yices import *

class Unroller(object):
    # def __init__(self, state_vars, nexts, inputs):
    def __init__(self, state_vars, nexts):    
        self.state_vars = state_vars
        self.nexts = nexts
        # self.inputs = inputs
        self.var_cache = dict()
        self.time_cache = []
    def at_time(self, term, k):
        cache = self._get_cache_at_time(k)
        term_k = Terms.subst(cache.keys(), cache.values(), term)
        return term_k
    def get_var(self, v , k):
        if (v, k) not in self.var_cache:
            v_k = Terms.new_uninterpreted_term(Terms.type_of_term(v),
                                               Terms.to_string(v) + "@" + str(k))
            self.var_cache[(v, k)] = v_k
        return self.var_cache[(v, k)]
    def _get_cache_at_time(self, k):
        assert(k >= 0)
        while len(self.time_cache) <= k:
            cache = dict()
            t = len(self.time_cache)
            for s in self.state_vars:
                s_t = self.get_var(self.state_vars[s], t)
                n_t = self.get_var(self.state_vars[s], t+1)
                cache[self.state_vars[s]] = s_t
                cache[self.nexts[s]] = n_t
            # for i in self.inputs:
            #     i_t = Terms.new_uninterpreted_term(Terms.type_of_term(i),
            #                                     Terms.to_string(i) + "@" + str(t))
            #     cache[i] = i_t
            self.time_cache.append(cache)
        return self.time_cache[k]

if __name__ == "__main__":
    print("Nothing to test on unroller")