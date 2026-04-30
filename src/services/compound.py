"""Compound data service — encapsulates all CompoundCloud SPARQL queries.

All SPARQL logic is centralised here; Flask routes just call these
functions and get back typed Pydantic models or plain dicts.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Optional

import requests
from wikibaseintegrator import wbi_helpers

from src.models.compound import (
    CompoundDetail,
    CompoundExperimentalDatum,
    CompoundIdentifier,
    CompoundSummary,
    CompoundToxicology,
)

COMPOUND_EP = "https://compoundcloud.wikibase.cloud/query/sparql"
QLEVER_EP = "https://qlever.cs.uni-freiburg.de/api/wikidata?format=json&query="

_QID_RE = re.compile(r"^Q\d+$")


def is_valid_qid(qid: str) -> bool:
    return bool(_QID_RE.fullmatch(qid))


# ── Individual queries ────────────────────────────────────────────────────


def get_properties(cwid: str) -> Optional[CompoundSummary]:
    """Fetch core identifiers (InChI, SMILES, formula, mass)."""
    q = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT ?cmp ?cmpLabel ?formula ?mass ?inchi ?inchiKey ?SMILES WHERE {\n"
        f"  VALUES ?cmp {{ wd:{cwid} }}\n"
        "  ?cmp wdt:P9 ?inchi ;\n"
        "       wdt:P10 ?inchiKey .\n"
        "  OPTIONAL { ?cmp wdt:P2 ?mass }\n"
        "  OPTIONAL { ?cmp wdt:P3 ?formula }\n"
        "  OPTIONAL { ?cmp wdt:P7 ?chiralSMILES }\n"
        "  OPTIONAL { ?cmp wdt:P12 ?nonchiralSMILES }\n"
        "  BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0),"
        ' IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0), "")'
        " AS ?SMILES)\n"
        "  SERVICE wikibase:label {"
        ' bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    result = wbi_helpers.execute_sparql_query(q, endpoint=COMPOUND_EP)
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    b = bindings[0]
    return CompoundSummary(
        wcid=b["cmp"]["value"],
        label=b["cmpLabel"]["value"],
        inchi=b["inchi"]["value"],
        inchikey=b["inchiKey"]["value"],
        SMILES=b.get("SMILES", {}).get("value", ""),
        formula=b.get("formula", {}).get("value", ""),
        mass=b.get("mass", {}).get("value", ""),
    )


def get_identifiers(cwid: str) -> list[CompoundIdentifier]:
    """Fetch external identifiers (CAS, PubChem, …)."""
    q = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT DISTINCT ?propertyLabel ?value ?formatterURL\n"
        "WHERE {\n"
        "  VALUES ?property { wd:P13 wd:P22 wd:P23 wd:P26 wd:P27"
        " wd:P28 wd:P36 wd:P41 wd:P43 wd:P44 wd:P45 }\n"
        "  ?property wikibase:directClaim ?valueProp .\n"
        f"  OPTIONAL {{ wd:{cwid} ?valueProp ?value }}\n"
        "  OPTIONAL { ?property wdt:P6 ?formatterURL }\n"
        "  SERVICE wikibase:label {"
        ' bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    result = wbi_helpers.execute_sparql_query(q, endpoint=COMPOUND_EP)
    bindings = result.get("results", {}).get("bindings", [])
    out: list[CompoundIdentifier] = []
    for b in bindings:
        out.append(
            CompoundIdentifier(
                property_label=b.get("propertyLabel", {}).get("value", ""),
                value=b.get("value", {}).get("value", ""),
                formatter_url=b.get("formatterURL", {}).get("value", ""),
            )
        )
    return out


def get_toxicology(cwid: str) -> list[CompoundToxicology]:
    """Fetch toxicology properties."""
    q = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT DISTINCT ?propertyLabel ?value ?formatterURL\n"
        "WHERE {\n"
        "  VALUES ?property { wd:P17 wd:P19 wd:P4 }\n"
        "  ?property wikibase:directClaim ?valueProp .\n"
        f"  OPTIONAL {{ wd:{cwid} ?valueProp ?value }}\n"
        "  OPTIONAL { ?property wdt:P6 ?formatterURL }\n"
        "  SERVICE wikibase:label {"
        ' bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    result = wbi_helpers.execute_sparql_query(q, endpoint=COMPOUND_EP)
    bindings = result.get("results", {}).get("bindings", [])
    out: list[CompoundToxicology] = []
    for b in bindings:
        out.append(
            CompoundToxicology(
                property_label=b.get("propertyLabel", {}).get("value", ""),
                value=b.get("value", {}).get("value", ""),
            )
        )
    return out


def get_experimental_data(
    cwid: str,
) -> list[CompoundExperimentalDatum]:
    """Fetch experimental data via Wikidata QLever."""
    # Step 1: resolve CompoundCloud QID → Wikidata QID
    q1 = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT ?qid WHERE {\n"
        "  wd:P5 wikibase:directClaim ?identifierProp .\n"
        f"  wd:{cwid} ?identifierProp ?wikidata .\n"
        "  BIND (iri(CONCAT("
        '"http://www.wikidata.org/entity/", ?wikidata)) AS ?qid)\n'
        "}"
    )
    r1 = wbi_helpers.execute_sparql_query(q1, endpoint=COMPOUND_EP)
    bindings = r1.get("results", {}).get("bindings", [])
    if not bindings:
        return []
    qid = bindings[0]["qid"]["value"]

    # Step 2: query Wikidata QLever for experimental properties
    q2 = (
        "PREFIX wd: <http://www.wikidata.org/entity/>\n"
        "PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        "PREFIX pr: <http://www.wikidata.org/prop/reference/>\n"
        "PREFIX wikibase: <http://wikiba.se/ontology#>\n\n"
        "SELECT DISTINCT ?propEntityLabel ?value"
        " ?unitsLabel ?source ?doi ?statement\n"
        "WHERE {\n"
        f"    <{qid}> ?propp ?statement .\n"
        "    ?statement a wikibase:BestRank ;\n"
        "      ?proppsv ["
        " wikibase:quantityAmount ?value ;"
        " wikibase:quantityUnit ?units ] .\n"
        "    ?property wikibase:claim ?propp ;"
        " wikibase:statementValue ?proppsv ;"
        " wdt:P1629 ?propEntity ;"
        " wdt:P31 wd:Q21077852 .\n"
        "    ?propEntity @en@rdfs:label ?propEntityLabel .\n"
        "    ?units @en@rdfs:label ?unitsLabel .\n"
        "    BIND (COALESCE(IF(BOUND(?sourceTmp),"
        ' ?sourceTmp, 1/0), "") AS ?source)\n'
        "    BIND (COALESCE(IF(BOUND(?doiTmp),"
        ' ?doiTmp, 1/0), "") AS ?doi)\n'
        "}"
    )
    url = QLEVER_EP + urllib.parse.quote_plus(q2)
    resp = requests.get(url, timeout=15)
    data = resp.json()
    bindings = data.get("results", {}).get("bindings", [])

    out: list[CompoundExperimentalDatum] = []
    for b in bindings:
        out.append(
            CompoundExperimentalDatum(
                property_label=b.get("propEntityLabel", {}).get("value", ""),
                value=b.get("value", {}).get("value", ""),
                units_label=b.get("unitsLabel", {}).get("value", ""),
                source=b.get("source", {}).get("value", ""),
                doi=b.get("doi", {}).get("value", ""),
                see_also=b.get("statement", {}).get("value", ""),
            )
        )
    return out


def get_full_compound(cwid: str) -> CompoundDetail:
    """Fetch everything about a compound."""
    return CompoundDetail(
        summary=get_properties(cwid),
        identifiers=get_identifiers(cwid),
        toxicology=get_toxicology(cwid),
        experimental_data=get_experimental_data(cwid),
    )
