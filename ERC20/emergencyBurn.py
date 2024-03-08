from z3 import *
# set_param(proof=True)
set_param(unsat_core=True)

# helper funcs and boilerplate. sets up a test framework

predicates = {}
my_proofs = {}

def require(s, assertion):
    # black magic introspection shit
    import traceback,ast
    frame = traceback.extract_stack()[-2]
    code = frame.line
    yea = ast.parse(code)
    yea = list(ast.iter_child_nodes(next(ast.iter_child_nodes(next(ast.iter_child_nodes(yea))))))[2]
    yea = ast.unparse(yea)

    p = FreshBool()
    predicates[p] = (yea, frame.lineno, frame.name)
    s.assert_and_track(assertion, p)

def print_unsat_core(s):
    for p in s.unsat_core():
        code, lineno, name = predicates[p]
        print(f'* {str(p):5} {"line " + str(lineno):9} {name:16}  {code}')


def my_proof(s, name=None):
    def decorating_function(user_function):
        if name is None:
            assert(user_function.__name__.startswith('proof_'))
            _name = user_function.__name__[6:]
        else:
            _name = name # shadowing bullshit
        def decorated_function(*args, **kwargs):
            s.push()
            user_function(*args, **kwargs)
            if s.check() == unsat:
                print('Unsat core:')
                print_unsat_core(s)
            else:
                print("Counterexample found:", s.model())
            s.pop()
        my_proofs[_name] = decorated_function
        return decorated_function
    return decorating_function

def run_proof(name):
    func = my_proofs[name]
    print(name)
    func()
    print('-> ok')

def run_proofs():
    for name in my_proofs:
        run_proof(name)

# actual 11nrvbusd stuff

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
    # sum_balanceof11nrvbusd = sum_balanceOF11nrvbusd - wad

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

# ok let's actually prove shit

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
