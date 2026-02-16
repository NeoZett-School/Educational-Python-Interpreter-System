from typing import List, Dict, Union, Optional, TypeAlias, Callable, Final, Any, overload
from dataclasses import dataclass
import os

from .memory import (
    ArgumentList,
    InstructionList,
    Instruction,
    Argument,
    Environment
)

from .exceptions import (
    ParserError, 
    InterpretationError,
    UnknownToken,
    AlreadyInterpreted
)

ParserResolver: TypeAlias = Callable[["Parser", InstructionList, int], int]
ParserResolutions: TypeAlias = Dict[str, ParserResolver]

RuntimeResolver: TypeAlias = Callable[["Interpreter", "Runtime", ArgumentList], None]
RuntimeResolutions: TypeAlias = Dict[str, RuntimeResolver]

EnvironmentLoader: TypeAlias = Callable[[Environment], None]
OnTokenize: TypeAlias = Callable[["Parser", str], None]

NO_TOKEN: Final = object()
NOT_FOUND: Final = object()

def debug_method(parser: "Parser", instruction: str) -> None:
    print(parser.line_no, instruction)

def parse_number(text: str) -> Union[str, int, float]:
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text

def default_cast(text: str) -> Any:
    lower_text = text.lower()
    match lower_text:
        case "true":
            return True
        case "false":
            return False
        case "none":
            return None
        case _:
            return parse_number(text)

@dataclass(slots=True)
class Accent:
    """The accent of the interpretation"""

    navigator: str = "."
    delimiter: str = ","
    str_prefix: str = "'"
    str_suffix: str = "'"
    comment: str = "//"
    suffix: str = ";"

    value_caster: Callable[[str], Any] = default_cast
    
    def is_string(self, s: str) -> bool:
        return s.startswith(self.str_prefix) and s.endswith(self.str_suffix)
    
    def extract_str(self, s: str) -> str:
        return s.strip().removeprefix(self.str_prefix).removesuffix(self.str_suffix)
    
    def parts(self, s: str) -> List[str]:
        return s.split(self.navigator)

@dataclass(slots=True)
class Runtime(Environment):
    """Runtime environments, for files, functions and other runtime."""

    file: str = "<core>"
    line_no: int = 0
    jump: int = 1
    stopped: bool = False
    
    def stop(self) -> None:
        self.stopped = True

class Parser:
    """Pure structural parser with parser-time resolvers."""

    __slots__ = (
        "accent", "parser_resolutions", "on_tokenize", "line_no"
    )

    def __init__(
        self, 
        accent: Accent, 
        parser_resolutions: ParserResolutions, 
        on_tokenize: Optional[OnTokenize] = None
    ) -> None:
        self.accent = accent
        self.parser_resolutions = parser_resolutions
        self.on_tokenize = on_tokenize

        self.line_no = 0
    
    def tokenize(self, instruction: str) -> List[str]:
        if self.on_tokenize:
            self.on_tokenize(self, instruction)

        acc = []
        buf = []
        in_string = False

        sp = self.accent.str_prefix
        ss = self.accent.str_suffix
        dl = self.accent.delimiter

        i = 0
        while i < len(instruction):
            if in_string:
                if instruction.startswith(ss, i):
                    acc.append("".join(buf) + ss)
                    buf.clear()
                    in_string = False
                    i += len(ss)
                    continue
                buf.append(instruction[i])
                i += 1
                continue

            if instruction.startswith(sp, i):
                buf.append(sp)
                in_string = True
                i += len(sp)
                continue

            if instruction.startswith(dl, i):
                acc.append("".join(buf).strip())
                buf.clear()
                i += len(dl)
                continue

            buf.append(instruction[i])
            i += 1

        if in_string:
            print(instruction)
            raise ParserError("Unterminated string literal")

        if buf:
            acc.append("".join(buf).strip())

        return [a for a in acc if a]
    
    def raw_parse(self, code: str) -> List[Instruction]:
        raw_instructions = code.split(self.accent.suffix)
        instructions = []

        self.line_no = 0

        for raw in raw_instructions:
            self.line_no += raw.count("\n")
            text = raw.replace("\n", "").strip()

            if not text or text.startswith(self.accent.comment):
                continue

            parts = self.tokenize(text)
            if not parts:
                continue

            instructions.append(
                Instruction(token=parts[0].lower(), args=parts[1:], line=self.line_no + 1)
            )

        return instructions
    
    def transform(self, instructions: List[Instruction]) -> List[Instruction]:
        """Apply parser_resolutions that may consume blocks and emit new instructions."""

        output = []
        i = 0

        while i < len(instructions):
            inst = instructions[i]
            resolver = self.parser_resolutions.get(inst.token)

            if resolver:
                i = resolver(self, instructions, i)
                continue

            output.append(inst)
            i += 1

        return output
    
    def parse(self, code: str) -> List[Instruction]:
        try:
            return self.transform(self.raw_parse(code))
        except Exception as e:
            raise ParserError(f"Error occured while parsing (line {self.line_no + 1}): {e.args}") from e

