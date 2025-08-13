# Tool JSON Files

The JSON files in this folder (e.g., `qaopapp_content.json`, `qsprpred_content.json`) contain the content and configuration for each tool page.

When a user visits a tool page, the JavaScript file `tool.js` determines which tool to load based on the URL or data passed from the backend. It then fetches the corresponding JSON file and uses its data to dynamically fill the `tool.html` template, updating the page with the correct information, features, and UI for that tool.

Each tool needs its own JSON file to ensure that the content is modular and can be easily updated or expanded without changing the HTML structure. This approach allows for a clean separation of content and presentation, making it easier to maintain and scale the application.
