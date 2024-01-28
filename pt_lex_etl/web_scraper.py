from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.keys import Keys
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import csv

# Local imports
from . import schemas, web_parser
from .utils import exceptions


# Constants for Selenium
URL = "https://dre.pt/"
SEARCH_ELEMENT_LOC = (By.ID, "b2-b2-Input_ActiveItem2")  # previous: "b2-b2-Input_ActiveItem"
DIPLOMA_CONTAINER_LOC = (By.ID, "b7-b11-InjectHTMLWrapper")  # previous: "b7-b8-InjectHTMLWrapper"
CONSOLIDATED_VERSION_LOC = (
    By.XPATH,
    "//button[@title='Consultar versão consolidada']",
)
CONSOLIDATED_TOGGLE_TEXT_LOC = (By.XPATH, "//span[text()='TEXTO COMPLETO']")
CONSOLIDATED_DATE_INPUT_LOC = (By.XPATH, "//input[@id='Input_Date']")
CONSOLIDATED_DATE_BTN_LOC = (By.XPATH, "//button[@id='FiltrarButton']")
CONSOLIDATED_ACTIVE_FILTER_LOC = (By.CSS_SELECTOR, ".active")
CONSOLIDATED_CONTENT_DIV_LOC = (
    By.XPATH,
    "//div[@data-block='LegislacaoConsolidada.DiplomaCompleto']",
)

FIELDNAMES = {
    "id_field": "document",  # or "diploma"
    "content_field": "text",  # UNCOMMENT once extracting URL is included
    "url_field": "url",
}


def scrape_html(
    diploma_metadata: schemas.DiplomaMetadata,
    local_connection: bool = True,
    headless: bool = True,
    attempts_limit: int = 3,
) -> str:
    browser = (
        _connect_locally_to_website(headless)
        if local_connection
        else _connect_to_website(headless)
    )
    # TODO: Validate scraped html (with pydantic)
    try:
        html = _navigate_and_extract(
            browser,
            diploma_metadata.code,
            diploma_metadata.version,
            attempts_limit=attempts_limit,
        )
    except exceptions.WebScraperMaxAttemptsError:
        print(f"{diploma_metadata.code} was NOT extracted.")

    browser.quit()
    return html


def scrape_multiple_html(
    diplomas_metadata: list[schemas.DiplomaMetadata],
    local_connection: bool = True,
    headless: bool = True,
    attempts_limit: int = 5,
) -> dict[str, dict[str, str]]:
    browser = (
        _connect_locally_to_website(headless)
        if local_connection
        else _connect_to_website(headless)
    )
    multiple_html = {}
    for metadata in tqdm(diplomas_metadata):
        # TODO: Validate scraped html (with pydantic)
        html = _navigate_and_extract(
            browser, metadata.code, metadata.version, attempts_limit=attempts_limit
        )
        multiple_html.update(
            {metadata.code: {"html": html, "version": metadata.version}}
        )
    browser.quit()
    return multiple_html


def scrape_multiple_to_disk(
    diplomas_metadata: list[schemas.DiplomaMetadata],
    local_connection: bool = True,
    headless: bool = True,
    file_path_and_name: str = "./corpus.csv",
    error_docs_path_and_name: str = "./not_extracted.txt",
    attempts_limit: int = 2,
) -> None:
    browser = (
        _connect_locally_to_website(headless)
        if local_connection
        else _connect_to_website(headless)
    )
    
    with open(error_docs_path_and_name, "w") as file:
        file.write("")
    
    for metadata in tqdm(diplomas_metadata):
        try:
            html = _navigate_and_extract(
                browser, metadata.code, metadata.version, attempts_limit=attempts_limit
            )
        except exceptions.WebScraperMaxAttemptsError:
            print(f"{metadata.code} was not extracted.")
            with open(error_docs_path_and_name, "a") as file:
                file.write(metadata.code)

            continue

        diploma_passages = web_parser.parse_html(html, metadata.version)
        diploma_passages = [
            {
                FIELDNAMES["id_field"]: metadata.code,
                FIELDNAMES["content_field"]: diploma_passage,
                FIELDNAMES["url_field"]: browser.current_url,
            }
            for diploma_passage in diploma_passages
        ]

        with open(file_path_and_name, "a") as file:
            writer = csv.DictWriter(
                file, fieldnames=list(FIELDNAMES.values()), delimiter="\t"
            )
            if file.tell() == 0:
                writer.writeheader()
            writer.writerows(diploma_passages)

        # print(f"Diploma '{metadata.code}' completed.")

    browser.quit()
    print("All scraping, parsing, and exporting completed! 💪")


