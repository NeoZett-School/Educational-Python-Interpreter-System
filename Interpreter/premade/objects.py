from typing import Iterable, Type, Final
from Interpreter.core import Runtime, Parser, Interpreter
from Interpreter.memory import Instruction, Explicit, Argument, Environment, InstructionList, ArgumentList
from Interpreter.exceptions import ResolutionError
from Interpreter.utils import Function, create_body, set_memory, extract_arguments

from Interpreter.syntax import Syntax, SyntaxDict

from .ffi import PyFunction, py_to_vm

class Error(ResolutionError):
    """An error raised from the program."""

NOT_FOUND: Final = object()

_import_cache = {}

casters = {
    "error": Error,
    "float": float,
    "int": int,
    "str": str,
    "bool": bool,
    "list": list,
    "any": lambda x: x,
}

def is_container_type(t: Type) -> bool:
    return (
        isinstance(t, type)
        and issubclass(t, Iterable)
        and not issubclass(t, (str, bytes))
    )

def p_class(parser: Parser, instructions: InstructionList, i: int) -> int:
    inst = instructions[i]

    if len(inst.args) < 1:
        raise ResolutionError("Class requires at least a name.")

    name = inst.args[0]
    inherit = inst.args[1:]

    (start, end), body, depth = create_body(instructions, i, "class", "end", ["class"])

    if not depth < 0:
        raise ResolutionError("Could not locate where class body ends.")
    
    instructions[start] = Instruction("__class__", [name, inherit, Environment(None), parser.transform(body)], start)

    del instructions[start+1:end+1]

    return start

