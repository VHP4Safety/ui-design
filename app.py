################################################################################
### Loading the required modules
import json
import re

import requests
import urllib.parse
from flask import Blueprint, Flask, abort, jsonify, render_template, request, send_file
from jinja2 import TemplateNotFound
from werkzeug.routing import BaseConverter

# from wikidataintegrator import wdi_core
from wikibaseintegrator import wbi_helpers

# Import BioStudies extractor
from biostudies.search import BioStudiesExtractor

################################################################################
### Configuration for BioStudies Integration
# Change these variables to switch between collections
BIOSTUDIES_COLLECTION = "VHP4Safety"  # Replace with "EU-ToxRisk" to test
BIOSTUDIES_COLLECTION_NAME = "VHP4Safety"  # Display name for the page
CASESTUDIES = ["thyroid", "kidney", "parkinson"]  # List of valid case studies

###Shared explanation dictionaries for filters (used in both tools and data page)
STAGE_EXPLANATIONS = {
    "ADME": "Absorption, distribution, metabolism, and excretion of a substance (toxic or not) in a living organism, following exposure to this substance.",
    "Hazard Assessment": "The process of assessing the intrinsic hazard a substance poses to human health and/or the environment",
    "Chemical Information": "Information about chemical properties and identity.",
    "General": "Not specific to a flow step.",
    "(External) exposure": "External exposure assessment.",
    "Generic": "Generic category.",
    "Other": "Other or unknown category.",
}

REG_QUESTIONS = {
    "reg_q_1a": {
        "label": "Kidney Case Study (a)",
        "explanation": "What is the safe cisplatin dose in cancer patients?",
    },
    "reg_q_1b": {
        "label": "Kidney Case Study (b)",
        "explanation": "What is the intrinsic hazard of tacrolimus for nephrotoxicity?",
    },
    "reg_q_2a": {
        "label": "Parkinson Case Study (a)",
        "explanation": "Can compound Dinoseb cause Parkinson's Disease?",
    },
    "reg_q_2b": {
        "label": "Parkinson Case Study (b)",
        "explanation": "What level of exposure to compound Dinoseb leads to risk for developing Parkinson’s disease?",
    },
    "reg_q_3a": {
        "label": "Thyroid Case Study (a)",
        "explanation": "What information about silychristin do we need to give an advice to women in their early pregnancy to decide whether the substance can be used?",
    },
    "reg_q_3b": {
        "label": "Thyroid Case Study (b)",
        "explanation": "Does silychristin influence the thyroid-mediated brain development in the fetus resulting in cognitive impairment in children?",
    },
}

# Derived: keep the old structure available for templates expecting {label: explanation}
REG_QUESTION_EXPLANATIONS = {v["label"]: v["explanation"] for v in REG_QUESTIONS.values()}


################################################################################
class RegexConverter(BaseConverter):
    """Converter for regular expression routes.

    References
    ----------
    Scholia views.py
    https://stackoverflow.com/questions/5870188

    """

    def __init__(self, url_map, *items):
        """Set up regular expression matcher."""
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


app = Flask(__name__)


################################################################################
### The landing page
@app.route("/")
def home():
    # get number of tools:
    url = "https://raw.githubusercontent.com/VHP4Safety/cloud/refs/heads/main/cap/service_index.json"
    response = requests.get(url)

    if response.status_code != 200:
        return f"Error fetching service list: {response.status_code}", 503

    try:
        tools = (
            response.json()
        )  # Geting the service_list.json in the dictionary format.
        tools = list(tools.values())  # Converting the dictionary to a list object.
    except Exception as e:
        return f"Error processing service data: {e}", 500
    num_tools = len(tools)
    num_case_studies = len(CASESTUDIES)
    num_datasets = BioStudiesExtractor(collection=BIOSTUDIES_COLLECTION).list_studies(
        page=1, page_size=1
    )["total"]
    return render_template(
        "home.html",
        num_tools=num_tools,
        num_case_studies=num_case_studies,
        num_datasets=num_datasets,
    )


