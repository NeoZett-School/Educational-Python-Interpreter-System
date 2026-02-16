from typing import List, Optional
from dataclasses import dataclass

from .core import (
    ParserResolver, RuntimeResolver, 
    ParserResolutions, RuntimeResolutions, 
    EnvironmentLoader, OnTokenize, 
    Accent, Interpreter
)

@dataclass(slots=True)
class Syntax:
    name: str
    internal: bool = False
    parser_resolver: Optional[ParserResolver] = None
    runtime_resolver: Optional[RuntimeResolver] = None

class SyntaxTree:
    __slots__ = ("syntax_list", "internal_format", "_syntax_dict")

    def __init__(self, syntax_list: Optional[List[Syntax]] = None, internal_format: str = "__{}__") -> None:
        self.syntax_list = syntax_list or []
        self.internal_format = internal_format

        self._syntax_dict = None
    
    @property
    def syntax_dict(self) -> "SyntaxDict":
        if not self._syntax_dict:
            self._syntax_dict = SyntaxDict(*self.syntax_list)
        return self.syntax_dict
    
    @property
    def parser_resolutions(self) -> ParserResolutions:
        return {
            syntax.name: syntax.parser_resolver for syntax in self.syntax_list 
            if syntax.parser_resolver is not None
        }
    
    @property
    def runtime_resolutions(self) -> RuntimeResolutions:
        return {
            syntax.name if not syntax.internal else self.internal_format.format(syntax.name): syntax.runtime_resolver 
            for syntax in self.syntax_list if syntax.runtime_resolver is not None
        }
    
    def create_interpreter(
        self, 
        accent: Optional[Accent] = None, 
        environment_loader: Optional[EnvironmentLoader] = None, 
        on_tokenize: Optional[OnTokenize] = None,
        debug: bool = False
    ) -> Interpreter:
        return Interpreter(self.parser_resolutions, self.runtime_resolutions, accent, environment_loader, on_tokenize, debug)

class SyntaxDict:
    __slots__ = ("syntax",)

    def __init__(self, *syntax: Syntax) -> None:
        self.syntax = {syntax.name: syntax for syntax in syntax}

    def as_list(self) -> List[Syntax]:
        return list(self.syntax.values())
    
    def update(self, other: "SyntaxDict") -> None:
        self.syntax.update(other.syntax)
    
    def get(self, name: str) -> Syntax:
        return self.syntax[name]
    
    def create_syntax_tree(self) -> SyntaxTree:
        return SyntaxTree(self.as_list())