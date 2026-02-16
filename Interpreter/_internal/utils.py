from typing import Tuple, List, Union, Optional, TypeAlias, Any
from dataclasses import dataclass

from .memory import (
    T, WithAddress, Instruction, MemoryAddress, Argument, Environment, InstructionList, ArgumentList
)
from .core import Runtime

from .exceptions import ResolutionError

Body: TypeAlias = List[Instruction]

@dataclass(slots=True)
class Function(WithAddress):
    owner: Optional[Union[Environment, Runtime]]
    file: Optional[str]
    name: str
    args: List[str]
    instructions: InstructionList

    def __call__(self) -> None:
        pass

def create_body(instructions: InstructionList, start: int, inst_token: str, end_token: str, args: List[Any]) -> Tuple[Tuple[int, int], Body, int]:
    """
    Create a body from instructions, from the start to where the end token is found and all arguments matching. 
    Depth will only increase if a instruction has the instance token. 

    Returns a tuple with values to unpack. The first value is another tuple with the start and end of the body, in that order. 
    The second value is the body itself (just a classical instruction list), and the third argument is the last recorded depth.

    If the returned depth is not less than zero, the end token has not been found and the body is corrupted. You should almost 
    always raise if the depth is not less than zero.
    """
    count = len(instructions)
    body = []

    i = start + 1
    depth = 0
    while i < count:
        inst = instructions[i]
        
        if inst.token == inst_token:
            depth += 1
        
        elif inst.token == end_token and inst.args == args:
            depth -= 1
            if depth < 0:
                break

        body.append(inst)
        i += 1
    
    return (start, i), body, depth

def set_memory(environment: Environment, name: str, value: T) -> MemoryAddress[T]:
    if name in environment.memory:
        address = environment.memory[name]
        address.value = value
    else:
        address = MemoryAddress(environment, name, value)
        environment.memory[name] = address
    return address

def extract_arguments(args: List[Any]) -> List[Any]:
    unpacked_values = []
    for arg in args:
        if not isinstance(arg, Argument):
            unpacked_values.append(arg)
            continue
        if arg.as_text.startswith("*"):
            seq = arg.as_value
            if not isinstance(seq, list):
                raise ValueError("star argument must be a python list")
            unpacked_values.extend(seq)
        else:
            unpacked_values.append(arg)
    return unpacked_values

def evaluate_condition(args: List[Any]) -> Any:
    """Alternative conditional."""
    if len(args) < 2:
        return False

    left = args[0].as_value if hasattr(args[0], "as_value") else args[0]
    right = args[-1].as_value if hasattr(args[-1], "as_value") else args[-1]
    ops = [arg.as_text if hasattr(arg, "as_text") else arg for arg in args[1:-1]]

    result = left == right
    inverted = False

    for op in ops:
        match op:
            case "not":
                inverted = not inverted
            case "is":
                result = left is right
            case "equal":
                result = left == right
            case "greater":
                try:
                    result = float(left) > float(right)
                except Exception:
                    result = False
            case "lesser":
                try:
                    result = float(left) < float(right)
                except Exception:
                    result = False
    
    if inverted:
        result = not result

    return result

def evaluate_math(args: List[Any]) -> Any:
    """Alternative math."""
    if len(args) < 2:
        return False

    left = args[0].as_value if hasattr(args[0], "as_value") else args[0]
    right = args[-1].as_value if hasattr(args[-1], "as_value") else args[-1]
    ops = [arg.as_text if hasattr(arg, "as_text") else arg for arg in args[1:-1]]

    if isinstance(left, str):
        left = float(left)
    if isinstance(right, str):
        right = float(right)

    result = abs(left - right)
    inverted = False

    for op in ops:
        match op:
            case "invert":
                inverted = not inverted
            case "plus":
                result = left + right
            case "minus":
                result = left - right
            case "times":
                result = left * right
            case "power":
                result = left ** right
            case "modolo":
                result = left % right
            case "divide":
                result = left / right
            case "divide_int":
                result = left // right
            case "difference":
                result = abs(left - right)
    
    if inverted:
        result = -result

    return result