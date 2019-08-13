import datetime
import time
from urllib.parse import urlencode

import requests
from loguru import logger

from ... import exceptions
from .. import base


class OpenBankAccountInfo(base.BaseAccountInfo):
    def __init__(
        self, contact_id, product, description, balance, raw_data, bank_client
    ):
        super().__init__()
        self.contact_id = contact_id
        self.product = product
        self.description = description
        self.balance = balance
        self._raw_data = raw_data
        self._bank_client = bank_client
        self._cache = {}

    @base.reauthenticate
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
        query_params = {}
        if _next_url:
            url = _next_url
        else:
            query_params["numeroContrato"] = self.contact_id
            query_params["producto"] = self.product

            if from_date:
                query_params["fechaDesde"] = from_date.strftime("%Y-%m-%d")

            if to_date:
                query_params["fechaHasta"] = to_date.strftime("%Y-%m-%d")

            if amount_from:
                query_params["importeDesde"] = amount_from
                query_params["divisaImporteDesde"] = amount_from_currency

            if amount_to:
                query_params["importeHasta"] = amount_to
                query_params["divisaImporteHasta"] = amount_to_currency

            url = "https://api.openbank.es/my-money/cuentas/movimientos"

        key = urlencode(query_params)
        cached = self._cache.get(key)
        if cached:
            res = cached
        else:
            res = requests.get(
                url, params=query_params, headers=self._bank_client.headers
            ).json()
            if res.get("status") == 401:
                raise exceptions.InvalidAuthTokenException(res)

            if from_date and (datetime.datetime.now() - from_date).days > 0:
                self._cache[key] = res

        for operation in res.get("movimientos", []):
            concept = operation["conceptoTabla"].strip()
            amount = operation["importe"]["importe"]
            category = operation["categoriaGanadora"]
            balance_after = operation["saldo"]["importe"]
            date = datetime.datetime.strptime(operation["fechaOperacion"], "%Y-%m-%d")
            is_receipt = operation["recibo"]
            yield base.Operation(
                concept, amount, category, balance_after, date, is_receipt, operation
            )

        next_url = res.get("_links", {}).get("nextPage", {}).get("href")
        if res.get("masMovimientos", False) and next_url:
            time.sleep(5)
            logger.debug(f"get_operations: Next URL: {next_url}")
            yield from self.get_operations(from_date, _next_url=next_url)

    def get_operations_since(self, operation_id):
        operations = self.get_operations()
        result_operaions = []
        for op in operations:
            if op.id != operation_id:
                logger.debug(f"get_operations_since: {operation_id} != {op.id}")
                result_operaions.append(op)
            else:
                break

        return result_operaions
