from Interpreter.core import Runtime, Parser, Interpreter
from Interpreter.memory import Instruction, ArgumentList, InstructionList, Explicit, Argument
from Interpreter.exceptions import ResolutionError
from Interpreter.utils import Function, create_body, extract_arguments, evaluate_condition

from .ffi import py_to_vm

from Interpreter.syntax import Syntax, SyntaxDict

def p_if(parser: Parser, instructions: InstructionList, i: int) -> int:
    inst = instructions[i]

    (start, end), body, depth = create_body(instructions, i, "if", "end", ["if"])

    if not depth < 0:
        raise ResolutionError("Could not locate where 'if' body ends.")
    
    instructions[start] = Instruction("__if__", [inst.args, parser.transform(body)], start)

    del instructions[start+1:end+1]

    return start

def r___if__(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The if statement could not be saved during runtime: the given arguments were too few.")
    
    cond_args, body = args

    resolved_args = []
    for arg in cond_args:
        value = interpreter.translate(runtime, arg).as_value
        if isinstance(value, str):
            resolved_args.append(interpreter.accent.extract_str(value))
        else:
            resolved_args.append(value)
    
    if evaluate_condition(resolved_args):
        interpreter.execute_instructions(body, runtime=runtime)

def p_while(parser: Parser, instructions: InstructionList, i: int) -> int:
    inst = instructions[i]

    (start, end), body, depth = create_body(instructions, i, "while", "end", ["while"])

    if not depth < 0:
        raise ResolutionError("Could not locate where 'while' body ends.")
    
    instructions[start] = Instruction("__while__", [inst.args, parser.transform(body)], start)

    del instructions[start+1:end+1]

    return start

def r___while__(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The while statement could not be saved during runtime: the given arguments were too few.")
    
    cond_args, body = args

    def evaluate_comparison():
        resolved_args = []
        for arg in cond_args:
            value = interpreter.translate(runtime, arg).as_value
            if isinstance(value, str):
                resolved_args.append(interpreter.accent.extract_str(value))
            else:
                resolved_args.append(value)
        
        return evaluate_condition(resolved_args)
    
    while evaluate_comparison():
        interpreter.execute_instructions(body, runtime=runtime)

        if runtime.stopped or interpreter.stopped:
            break

def p_try(parser: Parser, instructions: InstructionList, i: int) -> int:
    inst = instructions[i]

    (start, end), body, depth = create_body(instructions, i, "try", "end", ["try"])

    if not depth < 0:
        raise ResolutionError("Could not locate where 'try' body ends.")
    
    instructions[start] = Instruction("__try__", [inst.args, parser.transform(body)], start)

    del instructions[start+1:end+1]

    return start

def r___try__(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The try statement could not be saved during runtime: the given arguments were too few.")
    
    try_args, body = args
    func = interpreter.translate(runtime, try_args[0]).as_value

    if not isinstance(func, Function):
        raise ResolutionError("The function to handle whether the try block failed wasn't of the right type.")
    
    try:
        interpreter.execute_instructions(body, runtime=runtime)
    except Exception as e:
        fn_args = func.args
        values = [e]
        
        if fn_args and fn_args[-1].startswith("*"):
            variadic_name = fn_args[-1][1:]
            fixed_count = len(fn_args) - 1

            if len(values) < fixed_count:
                raise ResolutionError("Not enough arguments supplied.")
            
            fixed_values = values[:fixed_count]
            rest_values = values[fixed_count:]

            vm_list = py_to_vm(rest_values, runtime)

            values = fixed_values + [Explicit(variadic_name, vm_list)]
            fn_args = fn_args[:-1] + [variadic_name]
        
        if len(values) < len(fn_args):
            raise ResolutionError("All arguments must be supplied.")

        instructions = [
            Instruction("set", [name, "obj", Explicit(name, value.as_value if isinstance(value, Argument) else value)], func.instructions[0].line)
            for name, value in zip(fn_args, values)
        ]

        instructions.extend(func.instructions)
        interpreter.execute_instructions(instructions, func.owner, func.file)

def r_raise(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 1:
        raise ResolutionError("There must be at least one exception given to raise, using the runtime resolver.")
    
    raise args[0].as_value

comparison_syntax: SyntaxDict = SyntaxDict(
    Syntax("if", True, p_if, r___if__),
    Syntax("while", True, p_while, r___while__),
    Syntax("try", True, p_try, r___try__),
    Syntax("raise", False, runtime_resolver=r_raise)
)