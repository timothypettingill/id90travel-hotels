"""
Scrape ID90Travel's website for available hotels.

An XML catalog of hotels available on ID90Travel's website is kept in a 
collection of \"hotel_details\" sitemaps. This script finds those sitemaps, 
extracts the relevant hotel details from the XML data, and stores it as JSON.

"""

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

from httpx import Client


@dataclass
class Hotel:
    id: str
    name: str
    destination: str


def extract_sitemap_urls(client: Client) -> List[str]:
    """
    Extract URLs for hotel detail sitemaps.

    """
    url = "https://www.id90travel.com/robots.txt"
    pattern = r"https://www\.id90travel\.com/sitemaps/sitemap_hotel_details_?\d*\.xml"
    r = client.get(url)
    r.raise_for_status()
    matches = re.findall(pattern, r.text)
    return matches


def process_sitemap(client: Client, url: str) -> List[Optional[Hotel]]:
    """
    Create `Hotel` objects from sitemap XML data.

    """

    def _is_hotel_detail_url(url:str) -> bool:
        """
        Validate whether a sitemap URL is for a hotel detail page.

        A valid hotel detail URL follows the form https://www.id90travel.com/hotels/details/<destination>/<name>/<id>.

        """
        pattern = "^https://www\.id90travel\.com/hotels/details/.+$"
        match = re.match(pattern, url)
        if match:
            return True
        else:
            return False

    def _parse_hotel_detail_url(url: str) -> Optional[Hotel]:
        """
        Create a `Hotel` object from the information contained in a hotel 
        detail sitemap URL.

        """
        url_as_path = Path(url)
        id = url_as_path.parts[-1]
        name = url_as_path.parts[-2]
        destination = url_as_path.parts[-3]
        return Hotel(id=id, name=name, destination=destination)

    r = client.get(url)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    namespaces = {
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "default": "http://www.sitemaps.org/schemas/sitemap/0.9",
    }
    matches = root.findall(".//default:loc", namespaces=namespaces)
    urls = [elem.text for elem in matches]
    valid_urls = [url for url in urls if _is_hotel_detail_url(url)]
    hotels = [_parse_hotel_detail_url(url) for url in valid_urls]
    return hotels


def main() -> None:
    """
    Main execution loop.

    """
    output_filepath = (
        # <repository_root>/id90travel-hotels.json
        Path(__file__).parents[2].joinpath("id90travel-hotels.json")
    )
    with Client() as client:
        sitemap_urls = extract_sitemap_urls(client)
        hotels = []
        for url in sitemap_urls:
            hotels.extend(process_sitemap(client, url))

        hotels_as_dicts = [asdict(hotel) for hotel in hotels]
        with open(output_filepath, "w") as f:
            json.dump(hotels_as_dicts, f, indent=4)


if __name__ == "__main__":
    main()
