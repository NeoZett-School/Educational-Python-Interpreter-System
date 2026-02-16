"""The standard language allows using our own programming language that supports classes, inheritance, python FFI, variables and much more."""

from typing import Tuple
from Interpreter.core import ParserResolutions, RuntimeResolutions, Accent, Runtime, Interpreter
from Interpreter.memory import Environment
from Interpreter.utils import set_memory

from Interpreter.syntax import SyntaxTree, SyntaxDict

from .objects import object_syntax 
from .comparison import comparison_syntax
from .ffi import ffi_syntax
from .math import math_syntax
from .others import other_syntax

def standard_environment_loader(environment: Environment) -> None:
    set_memory(environment, "this", environment)
    set_memory(environment, "this_parent", environment.parent)

    if hasattr(environment, "file"):
        set_memory(environment, "this_path", environment.file)

standard_accent = Accent()

standard_syntax_dict: SyntaxDict = SyntaxDict()
standard_syntax_dict.update(object_syntax)
standard_syntax_dict.update(comparison_syntax)
standard_syntax_dict.update(ffi_syntax)
standard_syntax_dict.update(math_syntax)
standard_syntax_dict.update(other_syntax)

standard_syntax_tree: SyntaxTree = standard_syntax_dict.create_syntax_tree()

parser_resoultions: ParserResolutions = standard_syntax_tree.parser_resolutions
runtime_resolutions: RuntimeResolutions = standard_syntax_tree.runtime_resolutions

def create_standard_interpreter(debug: bool = False) -> Interpreter:
    return standard_syntax_tree.create_interpreter(
        accent = standard_accent,
        environment_loader = standard_environment_loader,
        debug = debug
    )

def interpret_file(file: str, debug: bool = False) -> Tuple[Interpreter, Runtime]:
    interpreter = create_standard_interpreter(debug)
    runtime = interpreter.interpret(file)
    return interpreter, runtime