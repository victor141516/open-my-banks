class BankException(Exception):
    pass


class BadIdTypeException(BankException):
    pass


class InvalidCredentialsException(BankException):
    pass


class CouldNotGetAuthTokenException(BankException):
    pass


class InvalidAuthTokenException(BankException):
    pass
