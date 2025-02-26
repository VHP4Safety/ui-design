from flask import Blueprint, request, jsonify, send_file
import requests
from wikidataintegrator import wdi_core
import json
import re
from urllib.parse import quote, unquote
import pandas as pd
import csv
import os

aop_app = Blueprint("aop_app", __name__)


@aop_app.route("/get_dummy_data", methods=["GET"])
def get_dummy_data():
    results = [
        {"Compound": "Compound1", "SMILES": "Smile 1"},
        {"Compound": "Compound1", "SMILES": "Smile 1"},
        {"Compound": "Compound1", "SMILES": "Smile 1"},
    ]
    return jsonify(results), 200


def is_valid_qid(qid):
    return re.fullmatch(r"Q\d+", qid) is not None


def get_compounds_q(q):
    if not is_valid_qid(q):
        return jsonify({"error": "Invalid identifier format"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery_full = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT DISTINCT (substr(str(?cmp), 45) as ?ID) (?cmpLabel AS ?Term) ?SMILES (?cmp AS ?ref)\n"
        "WHERE {\n"
        "  { ?parent wdt:P21 wd:"
        + q
        + " ; wdt:P29 ?cmp . } UNION { ?cmp wdt:P21 wd:"
        + q
        + " . }\n"
        "  ?cmp wdt:P1 ?type ; rdfs:label ?cmpLabel . FILTER(lang(?cmpLabel) = 'en')\n"
        "  ?type rdfs:label ?typeLabel . FILTER(lang(?typeLabel) = 'en')\n"
        "  OPTIONAL { ?cmp wdt:P7 ?chiralSMILES }\n"
        "  OPTIONAL { ?cmp wdt:P12 ?nonchiralSMILES }\n"
        '  BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0), IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0), "") AS ?SMILES)\n'
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(
            sparqlquery_full, endpoint=compoundwikiEP, as_dataframe=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    compound_list = []
    for _, row in compound_dat.iterrows():
        compound_list.append({"ID": row[1], "Term": row[2], "SMILES": row[0]})
    return jsonify(compound_list), 200


@aop_app.route("/get_compounds", methods=["GET"])
def get_compounds_VHP():
    return get_compounds_q("Q2059")


@aop_app.route("/get_compound_identifiers/<cwid>")
def show_compounds_identifiers_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT ?propertyLabel ?value\n"
        "WHERE {\n"
        "  VALUES ?property { wd:P3 wd:P2 wd:P32 }\n"
        "  ?property wikibase:directClaim ?valueProp .\n"
        "  OPTIONAL { wd:" + cwid + " ?valueProp ?value }\n"
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP, as_dataframe=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    compound_list = []
    for _, row in compound_dat.iterrows():
        compound_list.append(
            {"propertyLabel": row["propertyLabel"], "value": str(row["value"])}
        )
    return jsonify(compound_list), 200


@aop_app.route("/get_compound_expdata/<cwid>")
def show_compounds_expdata_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n"
        "PREFIX wid: <http://www.wikidata.org/entity/>\n"
        "PREFIX widt: <http://www.wikidata.org/prop/direct/>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n\n"
        "SELECT ?propEntityLabel ?value ?unitsLabel ?source ?doi\n"
        "WHERE {\n"
        "  wd:P5 wikibase:directClaim ?identifierProp .\n"
        "  wd:" + cwid + " ?identifierProp ?wikidata .\n"
        '  BIND (iri(CONCAT("http://www.wikidata.org/entity/", ?wikidata)) AS ?qid)\n'
        "  SERVICE <https://query.wikidata.org/sparql> {\n"
        "    ?qid ?propp ?statement .\n"
        "    ?statement a wikibase:BestRank ;\n"
        "      ?proppsv [ wikibase:quantityAmount ?value ; wikibase:quantityUnit ?units ] .\n"
        "    OPTIONAL { ?statement prov:wasDerivedFrom/pr:P248 ?source . OPTIONAL { ?source wdt:P356 ?doi . } }\n"
        "    ?property wikibase:claim ?propp ; wikibase:statementValue ?proppsv ; widt:P1629 ?propEntity ; widt:P31 wid:Q21077852 .\n"
        "    ?propEntity rdfs:label ?propEntityLabel . FILTER ( lang(?propEntityLabel) = 'en' )\n"
        "    ?units rdfs:label ?unitsLabel . FILTER ( lang(?unitsLabel) = 'en' )\n"
        '    BIND (COALESCE(IF(BOUND(?source), ?source, 1/0), "") AS ?source)\n'
        '    BIND (COALESCE(IF(BOUND(?doi), ?doi, 1/0), "") AS ?doi)\n'
        "  }\n"
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP, as_dataframe=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    compound_list = []
    for _, row in compound_dat.iterrows():
        compound_list.append(
            {
                "propEntityLabel": row["propEntityLabel"],
                "value": row["value"],
                "unitsLabel": row["unitsLabel"],
                "source": row["source"],
                "doi": row["doi"],
            }
        )
    return jsonify(compound_list), 200


@aop_app.route("/get_compound_properties/<cwid>")
def show_compounds_properties_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT ?cmp ?cmpLabel ?inchiKey ?SMILES WHERE {\n"
        "  VALUES ?cmp { wd:" + cwid + " }\n"
        "  ?cmp wdt:P10 ?inchiKey .\n"
        "  OPTIONAL { ?cmp wdt:P7 ?chiralSMILES }\n"
        "  OPTIONAL { ?cmp wdt:P12 ?nonchiralSMILES }\n"
        '  BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0), IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0), "") AS ?SMILES)\n'
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP, as_dataframe=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if compound_dat.empty:
        return jsonify({"error": "No data found"}), 404
    compound_list = [
        {
            "wcid": compound_dat.at[0, "cmp"],
            "label": compound_dat.at[0, "cmpLabel"],
            "inchikey": compound_dat.at[0, "inchiKey"],
            "SMILES": compound_dat.at[0, "SMILES"],
        }
    ]
    return jsonify(compound_list), 200


@aop_app.route("/get_compounds_parkinson", methods=["GET"])
def get_compounds_VHP_CS2():
    return get_compounds_q("Q5050")


def fetch_predictions(smiles, models, metadata, threshold=6.5):
    url = "https://qsprpred.cloud.vhp4safety.nl/api"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/json",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Priority": "u=0",
    }
    body = {"smiles": smiles, "models": models, "format": "json"}
    try:
        response = requests.post(
            url, headers=headers, data=json.dumps(body), timeout=20
        )
    except Exception as e:
        return {"error": str(e)}
    if response.status_code == 200:
        try:
            predictions = response.json()
        except Exception as e:
            return {"error": str(e)}
        filtered_predictions = []
        for prediction in predictions:
            try:
                filtered_prediction = {"smiles": prediction["smiles"]}
                for key, value in prediction.items():
                    if key != "smiles":
                        try:
                            val = float(value)
                        except Exception:
                            continue
                        if val >= threshold:
                            new_key = re.sub(r"prediction \((.+)\)", r"\1", key)
                            filtered_prediction[new_key] = value
                if models and models[0] in metadata:
                    filtered_prediction.update(metadata.get(models[0], {}))
                filtered_predictions.append(filtered_prediction)
            except Exception:
                continue
        return filtered_predictions
    else:
        return {"error": response.text}


@aop_app.route("/get_predictions", methods=["POST"])
def get_predictions():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON input"}), 400
    smiles = data.get("smiles", [])
    models = data.get("models", [])
    metadata = data.get("metadata", {})
    try:
        threshold = float(data.get("threshold", 6.5))
    except Exception:
        threshold = 6.5
    results = fetch_predictions(smiles, models, metadata, threshold)
    return jsonify(results)


AOPWIKISPARQL_ENDPOINT = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/"


def extract_ker_id(ker_uri):
    return ker_uri.split("/")[-1] if ker_uri else "Unknown"


def fetch_sparql_data(query):
    try:
        response = requests.get(
            AOPWIKISPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}
    if response.status_code != 200:
        return {"error": "Failed to fetch SPARQL data"}
    try:
        data = response.json()
    except Exception as e:
        return {"error": str(e)}
    cytoscape_elements = []
    node_dict = {}
    for result in data.get("results", {}).get("bindings", []):
        ke_upstream = result.get("KE_upstream", {}).get("value", "")
        ke_upstream_title = result.get("KE_upstream_title", {}).get("value", "")
        ke_downstream = result.get("KE_downstream", {}).get("value", "")
        ke_downstream_title = result.get("KE_downstream_title", {}).get("value", "")
        mie = result.get("MIE", {}).get("value", "")
        ao = result.get("ao", {}).get("value", "")
        ker_uri = result.get("KER", {}).get("value", "")
        ker_id = extract_ker_id(ker_uri)
        aop = result.get("aop", {}).get("value", "")
        aop_title = result.get("aop_title", {}).get("value", "")
        if ke_upstream not in node_dict:
            node_dict[ke_upstream] = {
                "data": {
                    "id": ke_upstream,
                    "label": ke_upstream_title,
                    "KEupTitle": ke_upstream_title,
                    "is_mie": ke_upstream == mie,
                    "uniprot_id": result.get("uniprot_id", {}).get("value", ""),
                    "protein_name": result.get("protein_name", {}).get("value", ""),
                    "organ": result.get("KE_upstream_organ", {}).get("value", ""),
                    "aop": [aop] if aop else [],
                    "aop_title": [aop_title] if aop_title else [],
                }
            }
        else:
            if aop and aop not in node_dict[ke_upstream]["data"]["aop"]:
                node_dict[ke_upstream]["data"]["aop"].append(aop)
            if (
                aop_title
                and aop_title not in node_dict[ke_upstream]["data"]["aop_title"]
            ):
                node_dict[ke_upstream]["data"]["aop_title"].append(aop_title)
        if ke_upstream == mie:
            node_dict[ke_upstream]["data"]["is_mie"] = True
        if ke_downstream not in node_dict:
            node_dict[ke_downstream] = {
                "data": {
                    "id": ke_downstream,
                    "label": ke_downstream_title,
                    "is_ao": ke_downstream == ao,
                    "uniprot_id": result.get("uniprot_id", {}).get("value", ""),
                    "protein_name": result.get("protein_name", {}).get("value", ""),
                    "organ": result.get("KE_downstream_organ", {}).get("value", "nose"),
                    "aop": [aop] if aop else [],
                    "aop_title": [aop_title] if aop_title else [],
                }
            }
        else:
            if aop and aop not in node_dict[ke_downstream]["data"]["aop"]:
                node_dict[ke_downstream]["data"]["aop"].append(aop)
            if (
                aop_title
                and aop_title not in node_dict[ke_downstream]["data"]["aop_title"]
            ):
                node_dict[ke_downstream]["data"]["aop_title"].append(aop_title)
        if ke_downstream == ao:
            node_dict[ke_downstream]["data"]["is_ao"] = True
        edge_id = f"{ke_upstream}_{ke_downstream}"
        cytoscape_elements.append(
            {
                "data": {
                    "id": edge_id,
                    "source": ke_upstream,
                    "target": ke_downstream,
                    "curie": f"aop.relationships:{ker_id}",
                    "ker_label": ker_id,
                }
            }
        )
    return list(node_dict.values()) + cytoscape_elements


@aop_app.route("/get_aop_network")
def get_aop_network():
    mies = request.args.get("mies", "")
    if not mies:
        return jsonify({"error": "MIEs parameter is required"}), 400
    AOPWIKIPARKINSONSPARQL_QUERY = (
        "SELECT DISTINCT ?aop ?aop_title ?MIEtitle ?MIE ?KE_downstream ?KE_downstream_title  ?KER ?ao ?AOtitle ?KE_upstream ?KE_upstream_title ?KE_upstream_organ ?KE_downstream_organ\n"
        "WHERE {\n"
        "  VALUES ?MIE { " + mies + " }\n"
        "  ?aop a aopo:AdverseOutcomePathway ;\n"
        "       dc:title ?aop_title ;\n"
        "       aopo:has_adverse_outcome ?ao ;\n"
        "       aopo:has_molecular_initiating_event ?MIE .\n"
        "  ?MIE dc:title ?MIEtitle .\n"
        "  ?aop aopo:has_key_event_relationship ?KER .\n"
        "  ?KER a aopo:KeyEventRelationship ;\n"
        "       aopo:has_upstream_key_event ?KE_upstream ;\n"
        "       aopo:has_downstream_key_event ?KE_downstream .\n"
        "  ?KE_upstream dc:title ?KE_upstream_title .\n"
        "  ?KE_downstream dc:title ?KE_downstream_title .\n"
        "  OPTIONAL { ?KE_upstream aopo:OrganContext ?KE_upstream_organ . ?KE_downstream aopo:OrganContext ?KE_downstream_organ . }\n"
        "}"
    )
    data = fetch_sparql_data(AOPWIKIPARKINSONSPARQL_QUERY)
    return jsonify(data)


@aop_app.route("/js/aop_app/populate_qsprpred.js")
def serve_populate_qsprpred_js():
    try:
        return send_file("js/aop_app/populate_qsprpred.js")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@aop_app.route("/js/aop_app/populate_aop_network.js")
def serve_populate_aop_network_js():
    try:
        return send_file("js/aop_app/populate_aop_network.js")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@aop_app.route("/js/aop_app/predict_qspr.js")
def serve_predict_qspr_js():
    try:
        return send_file("js/aop_app/predict_qspr.js")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@aop_app.route("/get_compounds/<qid>", methods=["GET"])
def get_compounds_by_qid(qid):
    if not is_valid_qid(qid):
        return jsonify({"error": "Invalid identifier format"}), 400
    return get_compounds_q(qid)


def load_case_mie_model(mie_query):
    try:
        df = pd.read_csv(
            os.path.join(os.path.dirname(__file__), "../static/data/caseMieModel.csv"),
            dtype=str,
        )
    except Exception as e:
        raise Exception("CSV load error: " + str(e))
    mie_ids = []
    for mie in mie_query.split():
        if "aop.events:" in mie:
            parts = mie.split("aop.events:")
            if len(parts) > 1 and parts[1]:
                mie_ids.append(parts[1])
    df["MIE/KE identifier in AOP wiki"] = df["MIE/KE identifier in AOP wiki"].astype(
        str
    )
    filtered_df = df[df["MIE/KE identifier in AOP wiki"].isin(mie_ids)]
    return filtered_df


@aop_app.route("/get_case_mie_model", methods=["GET"])
def get_case_mie_model():
    mie_query = request.args.get("mie_query", "")
    if not mie_query:
        return jsonify({"error": "mie_query parameter is required"}), 400
    try:
        filtered_df = load_case_mie_model(mie_query)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    model_to_mie = filtered_df.set_index("qsprpred_model")[
        "MIE/KE identifier in AOP wiki"
    ].to_dict()
    return jsonify(model_to_mie), 200


@aop_app.route("/load_and_show_genes", methods=["GET"])
def load_and_show_genes():
    mies = request.args.get("mies", "")
    if not mies:
        return jsonify({"error": "mies parameter is required"}), 400
    mies_list = [quote(mie, safe="") for mie in mies.split(",")]
    mies_list = [unquote(mie) for mie in mies_list]
    gene_elements = []
    csv_path = os.path.join(
        os.path.dirname(__file__), "../static/data/caseMieModel.csv"
    )
    try:
        with open(csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                mie_id = "https://identifiers.org/aop.events/" + row.get(
                    "MIE/KE identifier in AOP wiki", ""
                )
                uniprot_id = row.get("uniprot ID inferred from qspred name", "")
                ensembl_id = row.get("Ensembl", "")
                if mie_id and uniprot_id and ensembl_id and mie_id in mies_list:
                    uniprot_node_id = f"uniprot_{uniprot_id}"
                    ensembl_node_id = f"ensembl_{ensembl_id}"
                    gene_elements.append(
                        {
                            "data": {
                                "id": uniprot_node_id,
                                "label": uniprot_id,
                                "type": "uniprot",
                            },
                            "classes": "uniprot-node",
                        }
                    )
                    gene_elements.append(
                        {
                            "data": {
                                "id": ensembl_node_id,
                                "label": ensembl_id,
                                "type": "ensembl",
                            },
                            "classes": "ensembl-node",
                        }
                    )
                    gene_elements.append(
                        {
                            "data": {
                                "id": f"edge_{mie_id}_{uniprot_node_id}",
                                "source": uniprot_node_id,
                                "target": mie_id,
                                "label": "part of",
                            }
                        }
                    )
                    gene_elements.append(
                        {
                            "data": {
                                "id": f"edge_{uniprot_node_id}_{ensembl_node_id}",
                                "source": uniprot_node_id,
                                "target": ensembl_node_id,
                                "label": "translates to",
                            }
                        }
                    )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(gene_elements)


@aop_app.route("/add_qsprpred_compounds", methods=["POST"])
def add_qsprpred_compounds():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON input"}), 400
    compound_mapping = data.get("compound_mapping", {})
    model_to_protein_info = data.get("model_to_protein_info", {})
    model_to_mie = data.get("model_to_mie", {})
    response_data = data.get("response", [])
    cy_elements = data.get("cy_elements", [])
    if isinstance(response_data, list):
        grouped = {}
        for pred in response_data:
            smiles = pred.get("smiles")
            if not smiles:
                continue
            if smiles not in grouped:
                grouped[smiles] = []
            grouped[smiles].append(pred)
        for smiles, predictions in grouped.items():
            compound = compound_mapping.get(smiles)
            compound_id = (
                compound.get("term") if compound and "term" in compound else smiles
            )
            for prediction in predictions:
                for model, value in prediction.items():
                    if model != "smiles":
                        try:
                            if float(value) >= 6.5:
                                protein_info = model_to_protein_info.get(
                                    model,
                                    {"proteinName": "Unknown Protein", "uniprotId": ""},
                                )
                                target_node_id = f"https://identifiers.org/aop.events/{model_to_mie.get(model, '')}"
                                cy_elements.append(
                                    {
                                        "data": {
                                            "id": compound_id,
                                            "label": compound_id,
                                            "type": "chemical",
                                            "smiles": smiles,
                                        },
                                        "classes": "chemical-node",
                                    }
                                )
                                cy_elements.append(
                                    {
                                        "data": {
                                            "id": f"{compound_id}-{target_node_id}-{model}",
                                            "source": compound_id,
                                            "target": f"uniprot_{protein_info.get('uniprotId', '')}",
                                            "value": value,
                                            "type": "interaction",
                                            "label": f"pChEMBL: {value} ({model})",
                                        }
                                    }
                                )
                        except Exception:
                            continue
    return jsonify(cy_elements), 200


@aop_app.route("/add_aop_bounding_box", methods=["POST"])
def add_aop_bounding_box():
    data = request.json
    aop = request.args.get('aop', '')
    cy_elements = data.get("cy_elements", [])
    bounding_boxes = []
    if not aop:
        return jsonify({"error": "AOP parameter is required"}), 400

    seen = set()
    for node in cy_elements:
        node_aop = node['data'].get('aop', [])
        aop_titles = node['data'].get('aop_title', [])
        if not isinstance(node_aop, list):
            node_aop = [node_aop]
        for aop_item, aop_title in zip(node_aop, aop_titles):
            if aop_item not in seen:
                bounding_boxes.append({
                    "group": "nodes",
                    "data": {
                        "id": f"bounding-box-{aop_item}",
                        "label": f"{aop_title} (aop:{aop_item.replace('https://identifiers.org/aop/', '')})"},
                    "classes": "bounding-box"
                })
                seen.add(aop_item)

    for node in cy_elements:
        node_aop = node['data'].get('aop', [])
        if not isinstance(node_aop, list):
            node_aop = [node_aop]
        for aop_item in node_aop:
            node['data']['parent'] = f"bounding-box-{aop_item}"
    return jsonify(cy_elements + bounding_boxes), 200
