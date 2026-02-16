class ParserError(Exception):
    """Errors during parsing."""
class InterpretationError(Exception):
    """Errors during interpretation."""
class UnknownToken(InterpretationError):
    """The token was unknown."""
class AlreadyInterpreted(InterpretationError):
    """The file is already being interpreted."""
class ResolutionError(Exception):
    """During resolution, and error occured."""