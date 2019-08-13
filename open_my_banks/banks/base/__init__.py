import hashlib
from ... import exceptions
from loguru import logger
import json


class BaseBank(object):
    def __init__(self):
        super().__init__()
        pass

    @property
    def headers(self):
        raise NotImplementedError()

    def fetch_auth_token(self):
        raise NotImplementedError()

    def fetch_accounts(self, force=False):
        raise NotImplementedError()


class BaseAccountInfo(object):
    def __init__(self):
        super().__init__()
        pass

    def get_operations(
        self,
        from_date=None,
        to_date=None,
        amount_from=None,
        amount_to=None,
        amount_from_currency="EUR",
        amount_to_currency="EUR",
        _next_url=None,
    ):
        raise NotImplementedError()

    def get_operations_since(self, operation_id):
        raise NotImplementedError()


class Operation(object):
    def __init__(
        self, concept, amount, category, balance_after, date, is_receipt, raw_data
    ):
        super().__init__()
        self.concept = concept
        self.amount = amount
        self.is_income = amount >= 0
        self.category = category
        self.balance_after = balance_after
        self.date = date
        self.is_receipt = is_receipt
        self._raw_data = raw_data
        self.id = hashlib.sha256(json.dumps(self._raw_data).encode()).hexdigest()


def reauthenticate(f):
    def w(obj, *args, **kwargs):
        try:
            return f(obj, *args, **kwargs)
        except exceptions.InvalidAuthTokenException as e:
            logger.warning("Auth error, retrying auth")
            if issubclass(type(obj), BaseBank):
                obj.fetch_auth_token()
            else:
                obj._bank_client.fetch_auth_token()
            return f(obj, *args, **kwargs)

    return w
