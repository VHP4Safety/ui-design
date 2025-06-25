// tool.js - Handles dynamic loading of tool content from JSON

document.addEventListener("DOMContentLoaded", function () {
  // Try to get the tool_json variable from a Jinja-injected meta tag
  let toolJson = "tool/qsprpred_content.json";
  // Try to find the tool_json value from a meta tag if present
  const meta = document.querySelector('meta[name="tool_json"]');
  if (meta) {
    toolJson = meta.getAttribute("content");
  } else if (window.tool_json) {
    toolJson = window.tool_json;
  } else {
    // fallback to query param for legacy support
    toolJson =
      new URLSearchParams(window.location.search).get("tool") || toolJson;
  }

  fetch(`/static/data/${toolJson}`)
    .then((response) => response.json())
    .then((data) => {
      document.getElementById("tool-title").textContent = data.title;
      document.getElementById(
        "tool-version"
      ).textContent = `${data.version}, ${data.license}`;
      document.getElementById("tool-run-btn").onclick = function () {
        window.open(data.run_url, "_blank");
      };
      document.getElementById("tool-github-link").href = data.github_url;

      // Tabs
      const tabsDiv = document.getElementById("tool-tabs");
      const contentDiv = document.getElementById("tool-content");
      tabsDiv.innerHTML = "";
      contentDiv.innerHTML = "";
      data.tabs.forEach((tab, idx) => {
        const btn = document.createElement("button");
        btn.className = "tool-tab" + (idx === 0 ? " active" : "");
        btn.id = `tab-${tab.id}`;
        btn.textContent = tab.label;
        btn.onclick = function () {
          document
            .querySelectorAll(".tool-tab")
            .forEach((el) => el.classList.remove("active"));
          btn.classList.add("active");
          document
            .querySelectorAll(".tab-content")
            .forEach((el) => (el.style.display = "none"));
          document.getElementById(`tab-content-${tab.id}`).style.display =
            "block";
        };
        tabsDiv.appendChild(btn);

        const tabContent = document.createElement("div");
        tabContent.id = `tab-content-${tab.id}`;
        tabContent.className = "tab-content";
        tabContent.style.display = idx === 0 ? "block" : "none";
        tabContent.innerHTML = `<p>${tab.content}</p>`;
        contentDiv.appendChild(tabContent);
      });
    });
});
