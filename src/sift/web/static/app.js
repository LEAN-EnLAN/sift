/* Sift Web Companion — minimal SPA */

(function () {
    "use strict";

    const API_BASE = "/api";

    const form = document.getElementById("search-form");
    const queryInput = document.getElementById("query-input");
    const languageInput = document.getElementById("language-input");
    const resultsContainer = document.getElementById("results");
    const historyList = document.getElementById("history-list");

    // Load history on startup
    loadHistory();

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query) return;

        const languages = languageInput.value
            .split(",")
            .map(function (l) { return l.trim(); })
            .filter(function (l) { return l.length > 0; });

        performSearch(query, languages);
    });

    function performSearch(query, languages) {
        resultsContainer.innerHTML = '<p class="empty-state">Searching...</p>';

        fetch(API_BASE + "/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query, languages: languages, top: 5 }),
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) {
                    resultsContainer.innerHTML = '<p class="empty-state">Error: ' + escapeHtml(data.error) + "</p>";
                    return;
                }
                renderResults(data.results || []);
                loadHistory();
            })
            .catch(function (err) {
                resultsContainer.innerHTML = '<p class="empty-state">Request failed: ' + escapeHtml(err.message) + "</p>";
            });
    }

    function renderResults(repos) {
        if (!repos.length) {
            resultsContainer.innerHTML = '<p class="empty-state">No results found. Try different keywords.</p>';
            return;
        }

        var html = "";
        repos.forEach(function (repo) {
            var score = repo.score || 0;
            html += '<div class="repo-card">';
            html += '<h3><a href="' + escapeHtml(repo.url) + '" target="_blank" rel="noopener">' + escapeHtml(repo.name) + "</a></h3>";
            html += '<div class="repo-meta">';
            if (repo.description) html += escapeHtml(repo.description) + " &middot; ";
            html += "&#9733; " + (repo.stars || 0);
            if (repo.language) html += " &middot; " + escapeHtml(repo.language);
            if (repo.license) html += " &middot; " + escapeHtml(repo.license);
            html += "</div>";
            html += '<div class="score-bar"><div class="score-fill" style="width:' + Math.min(score, 100) + '%"></div></div>';
            if (repo.why) html += '<div class="repo-why">' + escapeHtml(repo.why) + "</div>";
            html += "</div>";
        });
        resultsContainer.innerHTML = html;
    }

    function loadHistory() {
        fetch(API_BASE + "/history")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var entries = data.entries || [];
                if (!entries.length) {
                    historyList.innerHTML = '<li style="color:var(--text-secondary)">No recent searches</li>';
                    return;
                }
                var html = "";
                entries.forEach(function (entry) {
                    html += '<li data-query="' + escapeHtml(entry.query) + '">' + escapeHtml(entry.query);
                    if (entry.languages && entry.languages.length) {
                        html += ' <span style="color:var(--text-secondary)">(' + escapeHtml(entry.languages.join(", ")) + ')</span>';
                    }
                    html += "</li>";
                });
                historyList.innerHTML = html;

                // Click to re-search
                historyList.querySelectorAll("li[data-query]").forEach(function (li) {
                    li.addEventListener("click", function () {
                        queryInput.value = li.getAttribute("data-query");
                        performSearch(li.getAttribute("data-query"), []);
                    });
                });
            })
            .catch(function () {
                historyList.innerHTML = '<li style="color:var(--text-secondary)">History unavailable</li>';
            });
    }

    function escapeHtml(text) {
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
})();
