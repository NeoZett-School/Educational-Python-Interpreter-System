from Interpreter.core import Runtime, Interpreter
from Interpreter.memory import Environment, ArgumentList
from Interpreter.exceptions import ResolutionError
from Interpreter.utils import set_memory, evaluate_math

from Interpreter.syntax import Syntax, SyntaxDict

def r_math(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The 'math' runtime resolver requires at least a return variable, operation and value to operate on, or a 'if' statement like structure.")
    
    env = runtime
    offset = 0

    if isinstance(args[0].as_value, Environment):
        env = args[0].as_value
        offset = 1

    name = args[offset + 0].as_text

    op = args[offset + 1].as_text
    op_args = [arg.as_value for arg in args[offset + 2:]]

    advanced_args = args[offset + 1:]

    result = 0

    match op:
        case "abs":
            result = abs(sum(op_args))
        case "sum":
            result = sum(op_args)
        case "min":
            result = min(*op_args)
        case "max":
            result = max(*op_args)
        case _:
            result = evaluate_math(advanced_args)
    
    set_memory(env, name, result)

math_syntax: SyntaxDict = SyntaxDict(
    Syntax("math", runtime_resolver=r_math)
)