from Interpreter.core import Runtime, Interpreter
from Interpreter.memory import Environment, Argument, ArgumentList
from Interpreter.exceptions import ResolutionError
from Interpreter.utils import set_memory, extract_arguments

from Interpreter.syntax import Syntax, SyntaxDict

def r_input(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The 'input' runtime resolver requires at least a variable name to save it to and a prompt.")
    
    name = args[0].as_text
    prompt = args[1].as_value

    set_memory(runtime, name, input(prompt))

def r_print(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 1:
        raise ResolutionError("The 'print' runtime resolver requires at least one argument.")
    
    if isinstance(args[0].as_value, Environment):
        print({name: value for name, value in args[0].as_value.memory.items() if not name.startswith("__")})
    
    print(*[arg.as_value if isinstance(arg, Argument) else arg for arg in extract_arguments(args)])

def r_jump(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 1:
        raise ResolutionError("The 'jump' runtime resolver requires a number as to how far forward or backwards.")
    
    runtime.jump = args[0].as_value

other_syntax: SyntaxDict = SyntaxDict(
    Syntax("input", runtime_resolver=r_input),
    Syntax("print", runtime_resolver=r_print),
    Syntax("jump", runtime_resolver=r_jump)
)