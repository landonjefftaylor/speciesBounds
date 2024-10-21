from yices import *

def add_term(a, b):
    #return Terms.add(a, b)
    return Terms.bvadd(a, b)

def sub_term(a, b):
    #return Terms.sub(a, b)
    return Terms.bvsub(a, b)

def eq_term(a, b):
    #return Terms.eq(a, b)
    return Terms.bveq_atom(a, b)

def geq_term(a, b):
    #return Terms.arith_geq_atom(a, b)
    return Terms.bvge_atom(a, b)

def leq_term(a, b):
    #return Terms.arith_geq_atom(a, b)
    return Terms.bvle_atom(a, b)
