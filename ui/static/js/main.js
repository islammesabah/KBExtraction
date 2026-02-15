/**
 * Main entrypoint:
 * - initialize graph controller (Cytoscape)
 * - initialize keyword dropdown and connect it to graph updates
 *
 * Keep this file tiny.
 */

import { createGraphController } from "./graph_controller.js";
import { initKeywordDropdown } from "./keyword_dropdown.js";

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize Cytoscape
    const graph = createGraphController("cy");

    await initKeywordDropdown({
        selectId: "keyword-select",
        onGraphPayload: (payload) => graph.setGraph(payload.elements),
        defaultKeyword: null // optionally set e.g. "Transparency"
    });

    // File Upload UX
    const fileInput = document.getElementById('documents');
    const fileChosen = document.getElementById('file-chosen');
    fileInput.addEventListener('change', function () {
        fileChosen.textContent = this.files.length > 0 ? `${this.files.length} files selected` : "No file chosen";

        if (this.files.length > 0) {
            handleFileUpload(this.files[0]);
        }
    });

    // 4. Verification Logic
    const verificationSection = document.getElementById('verification-section');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    // Tab Switching
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            // Add active to clicked
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    function handleFileUpload(file) {
        const formData = new FormData();
        formData.append('document', file);

        fetch('/api/upload_verify', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error extracting knowledge: ' + data.error);
                    return;
                }

                // Show section
                verificationSection.style.display = 'block';

                // Clear common list for new file
                document.getElementById('common-verified-list').innerHTML = '';

                // Populate Tabs
                populateSplitView('existing-tab', data.existing);
                populateSplitView('partial-tab', data.partial);
                populateSplitView('new-tab', data.new);
            })
            .catch(err => console.error('Error uploading file:', err));
    }

    function populateSplitView(tabId, content) {
        // Target the content list specific to this tab
        const paneTop = document.querySelector(`#${tabId} .content-list`);

        // Target the SHARED bottom panel
        const paneBottom = document.getElementById('common-verified-list');

        paneTop.innerHTML = '';
        // Do NOT clear paneBottom here, as it is shared across tabs.
        // Clearing it would lose selections from other tabs.
        // Only clear if we are doing a fresh file upload (handled in handleFileUpload)

        if (!content) {
            paneTop.innerHTML = '<p>No content available.</p>';
            return;
        }

        // Split text into sentences (simple splitter)
        const sentences = content.match(/[^.!?]+[.!?]*(\s|$)/g) || [content];

        sentences.forEach((sentence, index) => {
            const rawText = sentence.trim();
            if (!rawText) return;

            // Unique ID per tab/sentence
            const id = `${tabId}-sent-${index}`;

            // Create Top Item
            const topItem = document.createElement('div');
            topItem.className = 'sentence-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = id;

            const label = document.createElement('label');
            label.htmlFor = id;
            label.textContent = rawText;

            topItem.appendChild(checkbox);
            topItem.appendChild(label);
            paneTop.appendChild(topItem);

            // Interaction
            checkbox.addEventListener('change', function () {
                if (this.checked) {
                    addToBottom(paneBottom, id, rawText);
                } else {
                    removeFromBottom(paneBottom, id);
                }
            });
        });
    }

    function addToBottom(paneBottom, id, text) {
        // Check if already exists (shouldn't if logic is correct, but safe check)
        if (paneBottom.querySelector(`[data-origin-id="${id}"]`)) return;

        const item = document.createElement('div');
        item.className = 'verified-item';
        item.dataset.originId = id;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = true; // Default to checked for verification

        // Allow unchecking from bottom to remove it (and uncheck top)
        checkbox.addEventListener('change', function () {
            if (!this.checked) {
                const originCheckbox = document.getElementById(id);
                if (originCheckbox) originCheckbox.checked = false;
                item.remove();
            }
        });

        const input = document.createElement('input');
        input.type = 'text';
        input.value = text;

        // Info Icon
        const infoIcon = document.createElement('span');
        infoIcon.className = 'info-icon';
        infoIcon.textContent = 'ℹ️';
        infoIcon.title = 'source->relationship->target'; // Static tooltip as requested

        item.appendChild(checkbox);
        item.appendChild(input);
        item.appendChild(infoIcon);
        paneBottom.appendChild(item);
    }

    function removeFromBottom(paneBottom, id) {
        const item = paneBottom.querySelector(`[data-origin-id="${id}"]`);
        if (item) {
            item.remove();
        }
    }

    // 3. Search & Filter Logic
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('node-search');
    const detailsContent = document.getElementById('details-content');
    const toggleViewBtn = document.getElementById('toggle-view-btn');

    toggleViewBtn.addEventListener('click', () => {
        const isHidden = verificationSection.style.display === 'none';
        verificationSection.style.display = isHidden ? 'block' : 'none';
    });

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    function performSearch() {
        const query = searchInput.value.trim();
        if (!query) {
            cy.elements().removeClass('faded highlighted');
            detailsContent.innerHTML = '<p class="placeholder-text">Select a node or search to view details.</p>';
            return;
        }

        // Fetch details from server 
        fetch('/api/search_node', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: query })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    detailsContent.innerHTML = `<p style="color:red">Error: ${data.error}</p>`;
                    return;
                }

                // Update Details Panel
                if (data.details && data.details.length > 0) {
                    detailsContent.innerHTML = data.details.map(item => `<div class="detail-item">${item}</div>`).join('');
                } else {
                    detailsContent.innerHTML = '<p>No details found for this node.</p>';
                }

                // Highlight in Graph
                cy.elements().removeClass('highlighted').addClass('faded');

                // Find the node in the client-side graph by label (assuming name == label for now)
                // Or we could have returned IDs from server to be precise. 
                // Let's try to match by label since that's what we have locally easiest.
                const targetNode = cy.nodes().filter(n => n.data('label') === query || n.data('id') === query); // simple match

                if (targetNode.length > 0) {
                    targetNode.removeClass('faded').addClass('highlighted');
                    const neighborhood = targetNode.neighborhood();
                    neighborhood.removeClass('faded').addClass('highlighted');

                    // Zoom to fit
                    cy.animate({
                        fit: {
                            eles: targetNode.union(neighborhood),
                            padding: 50
                        }
                    });
                }
            })
            .catch(err => {
                console.error(err);
                detailsContent.innerHTML = `<p style="color:red">Error connecting to server.</p>`;
            });
    }
});
