from z3 import *
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))
from include import *

AddressSort = BitVecSort(160)
Address = lambda x: BitVecVal(x, AddressSort)
UintSort    = BitVecSort(256)
UintExpiry  = BitVecSort(48) 
Uint = lambda x: BitVecVal(x, UintSort)

MAX_ERC20Bond = Uint(120000000e18)

# We assume this bondERC20 is OHM
'''
global state = tuple (
    balanceOfallERC20Bond: ArraySort(AddressSort, ArraySort(UintExpiry, ArraySort(AddressSort, UintSort))), 
    totalbalanceOfallERC20Bond: ArraySort(AddressSort, ArraySort(UintExpiry, UintSort)), 
    balanceOfERC20: ArraySort(AddressSort, UintSort)
    )
'''
# create() = tuple (ERC20_address: AddressSort, expiry: UintExpiry, msg_sender: AddressSort, amount: UintSort)
def create(s, state, ERC20_address, expiry, msg_sender, amount):
    balanceOfallERC20Bond, totalbalanceOfallERC20Bond, balanceOfERC20 = state

    # implicit from how EVM works
    require(s, UGE(balanceOfERC20[msg_sender], amount))
    balanceOfERC20 = Store(balanceOfERC20, msg_sender, balanceOfERC20[msg_sender] - amount)
    balanceOfERC20 = Store(balanceOfERC20, ERC20_address, balanceOfERC20[ERC20_address] + amount)

    # ERC20BondToken bondToken = bondTokens[underlying_][expiry_];
    # if (bondToken == ERC20BondToken(address(0x00)))
        # revert Teller_TokenDoesNotExist(underlying_, expiry_);
    
    # underlying_.transferFrom(msg.sender, address(this), amount_);
    # bondToken.mint(msg.sender, amount_);
    balanceOfallERC20Bond = Store(balanceOfallERC20Bond, ERC20_address, Store(balanceOfallERC20Bond[ERC20_address], expiry, Store(balanceOfallERC20Bond[ERC20_address][expiry], msg_sender, balanceOfallERC20Bond[ERC20_address][expiry][msg_sender] + amount)))
    totalbalanceOfallERC20Bond = Store(totalbalanceOfallERC20Bond, ERC20_address, Store(totalbalanceOfallERC20Bond[ERC20_address], expiry, totalbalanceOfallERC20Bond[ERC20_address][expiry] + amount))

    return (balanceOfallERC20Bond, totalbalanceOfallERC20Bond, balanceOfERC20)

# redeem_withvalidation() = tuple (ERC20_address: AddressSort, expiry: UintExpiry, msg.sender: AddressSort, amount: UintSort)
def redeem_withvalidation(s, state, ERC20_address, expiry, msg_sender, amount):
    balanceOfallERC20Bond, totalbalanceOfallERC20Bond, balanceOfERC20 = state

    # require(balanceOf11nrvbusd[msg.sender] >= wad);
    require(s, UGE(balanceOfallERC20Bond[ERC20_address][expiry][msg_sender], amount))

    # token_.burn(msg.sender, amount_);
    balanceOfallERC20Bond = Store(balanceOfallERC20Bond, ERC20_address, Store(balanceOfallERC20Bond[ERC20_address], expiry, Store(balanceOfallERC20Bond[ERC20_address][expiry], msg_sender, balanceOfallERC20Bond[ERC20_address][expiry][msg_sender] - amount)))
    totalbalanceOfallERC20Bond = Store(totalbalanceOfallERC20Bond, ERC20_address, Store(totalbalanceOfallERC20Bond[ERC20_address], expiry, totalbalanceOfallERC20Bond[ERC20_address][expiry] - amount))

    # token_.underlying().transfer(msg.sender, amount_);
    require(s, UGE(balanceOfERC20[ERC20_address], amount))
    balanceOfERC20 = Store(balanceOfERC20, msg_sender, balanceOfERC20[msg_sender] + amount)
    balanceOfERC20 = Store(balanceOfERC20, ERC20_address, balanceOfERC20[ERC20_address] - amount)

    return (balanceOfallERC20Bond, totalbalanceOfallERC20Bond, balanceOfERC20)

# redeem() = tuple (
#    ERC20_address: AddressSort, 
#    FAKEbalanceofERC20Bond: Array(AddressSort, UintSort))
#    FAKEtotalbalanceofERC20Bond: UintSort
#    )

def redeem(s, state, ERC20_address, FAKEbalanceofERC20Bond, FAKEtotalbalanceofERC20Bond, msg_sender, amount):
    balanceOfallERC20Bond, totalbalanceOfallERC20Bond, balanceOfERC20 = state

    require(s, UGE(FAKEbalanceofERC20Bond[msg_sender], amount))

    # token_.burn(msg.sender, amount_);
    FAKEbalanceofERC20Bond = Store(FAKEbalanceofERC20Bond, msg_sender, FAKEbalanceofERC20Bond[msg_sender] - amount)
    FAKEtotalbalanceofERC20Bond = FAKEtotalbalanceofERC20Bond - amount

    # token_.underlying().transfer(msg.sender, amount_);
    require(s, UGE(balanceOfERC20[ERC20_address], amount))
    balanceOfERC20 = Store(balanceOfERC20, msg_sender, balanceOfERC20[msg_sender] + amount)
    balanceOfERC20 = Store(balanceOfERC20, ERC20_address, balanceOfERC20[ERC20_address] - amount)

    return (balanceOfallERC20Bond, totalbalanceOfallERC20Bond, balanceOfERC20)