def _connect_to_website(headless: bool = True) -> WebDriver:
    options = Options()
    options.headless = headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    browser = webdriver.Remote("http://127.0.0.1:4444/wd/hub", options=options)
    browser.get(URL)
    return browser


def _connect_locally_to_website(headless: bool = True) -> WebDriver:
    options = Options()
    options.headless = headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    chrome_service = Service(ChromeDriverManager().install())
    browser = webdriver.Chrome(service=chrome_service, options=options)
    browser.get(URL)
    return browser


def _navigate_and_extract(
    browser: WebDriver,
    diploma_code: str,
    version: str | None = None,
    attempts_limit: int = 5,
) -> str:
    for _ in range(attempts_limit):
        try:
            # Search for Diploma within website.
            element = _find_web_element(browser, SEARCH_ELEMENT_LOC)
            element.clear()
            element.send_keys(diploma_code, Keys.ENTER)

            # Search within results: select relevant diploma.
            partial_link_xpath = _build_partial_link_xpath(diploma_code)
            element = _find_web_element(browser, (By.XPATH, partial_link_xpath))
            # element.click()
            browser.get(element.get_attribute("href"))

            # Return the Diploma's HTML.
            return (
                _grab_html(browser)
                if not version
                else _grab_consolidated_html(browser, version)
            )

        except Exception as e:
            print(f"Exception type: {type(e).__name__}\n")

    # browser.quit()
    # raise Exception("Reached attempts limit.")
    raise exceptions.WebScraperMaxAttemptsError


def _build_partial_link_xpath(diploma_code: str) -> str:
    parsed_code = diploma_code.lower().replace("/", "-")
    parsed_code = parsed_code.split()
    parsed_code = f"{parsed_code[0]}/{parsed_code[-1]}"
    return f"//a[contains(@href, '{parsed_code}') and not(contains(@href, 'legislacao-consolidada'))]"


def _grab_html(browser: WebElement):
    # Grab the Diploma's content HTML element and return its text.
    element = _find_web_element(browser, DIPLOMA_CONTAINER_LOC)
    return element.get_attribute("innerHTML")


def _grab_consolidated_html(browser: WebElement, version_date: str):
    # navigate to consolidated version
    element = _find_web_element(browser, CONSOLIDATED_VERSION_LOC)
    element.click()

    # toggle full text
    element = _find_web_element(browser, CONSOLIDATED_TOGGLE_TEXT_LOC)
    element.click()

    # change consolidated version date
    element = _find_web_element(browser, CONSOLIDATED_DATE_INPUT_LOC)
    element.clear()
    element.send_keys(version_date, Keys.ENTER)

    # filter version by date
    element = _find_web_element(browser, CONSOLIDATED_DATE_BTN_LOC)
    element.click()

    # guarantee text is updated
    WebDriverWait(browser, 10).until(
        expected_conditions.invisibility_of_element_located(
            CONSOLIDATED_ACTIVE_FILTER_LOC
        )
    )

    # scrape full text
    element = _find_web_element(browser, CONSOLIDATED_CONTENT_DIV_LOC)
    return element.get_attribute("innerHTML")


def _find_web_element(browser: WebDriver, locator_tuple: tuple) -> WebElement:
    return WebDriverWait(browser, 10).until(
        expected_conditions.element_to_be_clickable(locator_tuple)
    )
