## Case Study JSON Files

The JSON files in this folder (e.g., `kidney_content.json`, `parkinson_content.json`, `thyroid_content.json`) contain all the content and workflow data for each case study.

When a user visits a case study page, the JavaScript file `casestudies.js` determines which case study to load based on the URL. It then fetches the corresponding JSON file and uses its data to dynamically fill the `casestudy.html` template, updating the page with the correct questions, steps, and content for that case study.
