from z3 import *
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))
from include import *

AddressSort = BitVecSort(160)
Address = lambda x: BitVecVal(x, AddressSort)
UintSort    = BitVecSort(256)
Uint = lambda x: BitVecVal(x, UintSort)

elenrvbusd_Address = BitVec('elenrvbusd_Address', AddressSort)
MAX_ELE = Uint(120000000e18)


# global state = tuple (balances: ArraySort(AddressSort, UintSort), ArraySort(AddressSort, UintSort), UintSort)

# deposit() = tuple (msg.sender: AddressSort, msg.value: UintSort)
def deposit(s, state, msg_sender, msg_value):
    balanceOf11nrvbusd, balanceOfERC20, sum_balanceOf11nrvbusd = state

    # implicit from how EVM works
    require(s, UGE(balanceOfERC20[msg_sender], msg_value))
    balanceOfERC20 = Store(balanceOfERC20, msg_sender, balanceOfERC20[msg_sender] - msg_value)
    balanceOfERC20 = Store(balanceOfERC20, elenrvbusd_Address, balanceOfERC20[elenrvbusd_Address] + msg_value)

    # balanceOf11nrvbusd[msg.sender] += msg.value;
    balanceOf11nrvbusd = Store(balanceOf11nrvbusd, msg_sender, balanceOf11nrvbusd[msg_sender] + msg_value)
    sum_balanceOf11nrvbusd = sum_balanceOf11nrvbusd + msg_value
    # Deposit(msg.sender, msg.value);

    return (balanceOf11nrvbusd, balanceOfERC20, sum_balanceOf11nrvbusd)

# emergencyBurn() = tuple (msg.sender: AddressSort, wad: UintSort)
def emergencyBurn(s, state, msg_sender, wad):
    balanceOf11nrvbusd, balanceOfERC20, sum_balanceOf11nrvbusd = state

    # require(balanceOf11nrvbusd[msg.sender] >= wad);
    require(s, UGE(balanceOf11nrvbusd[msg_sender], wad))

    # The missing _burn logic
    # balanceOf11nrvbusd[msg.sender] -= wad;
    # balanceOf11nrvbusd = Store(balanceOf11nrvbusd, msg_sender, balanceOf11nrvbusd[msg_sender] - wad)
    # sum_balanceOf11nrvbusd = sum_balanceOf11nrvbusd - wad

    # msg.sender.transfer(wad);
    require(s, UGE(balanceOfERC20[elenrvbusd_Address], wad))
    balanceOfERC20 = Store(balanceOfERC20, msg_sender, balanceOfERC20[msg_sender] + wad)
    balanceOfERC20 = Store(balanceOfERC20, elenrvbusd_Address, balanceOfERC20[elenrvbusd_Address] - wad)
    # Withdrawal(msg.sender, wad);

    return (balanceOf11nrvbusd, balanceOfERC20, sum_balanceOf11nrvbusd)

def initial_state():
    s = Solver()

    balanceOf11nrvbusd = Array('balanceOf11nrvbusd', AddressSort, UintSort)
    balanceOfERC20 = Array('balanceOfERC20', AddressSort, UintSort)
    sum_balanceOf11nrvbusd = Const('sum_balanceOf11nrvbusd', UintSort)

    # This is a manually defined constraint.
    # We proved that in horn.py, but this lemma needs to be manually imported.
    a = Const('a', AddressSort)
    require(s, ForAll([a], ULE(balanceOf11nrvbusd[a], balanceOfERC20[elenrvbusd_Address])))
    require(s, ForAll([a], ULE(balanceOf11nrvbusd[a], sum_balanceOf11nrvbusd)))
    require(s, sum_balanceOf11nrvbusd == balanceOfERC20[elenrvbusd_Address])
    require(s, ForAll([a], ULE(balanceOfERC20[a], MAX_ELE)))

    # assumptions
    balanceOfERC20 = Store(balanceOfERC20, elenrvbusd_Address, sum_balanceOf11nrvbusd)

    state = (balanceOf11nrvbusd, balanceOfERC20, sum_balanceOf11nrvbusd)

    return s, state

def is_ok(s, state):
    _, balanceOfERC20, sum_balanceOf11nrvbusd = state
    p = And(s.assertions()) 
    p = And(p, balanceOfERC20[elenrvbusd_Address] == sum_balanceOf11nrvbusd) 
    return p

# any external call to deposit
def symbolic_deposit(s, state):
    user = FreshConst(AddressSort, 'user')
    value = FreshConst(UintSort, 'value')
    
    require(s, user != elenrvbusd_Address)
    
    state = deposit(s, state, user, value)
    return state

# any external call to emergencyBurn
def symbolic_emergencyBurn(s, state):
    user = FreshConst(AddressSort, 'user')
    wad = FreshConst(UintSort, 'wad')

    require(s, user != elenrvbusd_Address)

    state = emergencyBurn(s, state, user, wad)
    return state

# ok let's actually prove

s, state = initial_state()

def sanity_check(cur_state):
    # sanity check. Let's make sure the initial state is valid
    s.push()
    s.add(Not(is_ok(s, cur_state)))
    assert(s.check() == unsat)
    s.pop()

sanity_check(state)

# each of these proofs is an inductive step.
# Given a (valid) initial state, prove that the final state after an
# arbitrary state transition is NOT invalid.
# Therefore, it would be impossible to reach an invalid state.

# each of these sub-proofs is a subgoal that checks a possible class
# of state transitions.
# together, they show that after any arbitrary transaction (within certain limitations)
# cannot break our invariants.
@my_proof(s)
def proof_deposit():
    new_state = symbolic_deposit(s, state)
    require(s, Not(is_ok(s, new_state)))

@my_proof(s)
def proof_emergencyBurn():
    new_state = symbolic_emergencyBurn(s, state)
    require(s, Not(is_ok(s, new_state)))

run_proofs()
