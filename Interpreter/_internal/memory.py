from typing import List, Dict, Union, Protocol, Optional, TypeAlias, TypeVar, Generic, Any, runtime_checkable
from dataclasses import dataclass, field
from abc import ABCMeta

T = TypeVar("T")

InstructionList: TypeAlias = List["Instruction"]
ArgumentList: TypeAlias = List[Union["Argument", Any]]

@runtime_checkable
class WithAddress(Protocol, metaclass=ABCMeta):
    """A marker for classes with a 'name' addressable to the object."""

    name: str

@dataclass(slots=True)
class Instruction:
    """An instruction contains token and arguments to an execution."""

    token: str
    args: List[Union[Any, str]]
    line: int

@dataclass(slots=True)
class MemoryAddress(WithAddress, Generic[T]):
    """Memory address contains a name and value."""

    owner: "Environment"
    name: str
    value: T

@dataclass(slots=True)
class Explicit(Generic[T]):
    """Explicit is uninterpreted values that should be considered 'as-is'."""

    name: Optional[str] = None
    value: T = None

    @property
    def as_text(self) -> Optional[Union[str, T]]:
        return self.name or self.value
    
    @property
    def as_value(self) -> T:
        return self.value

@dataclass(kw_only=True, slots=True)
class Argument(Generic[T]):
    """Argument is a unified 'as_text' or 'as_value' interpretation of an argument."""

    as_text: str
    as_value: T
    obj: Optional[Union[MemoryAddress, Any]] = None

@dataclass(slots=True)
class Environment:
    """Environments can be classes, used for memory and basic storage. Inherited by runtime."""

    parent: Optional["Environment"]
    is_obj: bool = False

    memory: Dict[str, MemoryAddress[Any]] = field(default_factory=dict, init=False, repr=False)

    def resolve(self, name: str, default: Any = None) -> MemoryAddress[Any]:
        if name in self.memory:
            return self.memory[name]
        if self.parent:
            return self.parent.resolve(name, default)
        return default