################################################################################
### Pages under 'Data'
@app.route("/data")
def data():
    # Get query parameters for pagination and search
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 18, type=int)
    search_query = request.args.get("query", "", type=str)

    # Get filter parameters
    filter_case_study = request.args.get("filter_case_study", "", type=str)
    filter_regulatory_question = request.args.get(
        "filter_regulatory_question", "", type=str
    )
    filter_flow_step = request.args.get("filter_flow_step", "", type=str)

    # Build filter list (only include non-empty filters)
    filters = []
    if filter_case_study:
        filters.append(("case_study", filter_case_study))
    if filter_regulatory_question:
        filters.append(("regulatory_question", filter_regulatory_question))
    if filter_flow_step:
        filters.append(("flow_step", filter_flow_step))

    # Initialize extractor
    extractor = BioStudiesExtractor(collection=BIOSTUDIES_COLLECTION)

    # Fetch data based on search query or list all
    if search_query:
        results = extractor.search_studies(
            search_query, page=page, page_size=page_size, filter=filters
        )
    else:
        results = extractor.list_studies(
            page=page, page_size=page_size, include_urls=True, filter=filters
        )

    # Extract studies and metadata
    studies = results.get("hits", [])
    total = results.get("total", 0)
    error = results.get("error", None)

    # Get filtering metadata (if filters were applied)
    filters_applied = results.get("filters_applied", False)
    hits_returned = results.get("hits_returned", len(studies))
    pages_fetched = results.get("pages_fetched", 1)
    page_size_met = results.get("page_size_met", True)

    # Calculate pagination info
    has_next = (page * page_size) < total
    has_prev = page > 1

    # Pass data to template
    return render_template(
        "data/data.html",
        studies=studies,
        total=total,
        page=page,
        page_size=page_size,
        search_query=search_query,
        collection_name=BIOSTUDIES_COLLECTION_NAME,
        collection=BIOSTUDIES_COLLECTION,
        error=error,
        has_next=has_next,
        has_prev=has_prev,
        filter_case_study=filter_case_study,
        filter_regulatory_question=filter_regulatory_question,
        filter_flow_step=filter_flow_step,
        filters_applied=filters_applied,
        hits_returned=hits_returned,
        pages_fetched=pages_fetched,
        page_size_met=page_size_met,
        stage_explanations=STAGE_EXPLANATIONS,
        reg_question_explanations=REG_QUESTION_EXPLANATIONS,
    )


################################################################################
### Pages under 'Tools'

# Page to list all the tools based on the list of tools on the cloud repo.

# Below is the original way of creating the service_list page which runs slow.
# Further down below it, I try to implement a way to get the combined json file
# rather than getting individual service information one-by-one.
""" 
@app.route("/tools")
def tools():
    # Github API link to receive the list of the tools on the cloud repo:
    url = f"https://api.github.com/repos/VHP4Safety/cloud/contents/docs/service"
    response = requests.get(url)

    # Checking if the request was successful (status code 200).
    if response.status_code == 200:
        # Extracting the list of files.
        tools_content = response.json()

        # Separating .json and .md files.
        json_files = {
            file["name"]: file
            for file in tools_content
            if file["type"] == "file" and file["name"].endswith(".json")
        }
        md_files = {
            file["name"]: file
            for file in tools_content
            if file["type"] == "file" and file["name"].endswith(".md")
        }
        png_files = {
            file["name"]: file
            for file in tools_content
            if file["type"] == "file" and file["name"].endswith(".png")
        }

        # Creating an empty list to store the results.
        tools = []

        # Fetching the .json files.
        for json_file_name, json_file in json_files.items():
            # Skipping the template.json file.
            if json_file_name == "template.json":
                continue

            json_url = json_file[
                "download_url"
            ]  # Using the download URL from the API response.
            json_response = requests.get(json_url)

            if json_response.status_code == 200:
                json_data = json_response.json()

                # Extracting the 'tool' field from the json file.
                tool_name = json_data.get("service")
                description_string = json_data.get("description")

                if tool_name:
                    # Replacing the .json extension with the .md to get the corresponding .md file.
                    md_file_name = json_file_name.replace(".json", ".md")
                    html_name = json_file_name.replace(".json", ".html")
                    url = "https://cloud.vhp4safety.nl/service/" + html_name

                    if md_file_name in md_files:
                        md_file_url = f"https://raw.githubusercontent.com/VHP4Safety/cloud/main/docs/service/{md_file_name}"
                    else:
                        md_file_url = "md file not found"
                    png_file_name = md_file_name.replace(".md", ".png")

                    if png_file_name in png_files:
                        png_file_url = f"https://raw.githubusercontent.com/VHP4Safety/cloud/main/docs/service/{png_file_name}"
                        tools.append(
                            {
                                "service": tool_name,
                                "url": url,
                                "meta_data": md_file_url,
                                "description": description_string,
                                "png": png_file_url,
                            }
                        )
                    else:
                        tools.append(
                            {
                                "service": tool_name,
                                "url": url,
                                "meta_data": md_file_url,
                                "description": description_string,
                                "png": "../../static/images/logo.png",
                            }
                        )

        # Passing the tools data to the template after processing all JSON files.
        return render_template("tools/tools.html", tools=tools)
    else:
        return f"Error fetching files: {response.status_code}"
"""


