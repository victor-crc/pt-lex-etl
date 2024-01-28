from typing import List
from bs4 import BeautifulSoup


# CURRENT METHOD: ==================================================================== //
# –– Excludes tables.
def parse_file(file: str) -> List[str]:
    soup = BeautifulSoup(file, "html.parser")
    passages = []
    for child in soup.children:
        if child.name == "table":
            passages.append("[TABELA]")
        elif child.name == "ol":
            for grandchild in child.children:
                passages.append(grandchild.text)
        else:
            passages.append(child.text)
    return passages
