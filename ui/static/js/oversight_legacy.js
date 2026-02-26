/**
 * oversight_legacy.js
 * -------------------
 * Legacy/supervisor-provided oversight UI logic.
 *
 * This module is intentionally isolated so it can be:
 * - kept temporarily
 * - deleted later without impacting the real pipeline
 *
 * NOTE:
 * - Bootstrap tabs do not require custom JS if using data-bs-toggle="tab".
 * - This code is here ONLY as a reference/backup.
 */

/**
 * Wire legacy upload+verification endpoint and populate 3 tabs + shared bottom panel.
 *
 * @param {Object} params
 * @param {string} params.fileInputId - file input id
 * @param {string} params.verificationSectionId - container section id
 * @param {string} params.commonVerifiedListId - shared bottom panel id
 * @param {string} params.endpoint - POST endpoint for legacy verify upload
 */
export function wireOversightLegacy({
  fileInputId = "documents",
  verificationSectionId = "oversight-section",
  commonVerifiedListId = "common-verified-list",
  endpoint = "/api/upload_verify",
}) {
  const fileInput = document.getElementById(fileInputId);
  const verificationSection = document.getElementById(verificationSectionId);
  const commonVerifiedList = document.getElementById(commonVerifiedListId);

  if (!fileInput || !verificationSection || !commonVerifiedList) return;

  fileInput.addEventListener("change", () => {
    if (!fileInput.files || fileInput.files.length === 0) return;
    handleFileUpload(fileInput.files[0]);
  });

  async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append("document", file);

    try {
      const resp = await fetch(endpoint, { method: "POST", body: formData });
      const data = await resp.json();

      if (data.error) {
        alert("Error extracting knowledge: " + data.error);
        return;
      }

      // Show section
      verificationSection.style.display = "block";

      // Clear shared list on fresh upload
      commonVerifiedList.innerHTML = "";

      // Populate the three legacy tabs
      populateSplitView("existing-tab", data.existing);
      populateSplitView("partial-tab", data.partial);
      populateSplitView("new-tab", data.new);
    } catch (err) {
      console.error("Error uploading file:", err);
    }
  }

  function populateSplitView(tabId, content) {
    const paneTop = document.querySelector(`#${tabId} .content-list`);
    const paneBottom = commonVerifiedList;
    if (!paneTop) return;

    paneTop.innerHTML = "";

    if (!content) {
      paneTop.innerHTML = "<p>No content available.</p>";
      return;
    }

    const sentences = content.match(/[^.!?]+[.!?]*(\s|$)/g) || [content];

    sentences.forEach((sentence, index) => {
      const rawText = sentence.trim();
      if (!rawText) return;

      const id = `${tabId}-sent-${index}`;

      const topItem = document.createElement("div");
      topItem.className = "sentence-item";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.id = id;

      const label = document.createElement("label");
      label.htmlFor = id;
      label.textContent = rawText;

      topItem.appendChild(checkbox);
      topItem.appendChild(label);
      paneTop.appendChild(topItem);

      checkbox.addEventListener("change", function () {
        if (this.checked) addToBottom(paneBottom, id, rawText);
        else removeFromBottom(paneBottom, id);
      });
    });
  }

  function addToBottom(paneBottom, id, text) {
    if (paneBottom.querySelector(`[data-origin-id="${id}"]`)) return;

    const item = document.createElement("div");
    item.className = "verified-item";
    item.dataset.originId = id;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;

    checkbox.addEventListener("change", function () {
      if (!this.checked) {
        const originCheckbox = document.getElementById(id);
        if (originCheckbox) originCheckbox.checked = false;
        item.remove();
      }
    });

    const input = document.createElement("input");
    input.type = "text";
    input.value = text;

    const infoIcon = document.createElement("span");
    infoIcon.className = "info-icon";
    infoIcon.textContent = "ℹ️";
    infoIcon.title = "source->relationship->target";

    item.appendChild(checkbox);
    item.appendChild(input);
    item.appendChild(infoIcon);
    paneBottom.appendChild(item);
  }

  function removeFromBottom(paneBottom, id) {
    const item = paneBottom.querySelector(`[data-origin-id="${id}"]`);
    if (item) item.remove();
  }
}