### Here begins the updated version for creating the tool list page.
@app.route("/tools")
def tools():
    url = "https://raw.githubusercontent.com/VHP4Safety/cloud/refs/heads/main/cap/service_index.json"
    response = requests.get(url)

    if response.status_code != 200:
        return f"Error fetching service list: {response.status_code}", 503

    try:
        tools = (
            response.json()
        )  # Geting the service_list.json in the dictionary format.
        tools = list(tools.values())  # Converting the dictionary to a list object.

        # Mapping the URLs with glossary IDs to their text values.
        stage_mapping = {
            "https://vhp4safety.github.io/glossary#VHP0000056": "ADME",
            "https://vhp4safety.github.io/glossary#VHP0000102": "Hazard Assessment",
            "https://vhp4safety.github.io/glossary#VHP0000148": "Chemical Information",
            "https://vhp4safety.github.io/glossary#VHP0000149": "General",
        }

        for tool in tools:
            full_stage_url = tool.get("stage", "")

            # Writing the service name and stage values in the logs for troubleshooting.
            # print(f"Tool: {tool['service']}, Stage URL: {full_stage_url}")  # Log the full URL

            # Checking if the full URL is in the mapping and updating the stage.
            if full_stage_url in stage_mapping:
                # print(f"Mapping stage URL {full_stage_url} to {stage_mapping[full_stage_url]}")  # Log the mapping
                tool["stage"] = stage_mapping[full_stage_url]
            elif tool["stage"] in ["NA", "Unknown"]:
                tool["stage"] = (
                    "Other"  # Combining "NA" and "Unknown" stages in a single stage-type, "Other".
                )

            html_name = tool.get("html_name")
            md_name = tool.get("md_file_name")
            png_name = tool.get("png_file_name")

            tool["url"] = f"https://cloud.vhp4safety.nl/service/{html_name}"
            tool["meta_data"] = (
                f"https://raw.githubusercontent.com/VHP4Safety/cloud/main/docs/service/{md_name}"
                if md_name
                else "md file not found"
            )

            # Check if the tool has the placeholder logo
            placeholder_logo = "https://github.com/VHP4Safety/ui-design/blob/main/static/images/logo.png"
            if png_name == placeholder_logo:
                tool["png"] = None  # set to None if it's the common placeholder
            else:
                tool["png"] = (
                    f"https://raw.githubusercontent.com/VHP4Safety/cloud/main/docs/service/{png_name}"
                    if not png_name.startswith("http")
                    else png_name
                )

            inst_url = tool.get("inst_url", "no_url")
            if not inst_url:  # catches "" as well
                inst_url = "no_url"
            tool["inst_url"] = inst_url

        # Getting selected stages from the URL.
        selected_stages = request.args.getlist("stage")

        # Filtering tools by selected stages.
        if selected_stages:
            tools = [tool for tool in tools if tool.get("stage") in selected_stages]

        # Getting all unique stages from the tools for the filter options.
        stages = sorted(set(tool.get("stage") for tool in tools if tool.get("stage")))

        # Forcing "Other" to be the last item in the list of stages.
        if "Other" in stages:
            stages.remove("Other")
            stages.append("Other")

        # Filtering over the regulatory questions.
        reg_questions = { v["label"]: k for k, v in REG_QUESTIONS.items() }

        selected_questions = request.args.getlist("reg_q")

        for question in selected_questions:
            field = reg_questions.get(question)
            if field:
                tools = [
                    tool for tool in tools if str(tool.get(field, "")).lower() == "true"
                ]

        # Getting the search query from URL to add a search bar based on tool names.
        search_query = request.args.get("search", "").strip().lower()

        # Filtering tools by search query.
        if search_query:
            tools = [
                tool
                for tool in tools
                if search_query in tool.get("service", "").lower()
            ]

        return render_template(
            "tools/tools.html",
            tools=tools,
            stages=stages,
            selected_stages=selected_stages,
            reg_questions=reg_questions,
            selected_questions=selected_questions,
            stage_explanations=STAGE_EXPLANATIONS,
            reg_question_explanations=REG_QUESTION_EXPLANATIONS,
        )

    except Exception as e:
        return f"Error processing service data: {e}", 500


