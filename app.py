################################################################################
### Loading the required modules
from flask import Flask, request, jsonify, render_template, send_file, Blueprint, render_template, abort
import requests
from wikidataintegrator import wdi_core
import json
import re
from werkzeug.routing import BaseConverter
from jinja2 import TemplateNotFound
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
@app.route('/')
def home():
    return render_template('home.html')
################################################################################

################################################################################
### Pages under 'Project Information'
@app.route('/information/mission_and_vision')
def mission_and_vision():
    return render_template('information/mission_and_vision.html')

@app.route('/information/research_lines')
def research_lines():
    return render_template('information/research_lines.html')

@app.route('/case_studies_and_regulatory_questions')
def case_studies_and_regulatory_questions():
    return render_template('information/case_studies_and_regulatory_questions.html')

@app.route('/information/partners_and_consortium')
def partners_and_consortium():
    return render_template('information/partners_and_consortium.html')

@app.route('/information/contact')
def contact():
    return render_template('information/contact.html')

@app.route('/youp')
def youp():
    return render_template('case_studies/thyroid/youp.html')

################################################################################

################################################################################
### Pages under 'Services' 

# Page to list all the services based on the list of services on the cloud repo.
@app.route('/templates/services/service_list')
def service_list():
    # Github API link to receive the list of the services on the cloud repo:
    url = f'https://api.github.com/repos/VHP4Safety/cloud/contents/docs/service'
    response = requests.get(url)

    # Checking if the request was successful (status code 200).
    if response.status_code == 200:
        # Extracting the list of files.
        service_content = response.json()

        # Separating .json and .md files.
        json_files = {file['name']: file for file in service_content if file['type'] == 'file' and file['name'].endswith('.json')}
        md_files = {file['name']: file for file in service_content if file['type'] == 'file' and file['name'].endswith('.md')}
        png_files = {file['name']: file for file in service_content if file['type'] == 'file' and file['name'].endswith('.png')}

        # Creating an empty list to store the results. 
        services = []

        # Fetching the .json files.
        for json_file_name, json_file in json_files.items():
            # Skipping the template.json file. 
            if json_file_name == 'template.json':
                continue
 
            json_url = json_file['download_url']  # Using the download URL from the API response.
            json_response = requests.get(json_url)

            if json_response.status_code == 200:
                json_data = json_response.json()
                
                # Extracting the 'service' field from the json file.
                service_name = json_data.get('service')
                description_string = json_data.get('description') 

                if service_name:
                    # Replacing the .json extension with the .md to get the corresponding .md file.
                    md_file_name = json_file_name.replace('.json', '.md')
                    html_name = json_file_name.replace('.json', '.html')
                    url = "https://cloud.vhp4safety.nl/service/"+ html_name 

                    if md_file_name in md_files:
                        md_file_url = f'https://raw.githubusercontent.com/VHP4Safety/cloud/main/docs/service/{md_file_name}'
                    else:
                        md_file_url = "md file not found"
                    png_file_name = md_file_name.replace('.md', '.png')

                    if png_file_name in png_files:
                        png_file_url = f'https://raw.githubusercontent.com/VHP4Safety/cloud/main/docs/service/{png_file_name}'
                        services.append({
                            'service': service_name,
                            'url': url,
                            'meta_data': md_file_url,
                            'description': description_string,
                            'png': png_file_url
                        })
                    else:
                        services.append({
                            'service': service_name,
                            'url': url,
                            'meta_data': md_file_url,
                            'description': description_string,
                            'png': "../../static/images/logo.png"
                        })

        mid=len(services) // 2
        chunk1 = services[ :mid]
        chunk2 = services[mid: ]
        print("Chunk1:")
        print(chunk1)

        print("Chunk2:")
        print(chunk2)

        # Passing the services data to the template after processing all JSON files.
        return render_template('services/service_list.html', chunk1=chunk1, chunk2=chunk2)
    else:
        return f"Error fetching files: {response.status_code}"

    # return render_template('services/service_list.html')

@app.route('/templates/services/qsprpred')
def qsprpred():
    return render_template('services/qsprpred.html')
    
################################################################################

################################################################################
### Pages under 'Case Studies' 

@app.route('/templates/case_studies/kidney/kidney')
def kidney_main():
    return render_template('case_studies/kidney/kidney.html')

@app.route('/templates/case_studies/parkinson/parkinson')
def parkinson_main():
    return render_template('case_studies/parkinson/parkinson.html')

@app.route('/templates/case_studies/parkinson/workflows/parkinson_hackathon_workflow')
def parkinson_hackathon_workflow():
    return render_template('case_studies/parkinson/workflows/parkinson_hackathon_workflow.html')

@app.route('/workflow/<workflow>')
def show(workflow):
    try:
        return render_template(f'case_studies/parkinson/workflows/{workflow}_workflow.html')
    except TemplateNotFound:
        abort(404)

@app.route('/compound/<cwid>')
def show_compound(cwid):
    try:
        return render_template(f'compound.html', cwid=cwid)
    except TemplateNotFound:
        abort(404)

@app.route('/templates/case_studies/thyroid/thyroid')
def thyroid_main():
    return render_template('case_studies/thyroid/thyroid.html')

@app.route('/templates/case_studies/thyroid/workflows/thyroid_hackathon_demo_workflow')
def thyroid_workflow_1():
    return render_template('case_studies/thyroid/workflows/thyroid_hackathon_demo_workflow.html')
@app.route('/templates/case_studies/thyroid/workflows/ngra_silymarin')
def ngra_silymarin():
    return render_template('case_studies/thyroid/workflows/ngra_silymarin.html')

################################################################################

# Import the new blueprint
from routes.aop_app import aop_app

# Register the blueprint
app.register_blueprint(aop_app)

################################################################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

