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
                print('-> ok')
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

def run_proofs():
    for name in my_proofs:
        run_proof(name)