@app.route("/tools/<toolname>")
def tool_page(toolname):
    # get the tools metadata:
    url = "https://raw.githubusercontent.com/VHP4Safety/cloud/refs/heads/main/cap/service_index.json"
    response = requests.get(url)

    if response.status_code != 200:
        return f"Error fetching service list: {response.status_code}", 503

    try:
        tools = response.json()
        tools = dict(tools)
        # Geting the service_list.json in the dictionary format.
        # Converting the dictionary to a list object.
    except Exception as e:
        return f"Error processing service data: {e}", 500

    # Map toolname to the correct JSON file in the new tool folder
    if toolname not in tools:
        abort(404)

    # get the tools metadata:
    url = "https://cloud.vhp4safety.nl/service/" + toolname+ ".json"
    response = requests.get(url)

    if response.status_code != 200:
        return f"Error fetching service list: {response.status_code}", 503

    try:
        tool_details = response.json()
        tool_details = dict(tool_details)
        # Geting the service_list.json in the dictionary format.
        # Converting the dictionary to a list object.
    except Exception as e:
        return f"Error processing service data: {e}", 500

    # Pass the json filename to the template (for JS to pick up)
    return render_template("tools/tool.html", tool_json=tools[toolname], tool_details=tool_details)

################################################################################
### Pages under 'Process Flow'


# General Process Flow page
@app.route("/process_flow")
def workflows():
    return render_template("process_flow.html")


################################################################################
### Pages under 'Case Studies'


# General case studies page
@app.route("/casestudies")
def workflows():
    return render_template("case_studies/casestudies.html")


# Individual case study page, dynamically filled based on URL
@app.route("/casestudies/<case>")
def casestudy_main(case):
    # Only allow known case studies
    if case not in CASESTUDIES:
        abort(404)
    return render_template(f"case_studies/casestudy.html", case=case)


@app.route("/case_studies/parkinson/workflows/parkinson_qAOP")
def parkinson_qaop():
    return render_template("case_studies/parkinson/workflows/parkinson_qAOP.html")


@app.route("/case_studies/thyroid/workflows/thyroid_qAOP")
def thyroid_qaop():
    return render_template("case_studies/thyroid/workflows/thyroid_qAOP.html")


@app.route("/workflow/<workflow>")
def show(workflow):
    try:
        return render_template(
            f"case_studies/parkinson/workflows/{workflow}_workflow.html"
        )
    except TemplateNotFound:
        abort(404)


################################################################################
### Pages related to chemical compounds


def is_valid_qid(qid):
    return re.fullmatch(r"Q\d+", qid) is not None


