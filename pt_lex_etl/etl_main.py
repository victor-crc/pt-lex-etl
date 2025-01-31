from pydantic import validate_call
from . import schemas, web_scraper, web_parser, file_parser


@validate_call
def etl_published_diploma(
    diploma_metadata: schemas.DiplomaMetadata,
    local_connection: bool = True,
    browser_host: str = "127.0.0.1",
    browser_port: str = "4444",
    headless: bool = True,
) -> list[str]:
    """
    Find, scrape and parse diploma content.
    Note: If `local_connection` is False, it requires
      docker's selenium/standalone-chrome to be running.
    """
    html_content = web_scraper.scrape_html(
        diploma_metadata=diploma_metadata,
        local_connection=local_connection,
        browser_host=browser_host,
        browser_port=browser_port,
        headless=headless,
    )
    diploma_passages = web_parser.parse_html(html_content, diploma_metadata.version)
    return diploma_passages


@validate_call
def etl_multiple_published_diplomas(
    diplomas_metadata: list[schemas.DiplomaMetadata],
    local_connection: bool = True,
    headless: bool = True,
) -> dict[str, list[str]]:
    """
    Find, scrape and parse multiple diplomas.
    Note: If `local_connection` is False, it requires
      docker's `selenium/standalone-chrome` to be running.
    """
    print("Starting scraping routine...")
    multiple_html = web_scraper.scrape_multiple_html(
        diplomas_metadata=diplomas_metadata,
        local_connection=local_connection,
        headless=headless,
    )
    print("Parsing diplomas...")
    multiple_diplomas_passages = web_parser.parse_multiple_html(multiple_html)
    print("ETL completed 💪")
    return multiple_diplomas_passages


@validate_call
def etl_multiple_published_to_disk(
    diplomas_metadata: list[schemas.DiplomaMetadata],
    local_connection: bool = True,
    headless: bool = True,
    file_path_and_name: str = "./corpus.csv",
) -> None:
    """
    Find, scrape, parse and export multiple diplomas to local file.
    Note: If `local_connection` is False, it requires
      docker's `selenium/standalone-chrome` to be running.
    """
    print("Starting scraping routine...")
    web_scraper.scrape_multiple_to_disk(
        diplomas_metadata=diplomas_metadata,
        local_connection=local_connection,
        headless=headless,
        file_path_and_name=file_path_and_name,
    )
    print("ETL completed 💪")


@validate_call
def etl_diploma_proposal(diploma_file: str) -> list[str]:
    """Parse diploma content from file."""
    # raise NotImplementedError("The function still lacks an input interface.")
    return file_parser.parse_file(diploma_file)
