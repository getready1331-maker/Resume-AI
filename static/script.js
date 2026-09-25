/* ==============================
   FINDING THE BACKEND

   The page may be opened three ways:
     1. http://127.0.0.1:5000        served by Flask itself
     2. http://127.0.0.1:5500        Live Server / another dev server
     3. file:///.../index.html       opened by double click

   In case 1 the API is on the same address. In cases 2 and 3 it is not,
   so we test the known Flask addresses and use the first one that answers.
============================== */

const CANDIDATES = [
    location.protocol.startsWith("http") ? location.origin : null,
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5050",
    "http://127.0.0.1:8000"
].filter(Boolean);

let API_URL = null;


async function findBackend() {

    if (API_URL !== null) {
        return API_URL;
    }

    for (const base of CANDIDATES) {
        try {
            const res = await fetch(base + "/api/health", { method: "GET" });

            if (!res.ok) {
                continue;
            }

            const info = await res.json();

            /* another project may also be running on one of these ports,
               so only accept the server that identifies itself as this app */
            if (info && info.app === "resume-analyzer") {
                API_URL = base;
                return API_URL;
            }

        } catch (ignored) {
            /* try the next address */
        }
    }

    throw new Error(
        "Could not reach the backend. Open a terminal in the project folder " +
        "and run: python app.py"
    );
}


const resumeFile = document.getElementById("resumeFile");
const fileName = document.getElementById("fileName");
const analyzeBtn = document.getElementById("analyzeBtn");
const message = document.getElementById("message");
const results = document.getElementById("results");
const jobOptions = document.getElementById("jobOptions");
const jobsCount = document.getElementById("jobsCount");
const cityChips = document.getElementById("cityChips");
const zoneFilter = document.getElementById("zoneFilter");
const roleFilter = document.getElementById("roleFilter");

/* every job returned by the backend, kept for filtering */
let allJobs = [];
let activeCity = "";


/* ==============================
   FILE SELECTION
============================== */

resumeFile.addEventListener("change", function () {

    if (!resumeFile.files.length) {
        fileName.textContent = "";
        return;
    }

    const file = resumeFile.files[0];

    const extension = file.name.split(".").pop().toLowerCase();

    if (!["pdf", "doc", "docx", "txt"].includes(extension)) {
        message.textContent = "Please upload a PDF, DOC, DOCX or TXT file.";
        resumeFile.value = "";
        fileName.textContent = "";
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        message.textContent = "File is larger than 5 MB. Please upload a smaller file.";
        resumeFile.value = "";
        fileName.textContent = "";
        return;
    }

    fileName.textContent = "✓ Selected: " + file.name;
    message.textContent = "";
});


/* ==============================
   ANALYZE RESUME
============================== */

analyzeBtn.addEventListener("click", async function () {

    if (!resumeFile.files.length) {
        message.textContent = "Please upload your resume first.";
        return;
    }

    const formData = new FormData();
    formData.append("resume", resumeFile.files[0]);

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";
    message.style.color = "#475569";
    message.textContent = "Reading your resume and finding jobs across India...";

    try {

        const base = await findBackend();

        const response = await fetch(base + "/api/analyze", {
            method: "POST",
            body: formData
        });

        let data = null;
        const rawText = await response.text();

        try {
            data = JSON.parse(rawText);
        } catch (parseError) {
            data = null;
        }

        if (!response.ok) {
            throw new Error(
                (data && data.error)
                    ? data.error
                    : "Server returned " + response.status + ": " +
                      rawText.slice(0, 120)
            );
        }

        if (!data) {
            throw new Error(
                "The server replied with something that is not JSON: " +
                rawText.slice(0, 120)
            );
        }

        showResults(data);
        message.textContent = "";

    } catch (error) {

        message.style.color = "#dc2626";
        message.textContent = error.message;

    } finally {

        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "🔍 Analyze Resume";
    }
});


/* ==============================
   SHOW RESULTS
============================== */

function showResults(data) {

    setText("score", data.resume_score + "%");
    setText("resumeSummary", data.summary);

    /* SCORE BREAKDOWN */

    setHtml(
        "scoreBreakdown",
        (data.score_breakdown || [])
            .map(item => `
                <div class="breakdown-row">
                    <span>${escapeHtml(item.label)}</span>
                    <span class="bar">
                        <i style="width:${Math.round((item.score / item.max) * 100)}%"></i>
                    </span>
                    <b>${item.score}/${item.max}</b>
                </div>
            `)
            .join("")
    );


    /* CAREER MATCHES */

    setHtml(
        "careerMatches",
        (data.career_matches || []).length
            ? data.career_matches
                .map(role => `
                    <div class="match-item">
                        <div>
                            <strong>${escapeHtml(role.title)}</strong>
                            <small>${escapeHtml(role.salary || "")}</small>
                        </div>
                        <span class="match">${role.match_score}% Match</span>
                    </div>
                `)
                .join("")
            : "<p>Add more skills to your resume to see career matches.</p>"
    );


    /* SKILLS FOUND */

    setHtml(
        "skillsFound",
        (data.skills_found || []).length
            ? data.skills_found.map(s => `<p>✓ ${escapeHtml(s)}</p>`).join("")
            : "<p>No known skills detected.</p>"
    );


    /* SKILLS TO IMPROVE */

    setHtml(
        "missingSkills",
        (data.skills_to_improve || []).length
            ? data.skills_to_improve.map(s => `<p>• ${escapeHtml(s)}</p>`).join("")
            : "<p>No major gaps detected.</p>"
    );


    /* SUGGESTIONS */

    setHtml(
        "suggestions",
        (data.suggestions || []).map(s => `<li>${escapeHtml(s)}</li>`).join("")
    );


    /* JOBS ACROSS INDIA */

    allJobs = data.jobs || [];
    activeCity = "";

    buildRoleFilter(allJobs);
    buildCityChips(data.cities || []);
    renderJobs();

    results.style.display = "block";
    results.scrollIntoView({ behavior: "smooth" });
}