@app.route("/compound/<cwid>")
def show_compound(cwid):
    try:
        return render_template(f"compound.html", cwid=cwid)
    except TemplateNotFound:
        abort(404)


@app.route("/get_compound_properties/<cwid>")
def show_compounds_properties_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT ?cmp ?cmpLabel ?formula ?mass ?inchi ?inchiKey ?SMILES WHERE {\n"
        "  VALUES ?cmp { wd:" + cwid + " }\n"
        "  ?cmp wdt:P9 ?inchi ;\n"
        "       wdt:P10 ?inchiKey .\n"
        "  OPTIONAL { ?cmp wdt:P2 ?mass }\n"
        "  OPTIONAL { ?cmp wdt:P3 ?formula }\n"
        "  OPTIONAL { ?cmp wdt:P7 ?chiralSMILES }\n"
        "  OPTIONAL { ?cmp wdt:P12 ?nonchiralSMILES }\n"
        '  BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0), IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0), "") AS ?SMILES)\n'
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wbi_helpers.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not bool(compound_dat):
        return jsonify({"error": "No data found"}), 404
    compound_dat = compound_dat["results"]["bindings"][0]
    # return jsonify(compound_dat);
    compound_list = [
        {
            "wcid": compound_dat["cmp"]["value"],
            "label": compound_dat["cmpLabel"]["value"],
            "inchi": compound_dat["inchi"]["value"],
            "inchikey": compound_dat["inchiKey"]["value"],
            "SMILES": compound_dat["SMILES"]["value"],
            "formula": compound_dat["formula"]["value"],
            "mass": compound_dat["mass"]["value"],
        }
    ]
    return jsonify(compound_list), 200


@app.route("/get_compound_identifiers/<cwid>")
def show_compounds_identifiers_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT DISTINCT ?propertyLabel ?value ?formatterURL\n"
        "WHERE {\n"
        "  VALUES ?property { wd:P13 wd:P22 wd:P23 wd:P26 wd:P27 wd:P28 wd:P36 wd:P41 wd:P43 wd:P44 wd:P45 }\n"
        "  ?property wikibase:directClaim ?valueProp .\n"
        "  OPTIONAL { wd:" + cwid + " ?valueProp ?value }\n"
        "  OPTIONAL { ?property wdt:P6 ?formatterURL }\n"
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wbi_helpers.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if len(compound_dat["results"]["bindings"]) == 0:
        return jsonify({"error": "No data found"}), 404
    compound_dat = compound_dat["results"]["bindings"]
    # return jsonify(compound_dat)

    compound_list = []
    for expProp in compound_dat:
        if "value" in expProp:
            compound_list.append(
                {
                    "propertyLabel": expProp["propertyLabel"]["value"],
                    "value": expProp["value"]["value"],
                    "formatterURL": expProp["formatterURL"]["value"],
                }
            )
        else:
            compound_list.append(
                {"propertyLabel": expProp["propertyLabel"]["value"], "value": "", "formatterURL": ""}
            )
    return jsonify(compound_list), 200


@app.route("/get_compound_toxicology/<cwid>")
def show_compounds_toxicology_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT DISTINCT ?propertyLabel ?value ?formatterURL\n"
        "WHERE {\n"
        "  VALUES ?property { wd:P17 wd:P19 wd:P4 }\n"
        "  ?property wikibase:directClaim ?valueProp .\n"
        "  OPTIONAL { wd:" + cwid + " ?valueProp ?value }\n"
        "  OPTIONAL { ?property wdt:P6 ?formatterURL }\n"
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wbi_helpers.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if len(compound_dat["results"]["bindings"]) == 0:
        return jsonify({"error": "No data found"}), 404
    compound_dat = compound_dat["results"]["bindings"]
    # return jsonify(compound_dat)

    compound_list = []
    for expProp in compound_dat:
        print(expProp)
        if "value" in expProp:
            compound_list.append(
                {
                    "propertyLabel": expProp["propertyLabel"]["value"],
                    "value": expProp["value"]["value"]
                }
            )
        else:
            compound_list.append(
                {"propertyLabel": expProp["propertyLabel"]["value"], "value": ""}
            )
    return jsonify(compound_list), 200


@app.route("/get_compound_expdata/<cwid>")
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
        "SELECT ?qid WHERE {\n"
        "  wd:P5 wikibase:directClaim ?identifierProp .\n"
        "  wd:" + cwid + " ?identifierProp ?wikidata .\n"
        '  BIND (iri(CONCAT("http://www.wikidata.org/entity/", ?wikidata)) AS ?qid)\n'
        "}"
    )
    try:
        compound_dat = wbi_helpers.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not bool(compound_dat):
        return jsonify({"error": "No data found"}), 404
    if len(compound_dat["results"]["bindings"]) == 0:
        return jsonify({"error": "No data found"}), 404
    compound_dat = compound_dat["results"]["bindings"][0]
    qid = compound_dat["qid"]["value"]
    # the next query may be affected by https://github.com/ad-freiburg/qlever-control/issues/187
    sparqlquery = (
        "PREFIX wd: <http://www.wikidata.org/entity/>\n"
        "PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        "PREFIX pr: <http://www.wikidata.org/prop/reference/>\n"
        "PREFIX wikibase: <http://wikiba.se/ontology#>\n\n"
        "SELECT DISTINCT ?propEntityLabel ?value ?unitsLabel ?source ?doi ?statement\n"
        "WHERE {\n"
        "    <" + qid + "> ?propp ?statement .\n"
        "    ?statement a wikibase:BestRank ;\n"
        "      ?proppsv [ wikibase:quantityAmount ?value ; wikibase:quantityUnit ?units ] .\n"
        "    #OPTIONAL { ?statement prov:wasDerivedFrom/pr:P248 ?sourceTmp . OPTIONAL { ?sourceTmp wdt:P356 ?doiTmp . } }\n"
        "    ?property wikibase:claim ?propp ; wikibase:statementValue ?proppsv ; wdt:P1629 ?propEntity ; wdt:P31 wd:Q21077852 .\n"
        "    ?propEntity @en@rdfs:label ?propEntityLabel .\n"
        "    ?units @en@rdfs:label ?unitsLabel .\n"
        '    BIND (COALESCE(IF(BOUND(?sourceTmp), ?sourceTmp, 1/0), "") AS ?source)\n'
        '    BIND (COALESCE(IF(BOUND(?doiTmp), ?doiTmp, 1/0), "") AS ?doi)\n'
        "}"
    )
    # return sparqlquery
    try:
        sparqlqueryURL = (
            "https://qlever.cs.uni-freiburg.de/api/wikidata?format=json&query="
            + urllib.parse.quote_plus(sparqlquery)
        )
        # return sparqlqueryURL
        compound_dat = requests.get(sparqlqueryURL)
        # return json.loads(compound_dat.content)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not bool(compound_dat):
        return jsonify({"error": "No data found"}), 404
    compound_dat = json.loads(compound_dat.content)["results"]["bindings"]
    # return jsonify(compound_dat)
    compound_list = []
    for expProp in compound_dat:
        # return jsonify(expProp)
        compound_list.append(
            {
                "propEntityLabel": expProp["propEntityLabel"]["value"],
                "value": expProp["value"]["value"],
                "unitsLabel": expProp["unitsLabel"]["value"],
                "source": expProp["source"]["value"],
                "doi": expProp["doi"]["value"],
                "seeAlso": expProp["statement"]["value"],
            }
        )
    return jsonify(compound_list), 200


################################################################################
### Pages under 'Legal'
@app.route("/legal/terms_of_service")
def terms_of_service():
    return render_template("legal/terms_of_service.html")


@app.route("/legal/privacypolicy")
def privacy_policy():
    return render_template("legal/privacypolicy.html")


################################################################################

# Import the new blueprint
# from routes.aop_app import aop_app

# Register the blueprint
# app.register_blueprint(aop_app)

################################################################################

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
