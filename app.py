################################################################################
### Loading the required modules
import json
import re

import requests
from flask import Blueprint, Flask, abort, jsonify, render_template, request, send_file
from jinja2 import TemplateNotFound
from werkzeug.routing import BaseConverter
from wikidataintegrator import wdi_core

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
    return render_template("home.html")


################################################################################


################################################################################
### Main tabs
@app.route("/casestudies")
def workflows():
    return render_template("tabs/casestudies.html")


@app.route("/data")
def data():
    return render_template("tabs/data.html")


@app.route("/archive")
def archive():
    return render_template("tabs/archive.html")


################################################################################
### Pages under 'Project Information', these are now part of home.html

# @app.route('/information/mission_and_vision')
# def mission_and_vision():
#     # This section is now part of the landing page or home.html.
#     return render_template('information/mission_and_vision.html')

# @app.route('/information/research_lines')
# def research_lines():
#     # This section is now part of the landing page or home.html.
#     return render_template('information/research_lines.html')

# @app.route('/case_studies_and_regulatory_questions')
# def case_studies_and_regulatory_questions():
#     # This section is now part of the landing page or home.html.
#     return render_template('information/case_studies_and_regulatory_questions.html')

# @app.route('/information/partners_and_consortium')
# def partners_and_consortium():
#     # This section is now part of the landing page or home.html.
#     return render_template('information/partners_and_consortium.html')

# @app.route('/information/contact')
# def contact():
#     # This section is now part of the landing page or home.html.
#     return render_template('information/contact.html')

################################################################################

################################################################################
### Pages under 'Tools'


# Page to list all the tools based on the list of tools on the cloud repo.

# Below is the original way of creating the service_list page which runs slow.
# Further down below it, I try to implement a way to get the combined json file 
# rather than getting individual service information one-by-one. 
""" 
@app.route("/templates/tools/tools")
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
@app.route("/templates/tools/tools")
@app.route("/templates/tools/tools")
def tools():
    url = 'https://raw.githubusercontent.com/VHP4Safety/cloud/main/cap/service_index.json'
    response = requests.get(url)

    if response.status_code != 200:
        return f"Error fetching service list: {response.status_code}", 503

    try:
        tools = response.json()

        # Mapping the URLs with glossary IDs to their text values. 
        stage_mapping = {
            "https://vhp4safety.github.io/glossary#VHP0000056": "ADME",
            "https://vhp4safety.github.io/glossary#VHP0000102": "Hazard Assessment",
            "https://vhp4safety.github.io/glossary#VHP0000148": "Chemical Information",
            "https://vhp4safety.github.io/glossary#VHP0000149": "General"
        }

        for tool in tools:
            full_stage_url = tool.get('stage', '')

            # Writing the service name and stage values in the logs for troubleshooting.
            # print(f"Tool: {tool['service']}, Stage URL: {full_stage_url}")  # Log the full URL

            # Checking if the full URL is in the mapping and updating the stage.
            if full_stage_url in stage_mapping:
                # print(f"Mapping stage URL {full_stage_url} to {stage_mapping[full_stage_url]}")  # Log the mapping
                tool['stage'] = stage_mapping[full_stage_url]
            elif tool['stage'] in ['NA', 'Unknown']: 
                tool['stage'] = 'Other'  # Combining "NA" and "Unknown" stages in a single stage-type, "Other".
            
            html_name = tool.get('html_name')
            md_name = tool.get('md_file_name')
            png_name = tool.get('png_file_name')

            tool['url'] = f"https://cloud.vhp4safety.nl/service/{html_name}"
            tool['meta_data'] = f"https://raw.githubusercontent.com/VHP4Safety/cloud/main/docs/service/{md_name}" if md_name else "md file not found"
            
            if png_name == 'https://github.com/VHP4Safety/ui-design/blob/main/static/images/logo.png':
                tool['png'] = 'https://raw.githubusercontent.com/VHP4Safety/ui-design/refs/heads/main/static/images/logo.png'
            else:
                tool['png'] = f"https://raw.githubusercontent.com/VHP4Safety/cloud/main/docs/service/{png_name}"

        # Getting selected stages from the URL.
        selected_stages = request.args.getlist('stage')

        # Filtering tools by selected stages.
        if selected_stages:
            tools = [tool for tool in tools if tool.get('stage') in selected_stages]

        # Getting all unique stages from the tools for the filter options.
        stages = sorted(set(tool.get('stage') for tool in tools if tool.get('stage')))

        # Forcing "Other" to be the last item in the list of stages.
        if 'Other' in stages:
            stages.remove('Other')
            stages.append('Other')

        return render_template("tools/tools.html", tools=tools, stages=stages, selected_stages=selected_stages)

    except Exception as e:
        return f"Error processing service data: {e}", 500

@app.route("/tools/qsprpred")
def qsprpred():
    return render_template("tools/qsprpred.html")


@app.route("/tools/qaop_app")
def qaop_app():
    return render_template("qaop_app.html")


################################################################################

################################################################################
### Pages under 'Case Studies'


@app.route("/casestudies/<case>")
def casestudy_main(case):
    # Only allow known case studies
    if case not in ["thyroid", "kidney", "parkinson"]:
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


@app.route("/compound/<cwid>")
def show_compound(cwid):
    try:
        return render_template(f"compound.html", cwid=cwid)
    except TemplateNotFound:
        abort(404)


################################################################################

################################################################################

### Pages under 'Legal'


@app.route("/legal/terms_of_service")
def terms_of_service():
    return render_template("legal/terms_of_service.html")


@app.route("/legal/privacypolicy")
def privacy_policy():
    return render_template("legal/privacypolicy.html")


# Import the new blueprint
from routes.aop_app import aop_app

# Register the blueprint
app.register_blueprint(aop_app)

################################################################################

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
