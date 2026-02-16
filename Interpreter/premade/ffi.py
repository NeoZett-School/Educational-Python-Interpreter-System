from typing import Dict, Optional, Callable, TypeVar, ParamSpec, Generic, Any
from Interpreter.core import Runtime, Interpreter
from Interpreter.memory import MemoryAddress, Explicit, Argument, Environment, ArgumentList
from Interpreter.exceptions import ResolutionError
from Interpreter.utils import set_memory

from Interpreter.syntax import Syntax, SyntaxDict

import importlib

from dataclasses import dataclass
import types

P = ParamSpec("P")
T = TypeVar("T")

@dataclass(slots=True)
class PyFunction(Generic[P, T]):
    func: Callable[P, T]

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.func(*args, **kwargs)

def py_to_vm(value: Any, parent: Optional[Environment], seen: Optional[Dict[int, Any]] = None) -> Any:
    if seen is None:
        seen = {}
    
    obj_id = id(value)
    if obj_id in seen:
        return seen[obj_id]
    
    if isinstance(value, (int, float, bool, type(None))):
        return value
    
    if isinstance(value, MemoryAddress):
        return value.value
    
    if isinstance(value, (Explicit, Argument)):
        return value.as_value
    
    if isinstance(value, Environment):
        return value
    
    if isinstance(value, list):
        env = Environment(parent, True)
        seen[obj_id] = env

        items = set_memory(env, "items", value).value

        set_memory(env, "get", PyFunction(items.__getitem__))
        set_memory(env, "set", PyFunction(items.__setitem__))
        set_memory(env, "pop", PyFunction(items.pop))
        set_memory(env, "append", PyFunction(items.append))
        set_memory(env, "remove", PyFunction(items.remove))
        set_memory(env, "clear", PyFunction(items.clear))
        set_memory(env, "count", PyFunction(items.count))
        set_memory(env, "index", PyFunction(items.index))
        set_memory(env, "insert", PyFunction(items.insert))
        set_memory(env, "copy", PyFunction(lambda: py_to_vm(items.copy(), parent, seen)))
        set_memory(env, "sort", PyFunction(items.sort))

        set_memory(env, "contains", PyFunction(lambda key: items.__contains__(key)))
        set_memory(env, "len", PyFunction(lambda: items.__len__()))

        return env
    
    if isinstance(value, str):
        env = Environment(parent, True)
        seen[obj_id] = env

        string = set_memory(env, "string", value).value

        set_memory(env, "get", PyFunction(string.__getitem__))
        set_memory(env, "count", PyFunction(string.count))
        set_memory(env, "index", PyFunction(string.index))
        set_memory(env, "format", PyFunction(string.format))

        set_memory(env, "contains", PyFunction(lambda key: string.__contains__(key)))
        set_memory(env, "len", PyFunction(lambda: string.__len__()))

        return env
    
    if isinstance(value, types.ModuleType):
        env = Environment(parent, False)
        seen[obj_id] = env
        for name in dir(value):
            if name.startswith("__"):
                continue
            try:
                attr = getattr(value, name)
            except Exception:
                continue
            set_memory(env, name, py_to_vm(attr, env, seen))
        return env
    
    if isinstance(value, type):
        env = Environment(parent, False)
        seen[obj_id] = env
        for name, attr in vars(value).items():
            if name.startswith("__"):
                continue
            set_memory(env, name, py_to_vm(attr, env, seen))
        return env
    
    if callable(value):
        fn = PyFunction(value)
        seen[obj_id] = fn
        return fn
    
    env = Environment(parent, is_obj=True)
    seen[obj_id] = env

    try:
        for name, attr in vars(value).items():
            if name.startswith("__"):
                continue
            set_memory(env, name, py_to_vm(attr, env, seen))
    except Exception:
        pass

    for name in dir(value):
        if name.startswith("__"):
            continue
        if name in env.memory:
            continue

        try:
            attr = getattr(value, name)
        except Exception:
            continue

        set_memory(env, name, py_to_vm(attr, env, seen))
    
    return env

def r_pytovm(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The 'pytovm' runtime resolver requires a name to save the vm and a python object.")
    
    name = args[0].as_text
    obj = args[1].as_value

    set_memory(runtime, name, py_to_vm(obj, runtime))

def r_pyimport(interpreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The 'pyimport' runtime resolver requires a name to save the vm and a name of the python module to import.")
    
    name = args[0].as_text
    module_name = args[1].as_value

    module = importlib.import_module(module_name)
    module_env = Environment(runtime, False)

    for attr_name in dir(module):
        if attr_name.startswith("__"):
            continue
        attr_value = getattr(module, attr_name)
        set_memory(module_env, attr_name, py_to_vm(attr_value, module))
    
    set_memory(runtime, name, module_env)

def r_id(intepreter: Interpreter, runtime: Runtime, args: ArgumentList) -> None:
    if len(args) < 2:
        raise ResolutionError("The 'id' runtime resolver requires a name to save the id and a name of the object.")
    
    name = args[0].as_text
    value = id([args[1].as_value])

    set_memory(runtime, name, value)

ffi_syntax: SyntaxDict = SyntaxDict(
    Syntax("pytovm", runtime_resolver=r_pytovm),
    Syntax("pyimport", runtime_resolver=r_pyimport),
    Syntax("id", runtime_resolver=r_id)
)