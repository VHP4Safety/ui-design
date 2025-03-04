from flask import Blueprint, request, jsonify, send_file
import requests
from wikidataintegrator import wdi_core
import json
import re

aop_app = Blueprint('aop_app', __name__)

@aop_app.route('/get_dummy_data', methods=['GET'])
def get_dummy_data():
    results = [
    {
        "Compound": "Compound1" ,
        "SMILES": "Smile 1" 
    },
    {
        "Compound": "Compound1" ,
        "SMILES": "Smile 1" 
    },
    {
        "Compound": "Compound1" ,
        "SMILES": "Smile 1" 
    }
    ]
    return results, 200

def get_compounds_q(q):
    # Setting up the url for sparql endpoint.
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"

    # Setting up the sparql query for the full list of compounds.
    sparqlquery_full = f"""
    PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>
    PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>

    SELECT DISTINCT (substr(str(?cmp), 45) as ?ID) (?cmpLabel AS ?Term)
        ?SMILES (?cmp AS ?ref)
    WHERE {{
        {{ ?parent wdt:P21 wd:{q} ; wdt:P29 ?cmp . }} UNION {{ ?cmp wdt:P21 wd:{q} . }}
    ?cmp wdt:P1 ?type ; rdfs:label ?cmpLabel . FILTER(lang(?cmpLabel) = 'en')
    ?type rdfs:label ?typeLabel . FILTER(lang(?typeLabel) = 'en')
    OPTIONAL {{ ?cmp wdt:P7 ?chiralSMILES }}
    OPTIONAL {{ ?cmp wdt:P12 ?nonchiralSMILES }}
    BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0), IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0),"") AS ?SMILES)
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    """

     # Making the SPARQL query
    compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(sparqlquery_full, endpoint=compoundwikiEP, as_dataframe=True)

    # Organizing the output into a list of dictionaries
    compound_list = []
    for _, row in compound_dat.iterrows():
        compound_list.append({"ID": row[1], "Term": row[2], "SMILES": row[0]})

    return jsonify(compound_list), 200

@aop_app.route('/get_compounds', methods=['GET'])
def get_compounds_VHP():
    return get_compounds_q("Q2059")

@aop_app.route('/get_compound_identifiers/<cwid>')
def show_compounds_identifiers_as_json(cwid):
    # Setting up the url for sparql endpoint.
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"

    sparqlquery = '''
      PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>
      PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>
      
SELECT ?propertyLabel ?value
WHERE {
  VALUES ?property { wd:P3 wd:P2 wd:P32 }
  ?property wikibase:directClaim ?valueProp .
  OPTIONAL { wd:''' + cwid + ''' ?valueProp ?value }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}
      '''
    print(sparqlquery + "\n")

    compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(sparqlquery, endpoint=compoundwikiEP, as_dataframe=True)

    compound_list = []
    for _, row in compound_dat.iterrows():
      compound_list.append({
        "propertyLabel": row["propertyLabel"],
        "value": str(row["value"])
      })

    return jsonify(compound_list), 200

@aop_app.route('/get_compound_expdata/<cwid>')
def show_compounds_expdata_as_json(cwid):
    # Setting up the url for sparql endpoint.
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"

    sparqlquery = '''
PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>
PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>
PREFIX wid: <http://www.wikidata.org/entity/>
PREFIX widt: <http://www.wikidata.org/prop/direct/>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?propEntityLabel ?value ?unitsLabel ?source ?doi
WHERE {
  wd:P5 wikibase:directClaim ?identifierProp .
  wd:''' + cwid + ''' ?identifierProp ?wikidata .
  BIND (iri(CONCAT("http://www.wikidata.org/entity/", ?wikidata)) AS ?qid)
  SERVICE <https://query.wikidata.org/sparql> {
    ?qid ?propp ?statement .
    ?statement a wikibase:BestRank ;
      ?proppsv [
        wikibase:quantityAmount ?value ;
        wikibase:quantityUnit ?units
      ] .
    OPTIONAL {
      ?statement prov:wasDerivedFrom/pr:P248 ?source .
      OPTIONAL { ?source wdt:P356 ?doi . }
    }
    ?property wikibase:claim ?propp ;
            wikibase:statementValue ?proppsv ;
            widt:P1629 ?propEntity ;
            widt:P31 wid:Q21077852 .
    ?propEntity rdfs:label ?propEntityLabel .
    FILTER ( lang(?propEntityLabel) = 'en' )
    ?units rdfs:label ?unitsLabel .
    FILTER ( lang(?unitsLabel) = 'en' )
    BIND (COALESCE(IF(BOUND(?source), ?source, 1/0), "") AS ?source)
    BIND (COALESCE(IF(BOUND(?doi), ?doi, 1/0), "") AS ?doi)
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}      '''
    print(sparqlquery + "\n")

    compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(sparqlquery, endpoint=compoundwikiEP, as_dataframe=True)

    compound_list = []
    for _, row in compound_dat.iterrows():
      compound_list.append({
        "propEntityLabel": row["propEntityLabel"],
        "value": row["value"],
        "unitsLabel": row["unitsLabel"],
        "source": row["source"],
        "doi": row["doi"]
      })

    return jsonify(compound_list), 200