def r___class__(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 4:
        raise ResolutionError("The class could not be saved during runtime: the given arguments were too few.")
    
    name, inherit, class_env, body = args
    name = name.as_text

    if not isinstance(class_env, Environment):
        raise ResolutionError(f"The class could not be saved during runtime: the arguments for '{name}' were corrupted.")
    
    class_env.parent = runtime

    interpreter.environment_loader(class_env)

    processed_inheritance = []
    for inherit_name in inherit:
        inherit_env = interpreter.translate(runtime, inherit_name)

        if not isinstance(inherit_env.as_value, Environment):
            raise ResolutionError(f"The class could not be saved during runtime: could not inherit from '{inherit_name}'")
        else:
            inherit_env = inherit_env.as_value
        
        class_env.memory.update(inherit_env.memory)
        processed_inheritance.append(inherit_env)
    
    set_memory(class_env, "__inheritance__", processed_inheritance)
    set_memory(class_env, "__name__", name)
    
    class_runtime = interpreter.execute_instructions(body, runtime)
    class_env.memory.update(class_runtime.memory)

    set_memory(runtime, name, class_env)

def p_func(parser: Parser, instructions: InstructionList, i: int) -> int:
    inst = instructions[i]

    if len(inst.args) < 1:
        raise ResolutionError("Function requires at least a name.")

    name = inst.args[0]
    args = inst.args[1:]

    (start, end), body, depth = create_body(instructions, i, "func", "end", ["func"])

    if not depth < 0:
        print(depth, inst, parser.line_no)
        raise ResolutionError("Could not locate where function body ends.")

    instructions[start] = Instruction("__func__", [name, Function(None, None, name, args, parser.transform(body))], start)

    del instructions[start+1:end+1]

    return start

def r___func__(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The function could not be saved during runtime: the given arguments were too few.")
    
    name, func = args
    name = name.as_text

    if not isinstance(func, Function):
        raise ResolutionError("The function could not be saved during runtime: the arguments were corrupted.")
    
    func.owner = runtime
    func.file = runtime.file
    
    set_memory(runtime, name, func)

def r_import(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 1:
        raise ResolutionError("The 'import' runtime resolver requires at least a path and optionally a variable name.")
    
    import_runtime = _import_cache.setdefault(args[0].as_value, interpreter.interpret(args[0].as_value))

    if len(args) == 1:
        runtime.memory.update(import_runtime.memory)
    else:
        set_memory(runtime, args[1].as_text, import_runtime)

def r_init(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The 'init' runtime resolver requires at least a class, name, and optional arguments.")
    
    class_env = args[0].as_value
    name = args[1].as_text

    if not isinstance(class_env, Environment):
        raise ResolutionError("The class you are initializing must be an actual class.")
    
    if class_env.is_obj:
        raise ResolutionError("The class you are initializing must not already be initialized.")
    
    func = class_env.resolve("init", NOT_FOUND)

    if func is NOT_FOUND or not isinstance(func.value, Function):
        raise ResolutionError("The class must have an 'init' function.")
    else:
        func = func.value
    
    fn_args = func.args
    obj = Environment(class_env.parent, True)
    obj.memory.update(class_env.memory)

    interpreter.environment_loader(obj)
    set_memory(obj, "__class__", class_env)
    set_memory(obj, "__name__", name)

    values = extract_arguments(args[2:])
    values = [obj] + values

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

    for mem in obj.memory.values():
        value = mem.value
        if isinstance(value, Function):
            value.owner = obj
    
    set_memory(runtime, name, obj)

def r_call(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 1:
        raise ResolutionError("The 'call' runtime resolver requires at least a name for the function to call. Optionally parse arguments following.")
    
    func = args[0].as_value

    if isinstance(func, PyFunction):
        if len(args) < 2:
            raise ResolutionError("The 'call' runtime resolver requires at least a name and destination for the result. Optionally parse arguments following.")
        
        dest = args[1].as_text

        values = extract_arguments([arg.as_value for arg in args[2:]])

        set_memory(runtime, dest, func(*values))
        return

    if not isinstance(func, Function):
        raise ResolutionError("The given function is not of the right type.")
    
    fn_args = func.args
    values = extract_arguments(args[1:])

    if func.owner and func.owner.is_obj:
        values = [func.owner] + values
    
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

def r_return(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The 'return' runtime resolver requires at least a name and value.")
    
    name = args[0].as_value
    value = args[1].as_value

    set_memory(interpreter.runtimes[-2], name, value)

def r_set(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The 'set' runtime resolver requires at least a name and value.")

    has_env = isinstance(args[0].as_value, Environment)
    offset = 1 if has_env else 0

    if len(args) - offset < 2:
        raise ResolutionError("The 'set' runtime resolver requires at least a name and value.")

    env = args[0].as_value if has_env else runtime
    name = args[offset].as_text

    if len(args) - offset == 2:
        t = "any"
        v = args[offset + 1].as_value
    else:
        t = args[offset + 1].as_text
        v = args[offset + 2].as_value

    if isinstance(v, Explicit) and t == "obj":
        evaluated = v.value
    else:
        try:
            cast = casters.get(t, casters["any"])
            if is_container_type(cast):
                evaluated = py_to_vm([arg.as_value for arg in args[offset + 2:]], runtime)
            else:
                evaluated = cast(v)
        except Exception as e:
            raise ResolutionError(f"Invalid value for type '{t}'.") from e
        
    set_memory(env, name, evaluated)

def r_del(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 1:
        raise ResolutionError("The 'del' runtime resolver requires a name to remove.")

    has_env = isinstance(args[0].as_value, Environment)
    offset = 1 if has_env else 0

    if len(args) <= offset:
        raise ResolutionError("The 'del' runtime resolver requires a name to remove.")

    env = args[0].as_value if has_env else runtime
    name = args[offset].as_text

    del env.memory[name]

def add_cast(key: str, cast: Type) -> None:
    casters[key] = cast

def remove_cast(key: str) -> None:
    del casters[key]

object_syntax: SyntaxDict = SyntaxDict(
    Syntax("class", True, p_class, r___class__),
    Syntax("func", True, p_func, r___func__),
    Syntax("import", runtime_resolver=r_import),
    Syntax("init", runtime_resolver=r_init),
    Syntax("call", runtime_resolver=r_call),
    Syntax("return", runtime_resolver=r_return),
    Syntax("set", runtime_resolver=r_set),
    Syntax("del", runtime_resolver=r_del)
)