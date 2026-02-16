from typing import List, Dict, Union, Protocol, Optional, TypeAlias, TypeVar, Generic, Any, runtime_checkable
from dataclasses import dataclass, field
from abc import ABCMeta

T = TypeVar("T")

InstructionList: TypeAlias = List[Instruction]
ArgumentList: TypeAlias = List[Union[Argument, Any]]

@runtime_checkable
class WithAddress(Protocol, metaclass=ABCMeta):
    name: str

@dataclass(slots=True)
class Instruction:
    token: str
    args: List[Union[Any, str]]
    line: int

@dataclass(slots=True)
class MemoryAddress(WithAddress, Generic[T]):
    owner: Environment
    name: str
    value: T

@dataclass(slots=True)
class Explicit(Generic[T]):
    name: Optional[str] = None
    value: T = None

    @property
    def as_text(self) -> Optional[Union[str, T]]: ...
    @property
    def as_value(self) -> T: ...

@dataclass(slots=True)
class Argument(Generic[T]):
    as_text: str
    as_value: T
    obj: Optional[Union[MemoryAddress, Any]] = None

@dataclass(slots=True)
class Environment:
    parent: Optional["Environment"]
    is_obj: bool = False

    memory: Dict[str, MemoryAddress[Any]] = field(default_factory=dict, init=False, repr=False)

    def resolve(self, name: str, default: Any = None) -> MemoryAddress[Any]: ...