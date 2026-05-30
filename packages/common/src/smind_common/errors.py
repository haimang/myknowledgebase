class SmindError(Exception):
    def __init__(self, message: str, *, code: str = "SMIND_ERROR") -> None:
        super().__init__(message)
        self.code = code

