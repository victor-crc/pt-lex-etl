"""Pre Processing (Parser) for web scraped Laws'

Laws' HTML strings are fetched from DRE's website: https://dre.pt/.
"""

from typing import Dict, Final, List, Union
import re

from bs4 import BeautifulSoup
from bs4.element import Tag
import pandas as pd
import numpy as np
from tqdm import tqdm


# Constants
INTRO_DIV_IDENTIFIER: Final[Dict[str, str]] = {"id": "b11-b2-InjectHTMLWrapper"}
ARTICLES_TABLE_IDENTIFIER: Final[Dict[str, str]] = {"class": '"table"'}
TITLE_DIV_IDENTIFIER: Final[Dict[str, re.Pattern]] = {"id": re.compile("C_Titulo$")}
CONTENT_DIV_IDENTIFIER: Final[Dict[str, re.Pattern]] = {
    "id": re.compile("InjectHTMLWrapper$")
}


def parse_multiple_html(
    multiple_html: Dict[str, Dict[str, str]]
) -> Dict[str, List[str]]:
    parsed_diplomas = {}
    for diploma_code, diploma_mapping in tqdm(multiple_html.items()):
        parsed_diplomas.update(
            {
                diploma_code: parse_html(
                    diploma_mapping["html"], diploma_mapping["version"]
                )
            }
        )
    return parsed_diplomas


def parse_html(html: str, version: Union[str, None] = None) -> List[str]:
    return _parse_original_html(html) if not version else _parse_consolidated_html(html)


def _parse_original_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    passages = [
        child.text.strip()
        for child in soup.children
        if child.text != "\n" and child.text.strip() != ""
    ]
    # TODO: Review if this is a robust solution to when the parsed document
    # is not split into passages.
    if len(passages) == 1:
        passages = passages[0].split("\n")
    return passages


def _parse_consolidated_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    intro = soup.find("div", INTRO_DIV_IDENTIFIER)
    articles = soup.find("table", ARTICLES_TABLE_IDENTIFIER)
    paragraphs = _parse_consolidated_articles(articles)
    intro_series = _format_consolidated_passages(intro.get_text())
    paragraphs_series = _format_consolidated_passages(paragraphs)
    diploma_text_list = intro_series.append(paragraphs_series).tolist()
    return diploma_text_list


def _parse_consolidated_articles(articles: Tag) -> List[str]:
    paragraphs: List[str] = []
    for tr in articles.find_all("tr"):
        title = tr.find_all("div", TITLE_DIV_IDENTIFIER)
        content = tr.find_all("div", CONTENT_DIV_IDENTIFIER)
        paragraphs = [
            *paragraphs,
            *[item.text for item in title],
            *[item.text for item in content],
        ]
    return paragraphs


def _format_consolidated_passages(passages: List[str]) -> pd.Series:
    series_passages = pd.Series(passages)
    series_passages = (
        series_passages.str.split("\n")
        .explode()
        .str.strip()
        .replace("", np.nan)
        .dropna()
        .reset_index(drop=True)
    )
    return series_passages
