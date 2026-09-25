/* =========================================================
   AI RESUME ANALYZER - FRONTEND
   Works with Flask backend on port 5050/5000/etc.
========================================================= */


/* ==============================
   FIND BACKEND
============================== */

const CANDIDATES = [
    location.protocol.startsWith("http") ? location.origin : null,

    "http://127.0.0.1:5050",
    "http://127.0.0.1:5000",
    "http://localhost:5050",
    "http://localhost:5000",
    "http://127.0.0.1:5001",
    "http://127.0.0.1:8000"
].filter(Boolean);

let API_URL = null;


async function findBackend() {

    if (API_URL !== null) {
        return API_URL;
    }

    for (const base of CANDIDATES) {

        try {

            const response = await fetch(
                base + "/api/health",
                {
                    method: "GET",
                    cache: "no-store"
                }
            );

            if (!response.ok) {
                continue;
            }

            const info = await response.json();

            if (
                info &&
                info.app === "resume-analyzer"
            ) {
                API_URL = base;
                return API_URL;
            }

        } catch (error) {
            // Try next backend address
        }
    }

    throw new Error(
        "Could not reach the backend. Run 'python app.py' in C:\\.reselude"
    );
}


/* ==============================
   DOM ELEMENTS
============================== */

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

let allJobs = [];
let activeCity = "";


/* ==============================
   FILE SELECTION
============================== */

if (resumeFile) {

    resumeFile.addEventListener("change", function () {

        if (!resumeFile.files.length) {

            if (fileName) {
                fileName.textContent = "";
            }

            return;
        }

        const file = resumeFile.files[0];

        const extension = file.name
            .split(".")
            .pop()
            .toLowerCase();

        const allowed = [
            "pdf",
            "doc",
            "docx",
            "txt"
        ];

        if (!allowed.includes(extension)) {

            showMessage(
                "Please upload a PDF, DOC, DOCX or TXT file.",
                true
            );

            resumeFile.value = "";

            if (fileName) {
                fileName.textContent = "";
            }

            return;
        }

        if (file.size > 5 * 1024 * 1024) {

            showMessage(
                "File is larger than 5 MB. Please upload a smaller file.",
                true
            );

            resumeFile.value = "";

            if (fileName) {
                fileName.textContent = "";
            }

            return;
        }

        if (fileName) {
            fileName.textContent =
                "✓ Selected: " + file.name;
        }

        if (message) {
            message.textContent = "";
        }
    });
}


/* ==============================
   ANALYZE RESUME
============================== */

if (analyzeBtn) {

    analyzeBtn.addEventListener("click", async function () {

        if (!resumeFile || !resumeFile.files.length) {

            showMessage(
                "Please upload your resume first.",
                true
            );

            return;
        }

        const file = resumeFile.files[0];

        const formData = new FormData();

        // IMPORTANT:
        // Flask expects the field name "resume"
        formData.append("resume", file);

        analyzeBtn.disabled = true;
        analyzeBtn.textContent = "Analyzing...";

        showMessage(
            "Reading your resume and finding jobs across India...",
            false
        );

        try {

            const base = await findBackend();

            const response = await fetch(
                base + "/api/analyze",
                {
                    method: "POST",
                    body: formData
                }
            );

            const rawText = await response.text();

            let data = null;

            try {
                data = JSON.parse(rawText);
            } catch (error) {
                data = null;
            }

            if (!response.ok) {

                throw new Error(
                    data && data.error
                        ? data.error
                        : data && data.message
                            ? data.message
                            : "Server returned HTTP " +
                              response.status
                );
            }

            if (!data) {

                throw new Error(
                    "The server returned an invalid response."
                );
            }

            if (data.success === false) {

                throw new Error(
                    data.error ||
                    data.message ||
                    "Resume analysis failed."
                );
            }

            showResults(data);

            if (message) {
                message.textContent = "";
            }

        } catch (error) {

            console.error("Analysis error:", error);

            showMessage(
                error.message ||
                "Something went wrong while analyzing the resume.",
                true
            );

        } finally {

            analyzeBtn.disabled = false;
            analyzeBtn.textContent = "🔍 Analyze Resume";
        }
    });
}


/* ==============================
   SHOW RESULTS
============================== */

