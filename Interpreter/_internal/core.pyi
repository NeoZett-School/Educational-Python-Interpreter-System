from typing import List, Dict, Union, Optional, TypeAlias, Callable, Final, Any, overload
from dataclasses import dataclass

from .memory import (
    ArgumentList, 
    InstructionList,
    Instruction,
    Argument,
    Environment
)

ParserResolver: TypeAlias = Callable[["Parser", InstructionList, int], int]
ParserResolutions: TypeAlias = Dict[str, ParserResolver]

RuntimeResolver: TypeAlias = Callable[["Interpreter", "Runtime", ArgumentList], None]
RuntimeResolutions: TypeAlias = Dict[str, RuntimeResolver]

EnvironmentLoader: TypeAlias = Callable[[Environment], None]
OnTokenize: TypeAlias = Callable[["Parser", str], None]

NO_TOKEN: Final = object()
NOT_FOUND: Final = object()

def parse_number(text: str) -> Union[str, int, float]: ...

def default_cast(text: str) -> Any: ...

@dataclass(slots=True)
class Accent:
    navigator: str = "."
    delimiter: str = ","
    str_prefix: str = "'"
    str_suffix: str = "'"
    suffix: str = ";"

    value_caster: Callable[[str], Any] = default_cast

    def is_string(self, s: str) -> bool: ...
    def extract_str(self, s: str) -> str: ...
    def parts(self, s: str) -> List[str]: ...

@dataclass(slots=True)
class Runtime(Environment):
    file: str
    line_no: int = 0
    jump: int = 1
    stopped: bool = False
    def stop(self) -> None: ...

class Parser:
    accent: Accent
    parser_resolutions: ParserResolutions
    line_no: int
    on_tokenize: Optional[OnTokenize]

    def __init__(
        self, 
        accent: Accent, 
        parser_resolutions: ParserResolutions, 
        on_tokenize: Optional[OnTokenize] = None
    ) -> None: ...
    def tokenize(self, instruction: str) -> List[str]: ...
    def raw_parse(self, code: str) -> List[Instruction]: ...
    def transform(self, instructions: List[Instruction]) -> List[Instruction]: ...
    def parse(self, code: str) -> List[Instruction]: ...

class Interpreter:
    accent: Accent
    resolutions: RuntimeResolutions
    parser: Parser
    runtimes: List[Runtime]
    files: List[str]
    environment_loader: Optional[EnvironmentLoader]
    stopped: bool

    def __init__(
        self,
        parser_resolutions: ParserResolutions,
        resolutions: RuntimeResolutions,
        accent: Optional[Accent] = None,
        environment_loader: Optional[EnvironmentLoader] = None,
        on_tokenize: Optional[OnTokenize] = None,
        debug: bool = False
    ) -> None: ...
    def stop(self) -> None: ...
    def jump(self, runtime: Runtime, lines: int) -> None: ...
    def translate(self, environment: Environment, arg: Any) -> Union[Argument, Any]: ...
    @overload
    def execute_instructions(
        self,
        instructions: InstructionList,
        parent: Optional[Environment] = None,
        file: Optional[str] = None
    ) -> Runtime: ...
    @overload
    def execute_instructions(
        self,
        instructions: InstructionList,
        *,
        runtime: Optional[Runtime]
    ) -> Runtime: ...
    def execute_instructions(
        self,
        instructions: InstructionList,
        parent: Optional[Environment] = None,
        file: Optional[str] = None,
        runtime: Optional[Runtime] = None
    ) -> Runtime: ...
    def execute(self, code: str) -> Runtime: ...
    def interpret(self, file: str) -> Environment: ...