@aop_app.route('/get_compound_properties/<cwid>')
def show_compounds_properties_as_json(cwid):
    # Setting up the url for sparql endpoint.
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"

    sparqlquery = '''
      PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>
      PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>
      
      SELECT ?cmp ?cmpLabel ?inchiKey ?SMILES WHERE {
        VALUES ?cmp { wd:''' + cwid + ''' }
        ?cmp wdt:P10 ?inchiKey .
        OPTIONAL { ?cmp wdt:P7 ?chiralSMILES }
        OPTIONAL { ?cmp wdt:P12 ?nonchiralSMILES }
        BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0), IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0),"") AS ?SMILES)
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
      }
      '''
    print(sparqlquery + "\n")

    compound_dat = wdi_core.WDFunctionsEngine.execute_sparql_query(sparqlquery, endpoint=compoundwikiEP, as_dataframe=True)

    compound_list = []
    compound_list.append({
      "wcid": compound_dat.at[0, "cmp"],
      "label": compound_dat.at[0, "cmpLabel"],
      "inchikey": compound_dat.at[0, "inchiKey"],
      "SMILES": compound_dat.at[0, "SMILES"]
    })

    return jsonify(compound_list), 200

@aop_app.route('/get_compounds_parkinson', methods=['GET'])
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
    body = {
        "smiles": smiles,
        "models": models,
        "format": "json"
    }
    response = requests.post(url, headers=headers, data=json.dumps(body))
    if response.status_code == 200:
        predictions = response.json()
        filtered_predictions = []
        for prediction in predictions:
            filtered_prediction = {"smiles": prediction["smiles"]}
            for key, value in prediction.items():
                if key != "smiles" and float(value) >= threshold:
                    new_key = re.sub(r'prediction \((.+)\)', r'\1', key)
                    filtered_prediction[new_key] = value
            filtered_predictions.append(filtered_prediction)
            # Ensure metadata exists for the model before updating
            if models and models[0] in metadata:
                filtered_prediction.update(metadata.get(models[0], {}))
        print(f"{len(filtered_predictions)} result(s)")
        return filtered_predictions
    else:
        return {"error": response.text}
    
@aop_app.route("/get_predictions", methods=["POST"])
def get_predictions():
    data = request.json
    smiles = data.get("smiles", [])
    models = data.get("models", [])
    metadata = data.get("metadata", {})
    threshold = data.get("threshold", 6.5)

    results = fetch_predictions(smiles, models, metadata, threshold)
    return jsonify(results)


AOPWIKISPARQL_ENDPOINT = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/"

