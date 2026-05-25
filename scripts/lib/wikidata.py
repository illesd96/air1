"""Wikidata SPARQL helpers."""
from __future__ import annotations

import os
import time
from typing import Iterator
from urllib.error import HTTPError

from SPARQLWrapper import SPARQLWrapper, JSON

USER_AGENT = os.getenv("USER_AGENT", "aircraft-db/0.1 (pilles@eev-systems.com)")
ENDPOINT = "https://query.wikidata.org/sparql"

# Top-level: instances of "aircraft model" (Q15056995) OR any subclass-of "aircraft" (Q11436)
# that have an English Wikipedia article. We pull names, manufacturer, country,
# first-flight date, units built, and Commons image filename in one shot.
AIRCRAFT_SPARQL = """
SELECT DISTINCT
  ?item ?itemLabel ?itemDescription
  ?manufacturer ?manufacturerLabel
  ?country     ?countryLabel
  ?firstFlight ?introduced ?retired
  ?unitsBuilt
  ?image
  ?wpUrl
WHERE {
  ?item wdt:P31/wdt:P279* wd:Q11436 .                # aircraft (any subclass)
  ?wpUrl schema:about ?item ;
         schema:isPartOf <https://en.wikipedia.org/> .
  OPTIONAL { ?item wdt:P176  ?manufacturer . }
  OPTIONAL { ?item wdt:P495  ?country . }
  OPTIONAL { ?item wdt:P606  ?firstFlight . }
  OPTIONAL { ?item wdt:P729  ?introduced . }
  OPTIONAL { ?item wdt:P730  ?retired . }
  OPTIONAL { ?item wdt:P1092 ?unitsBuilt . }
  OPTIONAL { ?item wdt:P18   ?image . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY ?itemLabel
LIMIT %d OFFSET %d
"""


def sparql(query: str) -> dict:
    wrapper = SPARQLWrapper(ENDPOINT, agent=USER_AGENT)
    wrapper.setReturnFormat(JSON)
    wrapper.setQuery(query)
    return wrapper.queryAndConvert()


def iter_aircraft(batch: int = 500, start_offset: int = 0) -> Iterator[dict]:
    """Yield raw SPARQL result rows for every aircraft in Wikidata.

    Handles 429 rate-limits with exponential backoff and resumes from
    `start_offset` if you need to continue after a previous run.
    """
    offset = start_offset
    backoff = 60  # seconds — WDQS rate-limit window
    while True:
        try:
            result = sparql(AIRCRAFT_SPARQL % (batch, offset))
        except HTTPError as e:
            if e.code == 429:
                print(f"\n  429 at offset {offset}; sleeping {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 600)
                continue
            raise
        backoff = 60
        rows = result["results"]["bindings"]
        if not rows:
            return
        for row in rows:
            yield row
        offset += batch
        time.sleep(2)   # be polite


def qid_from_uri(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]