class Interpreter:
    """Interpret code using a parser for runtime resolvers."""

    __slots__ = (
        "accent", "runtime_resolutions", "parser", "runtimes", "files", 
        "environment_loader", "stopped", "_debug"
    )

    def __init__(
        self,
        parser_resolutions: ParserResolutions,
        runtime_resolutions: RuntimeResolutions,
        accent: Optional[Accent] = None,
        environment_loader: Optional[EnvironmentLoader] = None,
        on_tokenize: Optional[OnTokenize] = None,
        debug: bool = False
    ) -> None:
        self.accent = accent or Accent()
        self.runtime_resolutions = runtime_resolutions
        self.parser = Parser(self.accent, parser_resolutions, on_tokenize if on_tokenize else debug_method if debug else None)
        self.runtimes = []
        self.files = []

        self.environment_loader = environment_loader
        self.stopped = False

        self._debug = debug

    def stop(self) -> None:
        self.stopped = True
    
    def jump(self, runtime: Runtime, lines: int) -> None:
        runtime.jump = lines
    
    def translate(self, environment: Environment, arg: Any) -> Union[Argument, Any]:
        if not isinstance(arg, str):
            return arg
        
        if self.accent.is_string(arg):
            text = self.accent.extract_str(arg)
            value = self.accent.value_caster(text)
            return Argument(as_text=text, as_value=value)
        
        parts = self.accent.parts(arg)
        count = len(parts)

        current_env = environment

        has_star = False
        for i, part in enumerate(parts):
            if part.startswith("*"):
                part = part.removeprefix("*")
                has_star = True
            memory = current_env.resolve(part, NOT_FOUND)

            if memory is NOT_FOUND:
                text = self.accent.extract_str(arg)
                value = self.accent.value_caster(text)
                return Argument(as_text=text, as_value=value)
            
            if i == count - 1:
                text = "*" + part if has_star else part
                value = memory.value
                return Argument(
                    as_text = text,
                    as_value = value,
                    obj = memory
                )
            
            if not isinstance(memory.value, Environment):
                file = environment.file if hasattr(environment, 'file') else "<code>"
                raise InterpretationError(
                    f"File '{file}': Cannot navigate through non-object '{part}'"
                )

            current_env = memory.value
    
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
    ) -> Runtime:
        runtime = runtime or Runtime(parent=parent, file=file or self.files[-1] if len(self.files) > 0 else "<code>")
        self.runtimes.append(runtime)

        if self.environment_loader:
            self.environment_loader(runtime)

        try:
            i = 0
            count = len(instructions)
            while i < count:
                if runtime.stopped or self.stopped:
                    break

                inst = instructions[i]
                runtime.line_no = inst.line

                resolver = self.runtime_resolutions.get(inst.token)
                if not resolver:
                    raise UnknownToken(
                        f"File '{runtime.file}', line {inst.line}: Unknown token '{inst.token}'"
                    )
                
                resolved_args = [self.translate(runtime, arg) for arg in inst.args]

                try:
                    resolver(self, runtime, resolved_args)
                except Exception as e:
                    if isinstance(e, InterpretationError):
                        e.args = (f"File '{runtime.file}', line {inst.line} -> {e.args[0]}",)
                        raise e
                    
                    exc_type = type(e)
                    exc_name = f"{exc_type.__module__}.{exc_type.__qualname__}"
                    
                    indent = "    " 
                    arg_lines = "\n".join([f"{indent}{str(arg)}" for arg in e.args])

                    raise InterpretationError(
                        f'File "{runtime.file}", line {inst.line}: execution failed\n'
                        f'Caused by {exc_name}: \n'
                        f'{arg_lines}'
                    ) from e
                
                i += runtime.jump
                runtime.jump = 1

        finally:
            self.runtimes.pop()
        
        return runtime
    
    def execute(self, code: str) -> Runtime:
        instructions = self.parser.parse(code)
        return self.execute_instructions(instructions)

    def interpret(self, file: str) -> Environment:
        file = os.path.abspath(file)

        if file in self.files:
            raise AlreadyInterpreted(f"File '{file}' is already being interpreted")

        with open(file, "r", encoding="utf-8") as f:
            self.files.append(file)
            try:
                env = self.execute(f.read())
            finally:
                self.files.remove(file)
        
        return env