function showResults(data) {

    /* ==========================
       RESUME SCORE
    ========================== */

    const resumeScore =
        Number(data.resume_score || 0);

    setText(
        "score",
        resumeScore + "%"
    );


    /* ==========================
       SUMMARY
    ========================== */

    setText(
        "resumeSummary",
        data.summary ||
        "Resume analyzed successfully."
    );


    /* ==========================
       SCORE BREAKDOWN
    ========================== */

    const breakdown =
        data.score_breakdown || {};

    let breakdownHTML = "";

    if (Array.isArray(breakdown)) {

        breakdownHTML = breakdown.map(item => {

            const name =
                item.name ||
                item.label ||
                "Score";

            const value =
                item.score ??
                item.value ??
                0;

            return `
                <div class="score-item">
                    <span>${escapeHtml(name)}</span>
                    <strong>${escapeHtml(value)}</strong>
                </div>
            `;

        }).join("");

    } else if (
        typeof breakdown === "object" &&
        breakdown !== null
    ) {

        breakdownHTML =
            Object.entries(breakdown)
                .map(([key, value]) => {

                    const label =
                        key
                            .replaceAll("_", " ")
                            .replace(/\b\w/g, letter =>
                                letter.toUpperCase()
                            );

                    return `
                        <div class="score-item">
                            <span>${escapeHtml(label)}</span>
                            <strong>${escapeHtml(value)}</strong>
                        </div>
                    `;

                })
                .join("");
    }

    if (!breakdownHTML) {

        breakdownHTML = `
            <div class="score-item">
                <span>Overall Resume Score</span>
                <strong>${resumeScore}%</strong>
            </div>
        `;
    }

    setHtml(
        "scoreBreakdown",
        breakdownHTML
    );


    /* ==========================
       CAREER MATCHES
    ========================== */

    const careerMatches =
        Array.isArray(data.career_matches)
            ? data.career_matches
            : [];

    setHtml(
        "careerMatches",

        careerMatches.length

            ? careerMatches.map(role => {

                const title =
                    role.title ||
                    role.role ||
                    "Career";

                const score =
                    role.match_score ??
                    role.score ??
                    0;

                const matchedSkills =
                    Array.isArray(role.matched_skills)
                        ? role.matched_skills
                        : [];

                const missingSkills =
                    Array.isArray(role.missing_skills)
                        ? role.missing_skills
                        : [];

                return `
                    <div class="match-item">

                        <div>

                            <strong>
                                ${escapeHtml(title)}
                            </strong>

                            ${
                                matchedSkills.length
                                    ? `
                                        <small>
                                            Skills matched:
                                            ${escapeHtml(
                                                matchedSkills.join(", ")
                                            )}
                                        </small>
                                      `
                                    : ""
                            }

                            ${
                                missingSkills.length
                                    ? `
                                        <small>
                                            Missing:
                                            ${escapeHtml(
                                                missingSkills.join(", ")
                                            )}
                                        </small>
                                      `
                                    : ""
                            }

                        </div>

                        <span class="match">
                            ${escapeHtml(score)}% Match
                        </span>

                    </div>
                `;

            }).join("")

            : `
                <p>
                    Add relevant technical skills to your resume
                    to see career matches.
                </p>
            `
    );


    /* ==========================
       SKILLS FOUND
    ========================== */

    const skillsFound =
        Array.isArray(data.skills_found)
            ? data.skills_found
            : [];

    setHtml(
        "skillsFound",

        skillsFound.length

            ? skillsFound
                .map(skill =>
                    `<p>✓ ${escapeHtml(skill)}</p>`
                )
                .join("")

            : "<p>No known skills detected.</p>"
    );


    /* ==========================
       SKILLS TO IMPROVE
    ========================== */

    const skillsToImprove =
        Array.isArray(data.skills_to_improve)
            ? data.skills_to_improve
            : [];

    setHtml(
        "missingSkills",

        skillsToImprove.length

            ? skillsToImprove
                .map(skill =>
                    `<p>• ${escapeHtml(skill)}</p>`
                )
                .join("")

            : "<p>No major skill gaps detected.</p>"
    );


    /* ==========================
       SUGGESTIONS
    ========================== */

    const suggestions =
        Array.isArray(data.suggestions)
            ? data.suggestions
            : [];

    setHtml(
        "suggestions",

        suggestions.length

            ? suggestions
                .map(suggestion =>
                    `<li>${escapeHtml(suggestion)}</li>`
                )
                .join("")

            : "<li>Your resume has been analyzed successfully.</li>"
    );


    /* ==========================
       JOBS
    ========================== */

    allJobs =
        Array.isArray(data.jobs)
            ? data.jobs
            : [];

    activeCity = "";


    /* JOB ERROR */

    if (
        data.jobs_error &&
        allJobs.length === 0
    ) {

        setHtml(
            "jobOptions",
            `
                <div class="empty-jobs">
                    <strong>Live jobs could not be loaded.</strong>
                    <p>
                        ${escapeHtml(data.jobs_error)}
                    </p>
                </div>
            `
        );

        setText(
            "jobsCount",
            "Live job listings are currently unavailable."
        );

    } else {

        buildRoleFilter(allJobs);

        buildCityChips(
            getCitiesFromJobs(allJobs)
        );

        renderJobs();
    }


    /* ==========================
       SHOW RESULTS
    ========================== */

    if (results) {

        results.style.display = "block";

        results.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
}


/* ==============================
   GET CITIES FROM REAL JOB DATA
============================== */

function getCitiesFromJobs(jobs) {

    const cityMap = new Map();

    jobs.forEach(job => {

        const location =
            job.location || "";

        if (!location) {
            return;
        }

        const parts =
            location
                .split(",")
                .map(x => x.trim())
                .filter(Boolean);

        const city =
            parts.length
                ? parts[0]
                : location;

        if (!cityMap.has(city)) {
            cityMap.set(city, 0);
        }

        cityMap.set(
            city,
            cityMap.get(city) + 1
        );
    });

    return [...cityMap.entries()]
        .map(([city, openings]) => ({
            city,
            openings
        }))
        .sort((a, b) =>
            b.openings - a.openings
        );
}


/* ==============================
   ROLE FILTER
============================== */

function buildRoleFilter(jobs) {

    if (!roleFilter) {
        return;
    }

    const seen = new Map();

    jobs.forEach(job => {

        const title =
            job.title ||
            job.job_title ||
            "Unknown Role";

        const roleId =
            job.role_id ||
            title;

        if (!seen.has(roleId)) {
            seen.set(roleId, title);
        }
    });

    roleFilter.innerHTML =
        `<option value="">All roles</option>` +

        [...seen]
            .map(([id, title]) => `
                <option value="${escapeHtml(id)}">
                    ${escapeHtml(title)}
                </option>
            `)
            .join("");
}


/* ==============================
   CITY CHIPS
============================== */

function buildCityChips(cities) {

    if (!cityChips) {
        return;
    }

    if (!cities.length) {

        cityChips.innerHTML = "";

        return;
    }

    cityChips.innerHTML =
        `
        <button
            class="chip active"
            data-city="">
            All cities
        </button>
        ` +

        cities
            .map(city => `
                <button
                    class="chip"
                    data-city="${escapeHtml(city.city)}">

                    ${escapeHtml(city.city)}

                    <span>
                        ${escapeHtml(city.openings)}
                    </span>

                </button>
            `)
            .join("");


    cityChips
        .querySelectorAll(".chip")
        .forEach(chip => {

            chip.addEventListener(
                "click",
                function () {

                    activeCity =
                        chip.dataset.city || "";

                    cityChips
                        .querySelectorAll(".chip")
                        .forEach(c =>
                            c.classList.remove("active")
                        );

                    chip.classList.add("active");

                    renderJobs();
                }
            );
        });
}


/* ==============================
   FILTER EVENTS
============================== */

if (zoneFilter) {
    zoneFilter.addEventListener(
        "change",
        renderJobs
    );
}

if (roleFilter) {
    roleFilter.addEventListener(
        "change",
        renderJobs
    );
}


/* ==============================
   RENDER JOBS
============================== */

function renderJobs() {

    if (!jobOptions) {
        return;
    }

    const zone =
        zoneFilter
            ? zoneFilter.value
            : "";

    const role =
        roleFilter
            ? roleFilter.value
            : "";


    const filtered =
        allJobs.filter(job => {

            const jobTitle =
                job.title ||
                job.job_title ||
                "";

            const jobRoleId =
                job.role_id ||
                jobTitle;

            const jobLocation =
                job.location ||
                "";

            return (

                (!zone ||
                    job.zone === zone)

                &&

                (!role ||
                    jobRoleId === role)

                &&

                (!activeCity ||
                    jobLocation
                        .toLowerCase()
                        .includes(
                            activeCity.toLowerCase()
                        ))
            );
        });


    const cityTotal =
        new Set(
            filtered
                .map(job =>
                    job.location || ""
                )
                .filter(Boolean)
        ).size;


    if (jobsCount) {

        jobsCount.textContent =
            filtered.length

                ? filtered.length +
                  " live openings in " +
                  cityTotal +
                  " locations"

                : "No live jobs match this filter.";
    }


    jobOptions.innerHTML =
        filtered.length

            ? filtered
                .map(createJobCard)
                .join("")

            : `
                <div class="empty-jobs">
                    No jobs match this filter.
                    Try another role or city.
                </div>
            `;
}


/* ==============================
   JOB CARD
============================== */

function createJobCard(job) {

    const title =
        job.title ||
        job.job_title ||
        "Job Opening";

    const company =
        job.company ||
        "Company not specified";

    const location =
        job.location ||
        "India";

    const jobType =
        job.job_type ||
        "Not specified";

    const experience =
        job.experience ||
        "Not specified";

    const posted =
        job.posted_date ||
        job.posted ||
        "Not available";

    const applyUrl =
        job.apply_link ||
        job.apply_url ||
        "#";

    const requirements =
        Array.isArray(job.skills_required)
            ? job.skills_required
            : Array.isArray(job.requirements)
                ? job.requirements
                : [];

    const matched =
        Array.isArray(job.matched_skills)
            ? job.matched_skills
            : [];

    const missing =
        Array.isArray(job.missing_skills)
            ? job.missing_skills
            : [];

    const matchScore =
        job.match_score ??
        0;

    const description =
        job.description ||
        job.about_company ||
        "No description available.";


    return `
        <div class="job-card">

            <div class="job-top">

                <div>

                    <div class="job-icon">
                        💼
                    </div>

                    <h3>
                        ${escapeHtml(title)}
                    </h3>

                    <div class="company">
                        ${escapeHtml(company)}
                    </div>

                </div>

                <span class="match">
                    ${escapeHtml(matchScore)}% Match
                </span>

            </div>


            <div class="job-meta">

                <span>
                    📍 ${escapeHtml(location)}
                </span>

                <span>
                    🕒 ${escapeHtml(jobType)}
                </span>

                <span>
                    👤 ${escapeHtml(experience)}
                </span>

                <span>
                    📅 ${escapeHtml(posted)}
                </span>

            </div>


            <div class="job-description">

                <p>
                    ${escapeHtml(
                        truncate(description, 300)
                    )}
                </p>

            </div>


            ${
                requirements.length

                    ? `
                        <div class="requirements">

                            <strong>
                                Skills Required
                            </strong>

                            <ul>

                                ${
                                    requirements
                                        .map(skill => {

                                            const isMatched =
                                                matched.some(
                                                    m =>
                                                        m.toLowerCase() ===
                                                        skill.toLowerCase()
                                                );

                                            const isMissing =
                                                missing.some(
                                                    m =>
                                                        m.toLowerCase() ===
                                                        skill.toLowerCase()
                                                );

                                            return `
                                                <li
                                                    class="${
                                                        isMatched
                                                            ? "have"
                                                            : isMissing
                                                                ? "missing"
                                                                : ""
                                                    }">

                                                    ${
                                                        isMatched
                                                            ? "✓ "
                                                            : ""
                                                    }

                                                    ${escapeHtml(skill)}

                                                </li>
                                            `;

                                        })
                                        .join("")
                                }

                            </ul>

                        </div>
                    `

                    : ""
            }


            ${
                matched.length

                    ? `
                        <div class="matched-job-skills">

                            <strong>
                                Your Matching Skills:
                            </strong>

                            <span>
                                ${escapeHtml(
                                    matched.join(", ")
                                )}
                            </span>

                        </div>
                    `

                    : ""
            }


            ${
                applyUrl !== "#"

                    ? `
                        <a
                            class="apply-btn"
                            href="${safeUrl(applyUrl)}"
                            target="_blank"
                            rel="noopener noreferrer">

                            View &amp; Apply

                        </a>
                    `

                    : `
                        <span class="apply-btn disabled">
                            Apply link unavailable
                        </span>
                    `
            }

        </div>
    `;
}


/* ==============================
   HELPERS
============================== */

function setText(id, value) {

    const element =
        document.getElementById(id);

    if (element) {
        element.textContent =
            value === undefined ||
            value === null
                ? ""
                : value;
    }
}


function setHtml(id, value) {

    const element =
        document.getElementById(id);

    if (element) {
        element.innerHTML =
            value || "";
    }
}


function showMessage(text, isError = false) {

    if (!message) {
        return;
    }

    message.style.color =
        isError
            ? "#dc2626"
            : "#475569";

    message.textContent =
        text;
}


function escapeHtml(value) {

    return String(
        value === undefined ||
        value === null
            ? ""
            : value
    )
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function safeUrl(url) {

    try {

        const parsed =
            new URL(url);

        if (
            parsed.protocol === "http:" ||
            parsed.protocol === "https:"
        ) {
            return parsed.href;
        }

        return "#";

    } catch (error) {

        return "#";
    }
}


function truncate(text, maxLength) {

    const value =
        String(text || "");

    if (value.length <= maxLength) {
        return value;
    }

    return value.substring(0, maxLength) + "...";
}


/* ==============================
   BACKEND STATUS CHECK
============================== */

(async function checkBackend() {

    const status =
        document.getElementById(
            "backendStatus"
        );

    if (!status) {
        return;
    }

    try {

        const base =
            await findBackend();

        status.className =
            "backend-status online";

        status.textContent =
            "● Connected to server at " +
            base;

    } catch (error) {

        status.className =
            "backend-status offline";

        status.textContent =
            "● Server not running. Run: python app.py";
    }

})();