AOPWIKIPARKINSONSPARQL_QUERY = """
SELECT DISTINCT ?aop ?aop_title ?MIEtitle ?MIE ?KE_downstream ?KE_downstream_title  
       ?KER ?ao ?AOtitle ?KE_upstream ?KE_upstream_title
WHERE {
  VALUES ?MIE { aop.events:388 aop.events:2039 aop.events:2036  }
    ?aop a aopo:AdverseOutcomePathway ;
         dc:title ?aop_title ;
         aopo:has_adverse_outcome ?ao ;
         aopo:has_molecular_initiating_event ?MIE .
    
    ?MIE dc:title ?MIEtitle .

      ?aop aopo:has_key_event_relationship ?KER .
      ?KER a aopo:KeyEventRelationship ;
           aopo:has_upstream_key_event ?KE_upstream ;
           aopo:has_downstream_key_event ?KE_downstream .
      
      ?KE_upstream dc:title ?KE_upstream_title .
      ?KE_downstream dc:title ?KE_downstream_title .
    
    OPTIONAL {
      ?ao rdfs:label ?AOtitle .
    }
}
"""

def extract_ker_id(ker_uri):
    """Extract only the numeric ID from the KER URI (after the last '/')"""
    return ker_uri.split("/")[-1] if ker_uri else "Unknown"

def fetch_sparql_data():
    """Fetch data from the SPARQL endpoint and format it for Cytoscape.js."""
    response = requests.get(AOPWIKISPARQL_ENDPOINT, params={"query": AOPWIKIPARKINSONSPARQL_QUERY, "format": "json"})
    if response.status_code != 200:
        return {"error": "Failed to fetch SPARQL data"}

    data = response.json()
    cytoscape_elements = []
    node_dict = {}  # Store nodes to avoid duplicates and overwriting MIE/AO attributes

    for result in data["results"]["bindings"]:
        # Extract key event data
        ke_upstream = result["KE_upstream"]["value"]
        ke_upstream_title = result["KE_upstream_title"]["value"]
        ke_downstream = result["KE_downstream"]["value"]
        ke_downstream_title = result["KE_downstream_title"]["value"]
        mie = result["MIE"]["value"]  # Molecular Initiating Event (MIE)
        ao = result["ao"]["value"] if "ao" in result else None  # Adverse Outcome (AO)
        ker_uri = result["KER"]["value"]  # Extract KER URI
        ker_id = extract_ker_id(ker_uri)  # Extract only the numeric part
        
        # Add or update the KE Upstream node
        if ke_upstream not in node_dict:
            node_dict[ke_upstream] = {
                "data": {
                    "id": ke_upstream,
                    "label": ke_upstream_title,
                    "KEupTitle": ke_upstream_title,
                    "is_mie": ke_upstream == mie  # Only set True if it matches MIE,
                }
            }
            if ke_upstream == mie:
                node_dict[ke_upstream]["data"]["in_brain"] = True
        else:
            if ke_upstream == mie:
                node_dict[ke_upstream]["data"]["is_mie"] = True

        # Add or update the KE Downstream node
        if ke_downstream not in node_dict:
            node_dict[ke_downstream] = {
                "data": {
                    "id": ke_downstream,
                    "label": ke_downstream_title,
                    "is_ao": ke_downstream == ao  # Only set True if it matches AO
                }
            }
        else:
            if ke_downstream == ao:
                node_dict[ke_downstream]["data"]["is_ao"] = True

        # Add edge with extracted KER ID
        edge_id = f"{ke_upstream}_{ke_downstream}"
        cytoscape_elements.append({
            "data": {
                "id": edge_id,
                "source": ke_upstream,
                "target": ke_downstream,
                "ker_label": ker_id  # Store KER ID for Cytoscape.js labeling
            }
        })

    # Convert node_dict values to a list and merge with edges
    return list(node_dict.values()) + cytoscape_elements


@aop_app.route("/get_aop_network")
def get_aop_network():
    """API route to return the AOP network."""
    data = fetch_sparql_data()
    return jsonify(data)

@aop_app.route('/js/aop_app/populate_compound_container.js')
def serve_populate_compound_container_js():
    return send_file('js/aop_app/populate_compound_container.js')

@aop_app.route('/js/aop_app/populate_aop_network.js')
def serve_populate_aop_network_js():
    return send_file('js/aop_app/populate_aop_network.js')

@aop_app.route('/js/aop_app/predict_qspr.js')
def serve_predict_qspr_js():
    return send_file('js/aop_app/predict_qspr.js')

@aop_app.route('/get_compounds/<qid>', methods=['GET'])
def get_compounds_by_qid(qid):
    return get_compounds_q(qid)
