class FullColumnException(RuntimeError):
    pass


class NotCurrentPlayerMoveException(RuntimeError):
    pass


class GameOverException(RuntimeError):
    pass


class OutOfBoundsException(RuntimeError):
    pass


class InvalidUndoException(RuntimeError):
    pass


class NoActiveGameException(RuntimeError):
    """Raised when trying to access game state with no active game."""
    pass
