import config
from open_my_banks.banks import openbank
import requests
import sys, os
import time


try:
    openbank = openbank.OpenBankBank(
        config.REMOTE_SELENIUM_URL,
        config.OPENBANK_USER_ID_TYPE,
        config.OPENBANK_USER_ID,
        config.OPENBANK_USER_PASSWORD,
    )
    openbank.fetch_auth_token()
    openbank.fetch_accounts()
    account = openbank.accounts[config.OPENBANK_CONTRACT_NUMBER]
    operations = account.get_operations()
    last_operation_id = next(operations).id
    while True:
        more_ops = account.get_operations_since(last_operation_id)
        if len(more_ops) > 0:
            last_operation_id = more_ops[0].id
        for op in more_ops:
            msg = (
                f"New {'income' if op.is_income else 'outcome'}\n"
                f"Concept: {op.concept}\n"
                f"Amount: {op.amount}\n"
                f"Now you have: {op.balance_after}"
            )
            requests.get(
                f"https://api.telegram.org/botA_TELEGRAM_BOT_TOKEN/sendMessage?chat_id=A_TELEGRAM_CHAT_ID&text={msg}"
            )
            last_operation_id = op.id

        time.sleep(60)

    from IPython import embed

    embed()

except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)
    import ipdb

    ipdb.set_trace()
    pass
