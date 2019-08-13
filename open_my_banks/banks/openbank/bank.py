from .account import OpenBankAccountInfo
from .. import base
from ... import exceptions
from loguru import logger
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common import exceptions as selenium_exceptions
import time


class OpenBankBank(base.BaseBank):
    def __init__(self, selenium_url, user_id_type, user_id, user_password):
        super().__init__()
        self.selenium_url = selenium_url
        self.user_id_type = user_id_type
        self.user_id = user_id
        self.user_password = user_password
        self.auth_token = None
        self.accounts = {}

    @property
    def headers(self):
        headers = {}
        if self.auth_token:
            headers["openBankAuthToken"] = self.auth_token

        return headers

    def fetch_auth_token(self):
        desiredCapabilities = DesiredCapabilities.CHROME.copy()
        chromeOptionsRemote = webdriver.ChromeOptions()
        chromeOptionsRemote.add_argument("--start-maximized")
        chromeOptionsRemote.add_argument("--disable-session-crashed-bubble")

        driver = webdriver.Remote(
            options=chromeOptionsRemote,
            command_executor=self.selenium_url,
            desired_capabilities=desiredCapabilities,
        )

        driver.get("https://www.openbank.es/")
        try:
            driver.find_element_by_css_selector(
                ".container-cookie-modal-footer-accept-span"
            ).click()
        except selenium_exceptions.NoSuchElementException:
            logger.info("No cookies screen")

        while len(driver.find_elements_by_css_selector("#login-wrapper.closed")) > 0:
            logger.debug("Opening login menu")
            driver.find_element_by_css_selector(".buttons-area__div-login").click()
        logger.debug("Login menu opened")

        document_types = {
            "NIF": "NIF",
            "NIE": "NIE",
            "SPANISH_PASSPORT": "Pasaporte español",
            "OTHER": "Otro documento extranjero",
        }

        logger.debug("Checking if selected ID type is correct")
        document_type_selector = driver.find_element_by_css_selector(
            "form.ok-login__form > .ok-login__group"
        )
        if document_type_selector.text == self.user_id_type:
            logger.debug("Selected ID type is correct")
        else:
            logger.debug("Selected ID type is not correct, changing")
            logger.debug("Open selector")
            document_type_selector.click()

            options = driver.find_elements_by_css_selector(
                "#react-select-2--list > .Select-option"
            )
            logger.debug("Available options: " + str([o.text for o in options]))
            logger.debug("Waiting to check if options have changed")
            time.sleep(1)
            while len(options) != len(
                driver.find_elements_by_css_selector(
                    "#react-select-2--list > .Select-option"
                )
            ):
                logger.debug("Options changed. Getting new one and waiting again")
                options = driver.find_elements_by_css_selector(
                    "#react-select-2--list > .Select-option"
                )
                logger.debug("New options: " + str([o.text for o in options]))
                time.sleep(1)

            logger.debug(
                f"Got final options, selecting correct one ({document_types[self.user_id_type]})"
            )
            for o in options:
                if o.text == document_types[self.user_id_type]:
                    while (
                        len(
                            driver.find_elements_by_css_selector(
                                ".ok-login__group > .ok-select > .Select.is-open"
                            )
                        )
                        > 0
                    ):
                        logger.debug("Got the correct one, clicking")
                        o.click()
                        time.sleep(0.5)
                    break
            else:
                raise exceptions.BadIdTypeException()

        logger.debug("Getting ID and password inputs")
        user_id_input = driver.find_element_by_css_selector(
            "#block-openbank-login-private .ok-login__group > div > input.ok-login__input"
        )
        user_password_input = driver.find_element_by_css_selector(
            "#block-openbank-login-private .ok-login__group > div.ok-numpad > div.ok-numpad-input input#userPassword"
        )

        logger.debug("Typing ID")
        user_id_input.send_keys(self.user_id)
        while user_id_input.get_attribute("value") != self.user_id:
            while len(user_id_input.get_attribute("value")) > 0:
                user_id_input.send_keys(Keys.BACKSPACE)
                user_id_input.send_keys(self.user_id)
            time.sleep(1)
            user_id_input.send_keys(self.user_id)
            time.sleep(1)

        logger.debug("Opening password input")
        while 1 == len(
            driver.find_elements_by_css_selector(
                "#block-openbank-login-private .ok-login__group > div.ok-numpad > div.ok-numpad-input > div.ok-numpad__keyboard.ok-numpad__keyboard-\
        -hidden"
            )
        ):
            user_password_input.click()

        logger.debug("Typing password")
        user_password_input.send_keys(self.user_password)
        while user_password_input.get_attribute("value") != self.user_password:
            while len(user_password_input.get_attribute("value")) > 0:
                user_password_input.send_keys(Keys.BACKSPACE)
                user_password_input.send_keys(self.user_password)
            time.sleep(1)
            user_password_input.send_keys(self.user_password)
            time.sleep(1)

        logger.debug("Clicking submit button")
        driver.find_element_by_css_selector(
            "#block-openbank-login-private div.ok-login__submit > button"
        ).click()

        while driver.current_url == "https://www.openbank.es/":
            if (
                len(
                    driver.find_elements_by_css_selector(
                        "#block-openbank-login-private .ok-login-error"
                    )
                )
                > 0
            ):
                logger.error("Invalid credentials")
                raise exceptions.InvalidCredentialsException()
            time.sleep(1)

        logger.debug("Waiting for login to complete")
        while not driver.current_url.startswith("https://clientes.openbank.es"):
            time.sleep(1)

        logger.debug("Getting auth token")
        auth_token_cookie = driver.get_cookie("tokenCredential")
        if auth_token_cookie is None or "value" not in auth_token_cookie:
            logger.error("Could not get auth token")
            raise exceptions.CouldNotGetAuthTokenException()

        driver.quit()
        auth_token = auth_token_cookie["value"].replace("%22", "")
        logger.debug(f"Auth token: {auth_token}")
        self.auth_token = auth_token
        return auth_token

    @base.reauthenticate
    def fetch_accounts(self, force=False):
        if len(self.accounts) > 0 and force is False:
            return

        data = requests.get(
            "https://api.openbank.es/posicion-global-total?listaSolicitada=TODOS&indicadorSaldoPreTarj=false",
            headers=self.headers,
        ).json()
        if data.get("status") == 401:
            raise exceptions.InvalidAuthTokenException(data)

        accounts = data.get("datosSalidaCuentas").get("cuentas", [])
        for account in accounts:
            viejo_contract_no = account.get("cviejo").get("numerodecontrato")
            if viejo_contract_no:
                c = account["cviejo"]
                contact_number = c["numerodecontrato"]
                product_number = c["subgrupo"]
                description = account["descripcion"].strip()
                balance = account["saldoActual"].get("importe")
                self.accounts[viejo_contract_no] = OpenBankAccountInfo(
                    contact_number, product_number, description, balance, account, self
                )

            nuevo_contract_no = account.get("cnuevo").get("numerodecontrato")
            if nuevo_contract_no:
                c = account["cnuevo"]
                contact_number = c["numerodecontrato"]
                product_number = c["producto"]
                description = account["descripcion"].strip()
                balance = account["saldoActual"].get("importe")
                self.accounts[nuevo_contract_no] = OpenBankAccountInfo(
                    contact_number, product_number, description, balance, account, self
                )