/* ==============================
   FILTERS
============================== */

function buildRoleFilter(jobs) {

    const seen = new Map();

    jobs.forEach(job => seen.set(job.role_id, job.title));

    roleFilter.innerHTML =
        `<option value="">All roles</option>` +
        [...seen].map(
            ([id, title]) =>
                `<option value="${escapeHtml(id)}">${escapeHtml(title)}</option>`
        ).join("");
}


function buildCityChips(cities) {

    if (!cities.length) {
        cityChips.innerHTML = "";
        return;
    }

    cityChips.innerHTML =
        `<button class="chip active" data-city="">All cities</button>` +
        cities
            .map(
                c => `
                <button class="chip" data-city="${escapeHtml(c.city)}">
                    ${escapeHtml(c.city)}
                    <span>${c.openings}</span>
                </button>`
            )
            .join("");

    cityChips.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
            activeCity = chip.dataset.city;
            cityChips.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            renderJobs();
        });
    });
}


zoneFilter.addEventListener("change", renderJobs);
roleFilter.addEventListener("change", renderJobs);


function renderJobs() {

    const zone = zoneFilter.value;
    const role = roleFilter.value;

    const filtered = allJobs.filter(job =>
        (!zone || job.zone === zone) &&
        (!role || job.role_id === role) &&
        (!activeCity || job.city === activeCity)
    );

    const cityTotal = new Set(filtered.map(job => job.city)).size;

    jobsCount.textContent =
        filtered.length
            ? filtered.length + " openings in " + cityTotal + " cities across India"
            : "No openings match this filter.";

    jobOptions.innerHTML = filtered.length
        ? filtered.map(createJobCard).join("")
        : `<div class="empty-jobs">
               No jobs for this filter. Choose another city or region.
           </div>`;
}


/* ==============================
   JOB CARD
============================== */

function createJobCard(job) {

    const requirements = job.requirements || [];
    const matched = job.matched_skills || [];

    return `
        <div class="job-card">

            <div class="job-top">

                <div>
                    <div class="job-icon">💼</div>
                    <h3>${escapeHtml(job.title)}</h3>
                    <div class="company">${escapeHtml(job.company)}</div>
                </div>

                <span class="match">${job.match_score}% Match</span>

            </div>

            <div class="job-meta">
                <span>📍 ${escapeHtml(job.location || "India")}</span>
                <span>🕒 ${escapeHtml(job.job_type || "Not specified")}</span>
                <span>👤 ${escapeHtml(job.experience || "Any experience")}</span>
                <span>💰 ${escapeHtml(job.salary || "Not disclosed")}</span>
                <span>📅 ${escapeHtml(job.posted || "Not available")}</span>
            </div>

            <div class="requirements">
                <strong>Requirements</strong>
                <ul>
                    ${
                        requirements.length
                            ? requirements
                                .map(req => `
                                    <li class="${matched.includes(req) ? "have" : ""}">
                                        ${escapeHtml(req)}
                                    </li>`)
                                .join("")
                            : "<li>See job description</li>"
                    }
                </ul>
            </div>

            ${
                job.apply_url && job.apply_url !== "#"
                    ? `<a class="apply-btn"
                           href="${safeUrl(job.apply_url)}"
                           target="_blank"
                           rel="noopener noreferrer">
                           View &amp; Apply
                       </a>`
                    : `<span class="apply-btn disabled">Demo Only</span>`
            }

        </div>
    `;
}


/* ==============================
   HELPERS
============================== */

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}


function setHtml(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.innerHTML = value;
    }
}


function escapeHtml(value) {
    return String(value === undefined || value === null ? "" : value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function safeUrl(url) {
    try {
        const parsed = new URL(url);
        if (parsed.protocol === "http:" || parsed.protocol === "https:") {
            return parsed.href;
        }
        return "#";
    } catch {
        return "#";
    }
}


/* ==============================
   CONNECTION CHECK ON PAGE LOAD
   Tells the user the server is missing before they upload anything.
============================== */

(async function checkBackend() {

    const status = document.getElementById("backendStatus");

    if (!status) {
        return;
    }

    try {

        const base = await findBackend();

        status.className = "backend-status online";
        status.textContent =
            "● Connected to the server at " + (base || location.origin);

    } catch (error) {

        status.className = "backend-status offline";
        status.textContent =
            "● Server not running. Open the project folder in a terminal " +
            "and run: python app.py";
    }
})();