def initial_state():
    s = Solver()

    balanceOfallERC20Bond = Array('balanceOfallERC20Bond', AddressSort, ArraySort(UintExpiry, ArraySort(AddressSort, UintSort)))
    totalbalanceOfallERC20Bond = Array('totalbalanceOfallERC20Bond', AddressSort, ArraySort(UintExpiry, UintSort))
    balanceOfERC20 = Array('balanceOfERC20', AddressSort, UintSort)

    # This is a manually defined constraint.
    # We proved that in horn.py, but this lemma needs to be manually imported.
    a = Const('a', AddressSort)
    b = Const('b', UintExpiry)
    c = Const('c', AddressSort)
    require(s, ForAll([a, b, c], ULE(balanceOfallERC20Bond[a][b][c], balanceOfERC20[a])))
    require(s, ForAll([a], ULE(balanceOfERC20[a], MAX_ERC20Bond)))
    require(s, ForAll([a, b, c], ULE(balanceOfallERC20Bond[a][b][c], totalbalanceOfallERC20Bond[a][b])))
    require(s, ForAll([a, b], totalbalanceOfallERC20Bond[a][b] == balanceOfERC20[a]))

    state = (balanceOfallERC20Bond, totalbalanceOfallERC20Bond, balanceOfERC20)
 
    return s, state

def is_ok(s, state, ERC20_address, expiry):
    _, totalbalanceOfallERC20Bond, balanceOfERC20 = state
    p = And(s.assertions()) 
    p = And(p, balanceOfERC20[ERC20_address] == totalbalanceOfallERC20Bond[ERC20_address][expiry])
    return p

# any external call to create
def symbolic_create(s, state):
    ERC20_address = FreshConst(AddressSort, 'user')
    expiry = FreshConst(UintExpiry, 'expiry')
    user = FreshConst(AddressSort, 'user')
    value = FreshConst(UintSort, 'value')
    
    require(s, user != ERC20_address)
    
    state = create(s, state, ERC20_address, expiry, user, value)
    return state, ERC20_address, expiry

# any external call to redeem_withvalidation
def symbolic_redeem_withvalidation(s, state):
    ERC20_address = FreshConst(AddressSort, 'user')
    expiry = FreshConst(UintExpiry, 'expiry')
    user = FreshConst(AddressSort, 'user')
    amount = FreshConst(UintSort, 'amount')

    require(s, user != ERC20_address)

    state = redeem_withvalidation(s, state, ERC20_address, expiry, user, amount)
    return state, ERC20_address, expiry

# any external call to redeem
def symbolic_redeem(s, state):
    ERC20_address = FreshConst(AddressSort, 'user')
    FAKEexpiryofERC20Bond = FreshConst(UintExpiry, 'expiry')
    FAKEbalanceofERC20Bond = Array('FakebalanceofERC20Bond', AddressSort, UintSort)
    FAKEtotalbalanceofERC20Bond = FreshConst(UintSort)
    user = FreshConst(AddressSort, 'user')
    amount = FreshConst(UintSort, 'amount')

    require(s, user != ERC20_address)
    a = Const('a', AddressSort)
    require(s, ForAll([a], ULE(FAKEbalanceofERC20Bond[a], FAKEtotalbalanceofERC20Bond)))
    require(s, ForAll([a], ULE(FAKEbalanceofERC20Bond[a], MAX_ERC20Bond)))

    state = redeem(s, state, ERC20_address, FAKEbalanceofERC20Bond, FAKEtotalbalanceofERC20Bond, user, amount)
    return state, ERC20_address, FAKEexpiryofERC20Bond

# ok let's actually prove shit

s, state = initial_state()

# each of these proofs is an inductive step.
# Given a (valid) initial state, prove that the final state after an
# arbitrary state transition is NOT invalid.
# Therefore, it would be impossible to reach an invalid state.

# each of these sub-proofs is a subgoal that checks a possible class
# of state transitions.
# together, they show that after any arbitrary transaction (within certain limitations)
# cannot break our invariants.
@my_proof(s)
def proof_create():
    new_state, ERC20_address, expiry = symbolic_create(s, state)
    require(s, Not(is_ok(s, new_state, ERC20_address, expiry)))

@my_proof(s)
def proof_redeem_withvalidation():
    new_state, ERC20_address, expiry = symbolic_redeem_withvalidation(s, state)
    require(s, Not(is_ok(s, new_state, ERC20_address, expiry)))

@my_proof(s)
def proof_redeem():
    new_state, ERC20_address, expiry = symbolic_redeem(s, state)
    require(s, Not(is_ok(s, new_state, ERC20_address, expiry)))

run_proofs()
