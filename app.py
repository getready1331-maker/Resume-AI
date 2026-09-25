import hashlib
import io
import os
import random
import re
from urllib.parse import quote_plus

from flask import Flask, jsonify, request, send_from_directory

try:
    from flask_cors import CORS
except ImportError:
    CORS = None

from pypdf import PdfReader
import docx


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

MAX_FILE_MB = 5

# PDF, DOCX and TXT are supported.
# DOC is kept because your frontend currently allows it, but legacy .doc
# files are difficult to parse reliably without an additional library.
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt"}

APP_NAME = "resume-analyzer"
APP_VERSION = "1.3"


app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_MB * 1024 * 1024


if CORS:
    CORS(app)


# ============================================================================
# CORS
# ============================================================================

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/api/<path:_any>", methods=["OPTIONS"])
def preflight(_any):
    return ("", 204)


# ============================================================================
# SKILL DICTIONARY
# ============================================================================

SKILLS = {
    "Python": ["python"],
    "Java": ["java", "core java"],
    "C++": ["c++", "cpp"],
    "C": ["c programming"],
    "JavaScript": ["javascript", "java script", "es6"],
    "TypeScript": ["typescript"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3", "tailwind", "bootstrap"],
    "React": ["react", "react.js", "reactjs"],
    "Node.js": ["node", "node.js", "nodejs", "express"],
    "Angular": ["angular"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring Boot": ["spring", "spring boot"],
    "SQL": ["sql", "mysql", "postgres", "postgresql", "oracle db"],
    "MongoDB": ["mongodb", "mongo"],
    "Git": ["git", "github", "gitlab", "version control"],
    "REST API": ["rest api", "restful", "api development"],
    "Docker": ["docker", "container"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services", "ec2", "s3"],
    "Azure": ["azure"],
    "Linux": ["linux", "ubuntu", "shell scripting", "bash"],
    "CI/CD": ["ci/cd", "jenkins", "github actions"],
    "Machine Learning": [
        "machine learning",
        "scikit-learn",
        "scikit",
        "sklearn"
    ],
    "Deep Learning": [
        "deep learning",
        "neural network",
        "tensorflow",
        "pytorch",
        "keras"
    ],
    "NLP": ["nlp", "natural language processing"],
    "Data Analysis": [
        "data analysis",
        "pandas",
        "numpy",
        "data analytics"
    ],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "Excel": ["excel", "spreadsheet", "pivot table"],
    "Statistics": ["statistics", "statistical", "probability"],
    "Testing": [
        "software testing",
        "selenium",
        "junit",
        "pytest",
        "quality assurance",
        "qa"
    ],
    "Android": ["android", "kotlin"],
    "Flutter": ["flutter", "dart"],
    "iOS": ["swift", "ios development"],
    "UI/UX": [
        "ui/ux",
        "figma",
        "wireframe",
        "user experience",
        "user interface"
    ],
    "Cybersecurity": [
        "cyber security",
        "cybersecurity",
        "penetration testing",
        "owasp"
    ],
    "Networking": [
        "networking",
        "tcp/ip",
        "computer networks",
        "ccna"
    ],
    "Digital Marketing": [
        "digital marketing",
        "seo",
        "google ads",
        "social media marketing"
    ],
    "Content Writing": [
        "content writing",
        "copywriting",
        "blogging"
    ],
    "Accounting": [
        "accounting",
        "tally",
        "gst",
        "bookkeeping"
    ],
    "Sales": [
        "sales",
        "business development",
        "lead generation"
    ],
    "Human Resources": [
        "human resource",
        "human resources",
        "recruitment",
        "talent acquisition"
    ],
    "Communication": [
        "communication skills",
        "communication",
        "presentation skills"
    ],
    "Teamwork": [
        "teamwork",
        "team player",
        "collaboration"
    ],
    "Leadership": [
        "leadership",
        "team lead",
        "mentoring"
    ],
    "Problem Solving": [
        "problem solving",
        "analytical skills"
    ],
}


# ============================================================================
# JOB ROLES
# ============================================================================

ROLES = [
    {
        "id": "frontend",
        "title": "Frontend Developer",
        "core": ["HTML", "CSS", "JavaScript", "React"],
        "bonus": ["TypeScript", "Git", "UI/UX", "REST API"],
        "companies": [
            "Zoho",
            "Freshworks",
            "Swiggy",
            "Razorpay",
            "Infosys",
            "Zeta"
        ],
        "salary": ["₹4 - 12 LPA"]
    },

    {
        "id": "backend",
        "title": "Backend Developer",
        "core": ["Python", "SQL", "REST API"],
        "bonus": [
            "Django",
            "Flask",
            "Node.js",
            "Docker",
            "AWS",
            "Java",
            "Spring Boot"
        ],
        "companies": [
            "TCS",
            "Zoho",
            "PhonePe",
            "Groww",
            "Wipro",
            "Postman"
        ],
        "salary": ["₹5 - 15 LPA"]
    },

    {
        "id": "fullstack",
        "title": "Full Stack Developer",
        "core": ["HTML", "CSS", "JavaScript", "SQL"],
        "bonus": [
            "React",
            "Node.js",
            "Python",
            "MongoDB",
            "Git",
            "Docker"
        ],
        "companies": [
            "Accenture",
            "Cognizant",
            "Zerodha",
            "Meesho",
            "Tech Mahindra"
        ],
        "salary": ["₹5 - 16 LPA"]
    },

    {
        "id": "data-analyst",
        "title": "Data Analyst",
        "core": ["SQL", "Excel", "Data Analysis"],
        "bonus": [
            "Python",
            "Power BI",
            "Tableau",
            "Statistics"
        ],
        "companies": [
            "Deloitte",
            "EY India",
            "Flipkart",
            "HDFC Bank",
            "Mu Sigma"
        ],
        "salary": ["₹4 - 11 LPA"]
    },

    {
        "id": "data-scientist",
        "title": "Data Scientist / ML Engineer",
        "core": ["Python", "Machine Learning", "Statistics"],
        "bonus": [
            "Deep Learning",
            "NLP",
            "SQL",
            "Data Analysis",
            "AWS"
        ],
        "companies": [
            "Fractal Analytics",
            "Nvidia India",
            "Ola Krutrim",
            "Tiger Analytics"
        ],
        "salary": ["₹6 - 22 LPA"]
    },

    {
        "id": "devops",
        "title": "DevOps / Cloud Engineer",
        "core": ["Linux", "Docker", "AWS"],
        "bonus": [
            "Kubernetes",
            "CI/CD",
            "Git",
            "Azure",
            "Python"
        ],
        "companies": [
            "Nutanix",
            "Rakuten India",
            "HCLTech",
            "Persistent Systems"
        ],
        "salary": ["₹6 - 20 LPA"]
    },

    {
        "id": "mobile",
        "title": "Mobile App Developer",
        "core": ["Android", "Flutter"],
        "bonus": [
            "Java",
            "iOS",
            "REST API",
            "Git",
            "UI/UX"
        ],
        "companies": [
            "Dream11",
            "CRED",
            "Paytm",
            "MakeMyTrip",
            "Jupiter"
        ],
        "salary": ["₹4 - 14 LPA"]
    },

    {
        "id": "qa",
        "title": "QA / Test Engineer",
        "core": ["Testing"],
        "bonus": [
            "Java",
            "Python",
            "SQL",
            "Git",
            "CI/CD"
        ],
        "companies": [
            "Capgemini",
            "LTIMindtree",
            "Qualitest",
            "Infosys"
        ],
        "salary": ["₹3.5 - 10 LPA"]
    },

    {
        "id": "security",
        "title": "Cybersecurity Analyst",
        "core": ["Cybersecurity", "Networking"],
        "bonus": [
            "Linux",
            "Python",
            "AWS"
        ],
        "companies": [
            "Quick Heal",
            "Palo Alto India",
            "Wipro",
            "SISA"
        ],
        "salary": ["₹5 - 16 LPA"]
    },

    {
        "id": "uiux",
        "title": "UI/UX Designer",
        "core": ["UI/UX"],
        "bonus": [
            "HTML",
            "CSS",
            "Communication",
            "Problem Solving"
        ],
        "companies": [
            "Zomato",
            "Lenskart",
            "Myntra",
            "Obvious",
            "Cleartrip"
        ],
        "salary": ["₹4 - 13 LPA"]
    },

    {
        "id": "marketing",
        "title": "Digital Marketing Executive",
        "core": ["Digital Marketing"],
        "bonus": [
            "Content Writing",
            "Excel",
            "Communication",
            "Data Analysis"
        ],
        "companies": [
            "Nykaa",
            "boAt",
            "WebEngage",
            "Dentsu India"
        ],
        "salary": ["₹3 - 9 LPA"]
    },

    {
        "id": "hr",
        "title": "HR / Talent Acquisition",
        "core": ["Human Resources"],
        "bonus": [
            "Communication",
            "Excel",
            "Leadership"
        ],
        "companies": [
            "Naukri",
            "Randstad India",
            "TCS",
            "Adecco"
        ],
        "salary": ["₹3 - 8 LPA"]
    },

    {
        "id": "finance",
        "title": "Accounts & Finance Executive",
        "core": ["Accounting"],
        "bonus": [
            "Excel",
            "SQL",
            "Communication"
        ],
        "companies": [
            "ICICI Bank",
            "Zoho Books",
            "KPMG India",
            "Bajaj Finserv"
        ],
        "salary": ["₹3 - 9 LPA"]
    },

    {
        "id": "sales",
        "title": "Business Development Executive",
        "core": ["Sales"],
        "bonus": [
            "Communication",
            "Excel",
            "Digital Marketing"
        ],
        "companies": [
            "Zoho",
            "BYJU'S",
            "Udaan",
            "IndiaMART"
        ],
        "salary": ["₹3 - 10 LPA"]
    },
]


# ============================================================================
# CITIES
# ============================================================================

CITIES = [
    {"city": "Bengaluru", "state": "Karnataka", "zone": "South"},
    {"city": "Hyderabad", "state": "Telangana", "zone": "South"},
    {"city": "Chennai", "state": "Tamil Nadu", "zone": "South"},
    {"city": "Coimbatore", "state": "Tamil Nadu", "zone": "South"},
    {"city": "Kochi", "state": "Kerala", "zone": "South"},
    {"city": "Thiruvananthapuram", "state": "Kerala", "zone": "South"},
    {"city": "Mysuru", "state": "Karnataka", "zone": "South"},
    {"city": "Visakhapatnam", "state": "Andhra Pradesh", "zone": "South"},

    {"city": "Pune", "state": "Maharashtra", "zone": "West"},
    {"city": "Mumbai", "state": "Maharashtra", "zone": "West"},
    {"city": "Nagpur", "state": "Maharashtra", "zone": "West"},
    {"city": "Ahmedabad", "state": "Gujarat", "zone": "West"},
    {"city": "Surat", "state": "Gujarat", "zone": "West"},

    {"city": "Indore", "state": "Madhya Pradesh", "zone": "Central"},
    {"city": "Bhopal", "state": "Madhya Pradesh", "zone": "Central"},
    {"city": "Raipur", "state": "Chhattisgarh", "zone": "Central"},

    {"city": "New Delhi", "state": "Delhi", "zone": "North"},
    {"city": "Noida", "state": "Uttar Pradesh", "zone": "North"},
    {"city": "Gurugram", "state": "Haryana", "zone": "North"},
    {"city": "Lucknow", "state": "Uttar Pradesh", "zone": "North"},
    {"city": "Jaipur", "state": "Rajasthan", "zone": "North"},
    {"city": "Chandigarh", "state": "Punjab", "zone": "North"},
    {"city": "Dehradun", "state": "Uttarakhand", "zone": "North"},
    {"city": "Kanpur", "state": "Uttar Pradesh", "zone": "North"},

    {"city": "Kolkata", "state": "West Bengal", "zone": "East"},
    {"city": "Bhubaneswar", "state": "Odisha", "zone": "East"},
    {"city": "Patna", "state": "Bihar", "zone": "East"},
    {"city": "Ranchi", "state": "Jharkhand", "zone": "East"},

    {"city": "Guwahati", "state": "Assam", "zone": "North East"},

    {"city": "Remote (India)", "state": "Work from home", "zone": "Remote"},
]


JOB_TYPES = [
    "Full Time",
    "Internship",
    "Contract",
    "Hybrid"
]

EXPERIENCE = [
    "0 - 1 yrs",
    "0 - 2 yrs",
    "1 - 3 yrs",
    "2 - 5 yrs",
    "3 - 6 yrs"
]

POSTED = [
    "Today",
    "1 day ago",
    "2 days ago",
    "4 days ago",
    "1 week ago",
    "2 weeks ago"
]


# ============================================================================
# TEXT EXTRACTION
# ============================================================================

def extract_text(file_storage):
    """
    Extract readable text from PDF, DOCX, DOC or TXT.
    """

    name = (file_storage.filename or "").lower()

    if "." not in name:
        raise ValueError(
            "The file has no extension. Please upload a PDF or DOCX resume."
        )

    extension = name.rsplit(".", 1)[-1]

    raw = file_storage.read()

    if not raw:
        raise ValueError("The uploaded file is empty.")

    # ---------------- PDF ----------------

    if extension == "pdf":

        try:
            reader = PdfReader(io.BytesIO(raw))

            pages = []

            for page in reader.pages:
                page_text = page.extract_text() or ""
                pages.append(page_text)

            text = "\n".join(pages)

        except Exception:
            raise ValueError(
                "The PDF could not be read. Please upload a valid PDF resume."
            )

    # ---------------- DOCX ----------------

    elif extension == "docx":

        try:
            document = docx.Document(io.BytesIO(raw))

            parts = []

            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    parts.append(paragraph.text)

            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            parts.append(cell.text)

            text = "\n".join(parts)

        except Exception:
            raise ValueError(
                "The DOCX file could not be read. Please upload a valid DOCX resume."
            )

    # ---------------- TXT ----------------

    elif extension == "txt":

        text = raw.decode("utf-8", errors="ignore")

    # ---------------- DOC ----------------

    elif extension == "doc":

        # Old .doc files are binary Word files.
        # This method extracts readable characters where possible.
        decoded = raw.decode("utf-8", errors="ignore")

        text = re.sub(
            r"[^\x20-\x7E\n]+",
            " ",
            decoded
        )

    else:

        raise ValueError(
            "Unsupported file type. Please upload PDF, DOC or DOCX."
        )

    # Clean text

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    text = text.strip()

    if len(text) < 40:

        raise ValueError(
            "Very little readable text was found in this file. "
            "If this is a scanned resume, use a text-based PDF or DOCX."
        )

    return text


# ============================================================================
# RESUME VALIDATION
# ============================================================================

# These are strong indicators that a document is a resume/CV.
RESUME_SECTION_KEYWORDS = {
    "education": [
        "education",
        "academic qualification",
        "academic qualifications",
        "qualification",
        "qualifications",
        "degree",
        "university",
        "college"
    ],

    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "internship",
        "internships",
        "work history"
    ],

    "skills": [
        "skills",
        "technical skills",
        "technical skill",
        "core skills",
        "competencies",
        "technologies",
        "programming languages"
    ],

    "projects": [
        "projects",
        "project",
        "academic projects",
        "personal projects",
        "major project"
    ],

    "contact": [
        "email",
        "phone",
        "mobile",
        "linkedin",
        "github",
        "contact"
    ],

    "profile": [
        "objective",
        "career objective",
        "profile",
        "professional summary",
        "summary",
        "about me"
    ],

    "certifications": [
        "certification",
        "certifications",
        "certificate",
        "certificates"
    ],

    "achievements": [
        "achievement",
        "achievements",
        "awards",
        "honors",
        "activities"
    ]
}


def normalize_text(text):
    """
    Make text easier to validate.
    """

    text = text.lower()

    # Replace unusual spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def count_resume_sections(text):
    """
    Count how many different resume sections appear in the document.
    """

    lowered = normalize_text(text)

    section_results = {}

    for section, keywords in RESUME_SECTION_KEYWORDS.items():

        found = False

        for keyword in keywords:

            if keyword in lowered:
                found = True
                break

        section_results[section] = found

    return section_results


def has_contact_information(text):
    """
    Detect common email/phone/contact patterns.
    """

    email_found = bool(
        re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text
        )
    )

    phone_found = bool(
        re.search(
            r"(?:\+91[\s-]?)?[6-9]\d{9}",
            text
        )
    )

    linkedin_found = "linkedin" in text.lower()

    github_found = "github" in text.lower()

    return (
        email_found
        or phone_found
        or linkedin_found
        or github_found
    )


def resume_validation(text):
    """
    Decide whether the uploaded document looks like a resume.

    Returns:
        {
            "valid": True/False,
            "score": number,
            "sections": [...],
            "reason": "..."
        }
    """

    lowered = normalize_text(text)

    words = len(lowered.split())

    if words < 60:

        return {
            "valid": False,
            "score": 0,
            "sections": [],
            "reason": (
                "The uploaded document is too short to be a complete resume."
            )
        }

    section_results = count_resume_sections(lowered)

    found_sections = [
        section
        for section, found in section_results.items()
        if found
    ]

    score = 0

    # Resume section evidence

    score += len(found_sections) * 10

    # Contact information

    if has_contact_information(text):
        score += 15

    # Technical/skill evidence

    detected_skills = find_skills(text)

    if len(detected_skills) >= 2:
        score += 10

    if len(detected_skills) >= 5:
        score += 5

    # Resume-specific words

    resume_identity_words = [
        "resume",
        "curriculum vitae",
        "cv",
        "career objective",
        "professional summary",
        "work experience",
        "technical skills",
        "education",
        "projects"
    ]

    identity_hits = sum(
        1
        for keyword in resume_identity_words
        if keyword in lowered
    )

    score += min(identity_hits * 5, 20)

    # Common report/document indicators.
    # These don't automatically reject a file, because some resumes
    # can contain these words too.
    report_indicators = [
        "chapter",
        "table of contents",
        "abstract",
        "references",
        "methodology",
        "literature review",
        "conclusion",
        "question",
        "assignment",
        "experiment",
        "research paper"
    ]

    report_hits = sum(
        1
        for keyword in report_indicators
        if keyword in lowered
    )

    # Strong resume evidence should outweigh a single generic word.
    # But a report with many report indicators and almost no resume
    # structure should be rejected.
    if report_hits >= 4 and len(found_sections) <= 2:
        score -= 30

    # Strong minimum criteria.
    #
    # A normal report might contain "education" or "skills" once.
    # Requiring several different resume signals prevents that.
    valid = False

    if len(found_sections) >= 4:
        valid = True

    elif len(found_sections) >= 3 and has_contact_information(text):
        valid = True

    elif (
        len(found_sections) >= 3
        and len(detected_skills) >= 3
        and words >= 100
    ):
        valid = True

    elif (
        "resume" in lowered
        or "curriculum vitae" in lowered
        or re.search(r"\bcv\b", lowered)
    ) and len(found_sections) >= 2:
        valid = True

    # Reject obvious report-like documents with weak resume evidence.
    if report_hits >= 5 and len(found_sections) < 4:
        valid = False

    # Final score bounds
    score = max(0, min(score, 100))

    if valid:

        reason = (
            "The document contains multiple resume-related sections "
            "and appears to be a valid resume."
        )

    else:

        reason = (
            "This document does not contain enough resume-related "
            "information. Please upload a CV or resume containing "
            "sections such as Education, Skills, Experience or Projects."
        )

    return {
        "valid": valid,
        "score": score,
        "sections": found_sections,
        "reason": reason
    }


# ============================================================================
# SKILL DETECTION
# ============================================================================

def _compile_patterns():

    compiled = {}

    for skill, aliases in SKILLS.items():

        parts = []

        for alias in aliases:

            alias = alias.strip()

            if alias:
                parts.append(re.escape(alias))

        if not parts:
            continue

        compiled[skill] = re.compile(
            r"(?<![a-z0-9+#])(?:"
            + "|".join(parts)
            + r")(?![a-z0-9+#])",
            re.IGNORECASE
        )

    return compiled


SKILL_PATTERNS = _compile_patterns()


def find_skills(text):

    found = []

    for skill, pattern in SKILL_PATTERNS.items():

        if pattern.search(text):
            found.append(skill)

    return sorted(found)


# ============================================================================
# CAREER MATCHING
# ============================================================================

def match_roles(found_skills):

    skill_set = set(found_skills)

    scored = []

    for role in ROLES:

        core_hits = [
            skill
            for skill in role["core"]
            if skill in skill_set
        ]

        bonus_hits = [
            skill
            for skill in role["bonus"]
            if skill in skill_set
        ]

        core_ratio = (
            len(core_hits) /
            max(len(role["core"]), 1)
        )

        bonus_ratio = (
            len(bonus_hits) /
            max(len(role["bonus"]), 1)
        )

        score = round(
            (core_ratio * 70) +
            (bonus_ratio * 30)
        )

        if score > 0:

            missing = [
                skill
                for skill in role["core"] + role["bonus"]
                if skill not in skill_set
            ]

            scored.append(
                {
                    "role": role,
                    "score": max(
                        35,
                        min(score, 98)
                    ),
                    "matched": core_hits + bonus_hits,
                    "missing": missing
                }
            )

    scored.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return scored


# ============================================================================
# RESUME SCORE
# ============================================================================

def score_resume(text, found_skills):

    lowered = text.lower()

    words = len(text.split())

    skill_points = min(
        len(found_skills) * 4,
        45
    )

    sections = {

        "education": [
            "education",
            "b.tech",
            "bachelor",
            "degree",
            "university",
            "college"
        ],

        "experience": [
            "experience",
            "intern",
            "worked",
            "employment"
        ],

        "projects": [
            "project",
            "built",
            "developed",
            "created"
        ],

        "contact": [
            "@",
            "phone",
            "mobile",
            "linkedin",
            "+91"
        ]
    }

    section_points = 0

    missing_sections = []

    for name, keywords in sections.items():

        if any(
            keyword in lowered
            for keyword in keywords
        ):

            section_points += 5

        else:

            missing_sections.append(name)

    action_words = [
        "developed",
        "designed",
        "implemented",
        "managed",
        "led",
        "improved",
        "created",
        "optimized",
        "built",
        "achieved",
        "delivered",
        "automated"
    ]

    action_count = sum(
        1
        for word in action_words
        if word in lowered
    )

    action_points = min(
        action_count * 2,
        15
    )

    numbers_points = 10 if re.search(
        r"\d+\s*%|\d{2,}\+|\d+\s*(users|projects|students)",
        lowered
    ) else 0

    if words >= 550:

        length_points = 10

    elif words >= 300:

        length_points = 8

    elif words >= 150:

        length_points = 5

    else:

        length_points = 2

    total = (
        skill_points +
        section_points +
        action_points +
        numbers_points +
        length_points
    )

    if words < 150:
        total = min(total, 70)

    elif words < 250:
        total = min(total, 85)

    breakdown = [

        {
            "label": "Skills & keywords",
            "score": skill_points,
            "max": 45
        },

        {
            "label": "Resume sections",
            "score": section_points,
            "max": 20
        },

        {
            "label": "Action words",
            "score": action_points,
            "max": 15
        },

        {
            "label": "Measurable results",
            "score": numbers_points,
            "max": 10
        },

        {
            "label": "Length & detail",
            "score": length_points,
            "max": 10
        }
    ]

    return (
        min(total, 100),
        breakdown,
        missing_sections,
        words
    )


# ============================================================================
# SUGGESTIONS
# ============================================================================

def build_suggestions(
    score,
    found_skills,
    missing_sections,
    top_matches,
    words
):

    tips = []

    if "experience" in missing_sections:

        tips.append(
            "Add an Experience or Internship section, "
            "including academic or freelance work."
        )

    if "projects" in missing_sections:

        tips.append(
            "List 2-3 projects with the tools used "
            "and what each project achieved."
        )

    if "contact" in missing_sections:

        tips.append(
            "Add your email, phone number and LinkedIn URL "
            "at the top of the resume."
        )

    if "education" in missing_sections:

        tips.append(
            "Add your education with degree, institute "
            "and year of passing."
        )

    if len(found_skills) < 8:

        tips.append(
            "Create a clear Skills section listing "
            "your tools, technologies and programming languages."
        )

    if words < 250:

        tips.append(
            "Your resume is short. Describe each project "
            "or experience in 2-3 bullet points."
        )

    elif words > 900:

        tips.append(
            "Consider reducing unnecessary content "
            "and keeping the resume concise."
        )

    tips.append(
        "Use measurable results in bullet points, "
        "such as percentages, numbers or project impact."
    )

    if top_matches:

        gap = top_matches[0]["missing"][:3]

        if gap:

            tips.append(
                "For "
                + top_matches[0]["role"]["title"]
                + " roles, consider learning "
                + ", ".join(gap)
                + "."
            )

    tips.append(
        "Save your final resume as PDF to preserve formatting."
    )

    if score >= 80:

        tips.insert(
            0,
            "Your resume contains strong resume signals. "
            "Tailor the summary for each job."
        )

    return tips[:7]


# ============================================================================
# JOB LINKS
# ============================================================================

def apply_link(title, city):

    if city.startswith("Remote"):

        return (
            "https://www.naukri.com/"
            + quote_plus(
                title.lower().replace(" ", "-")
            )
            + "-jobs?wfhType=2"
        )

    return (
        "https://www.naukri.com/jobs-in-"
        + quote_plus(
            city.lower().replace(" ", "-")
        )
        + "?keyword="
        + quote_plus(title)
    )


# ============================================================================
# JOB GENERATION
# ============================================================================

def make_job(
    role,
    place,
    position,
    base_score,
    skill_set,
    rng
):

    requirements = (
        role["core"] +
        role["bonus"][:2]
    )

    match_score = max(
        40,
        min(
            98,
            base_score + rng.randint(-6, 6)
        )
    )

    return {

        "id": role["id"] + "-" + str(position),

        "role_id": role["id"],

        "title": role["title"],

        "company": role["companies"][
            position % len(role["companies"])
        ],

        "location": (
            place["city"]
            + ", "
            + place["state"]
        ),

        "city": place["city"],

        "state": place["state"],

        "zone": place["zone"],

        "job_type": rng.choice(JOB_TYPES),

        "experience": rng.choice(EXPERIENCE),

        "salary": role["salary"],

        "posted": rng.choice(POSTED),

        "match_score": match_score,

        "matched_skills": [
            skill
            for skill in requirements
            if skill in skill_set
        ],

        "requirements": requirements,

        "apply_url": apply_link(
            role["title"],
            place["city"]
        )
    }


def build_jobs(
    top_matches,
    found_skills,
    per_role=6,
    only_cities=None
):

    jobs = []

    skill_set = set(found_skills)

    for match in top_matches:

        role = match["role"]

        seed = int(
            hashlib.md5(
                role["id"].encode()
            ).hexdigest()[:8],
            16
        )

        rng = random.Random(
            seed + len(found_skills)
        )

        pool = (
            only_cities
            if only_cities
            else CITIES
        )

        if only_cities:

            places = list(pool)

        else:

            places = rng.sample(
                pool,
                k=min(
                    per_role,
                    len(pool)
                )
            )

        for position, place in enumerate(places):

            jobs.append(
                make_job(
                    role,
                    place,
                    position,
                    match["score"],
                    skill_set,
                    rng
                )
            )

    jobs.sort(
        key=lambda job: job["match_score"],
        reverse=True
    )

    return jobs


def city_summary(jobs):

    counts = {}

    for job in jobs:

        key = (
            job["city"],
            job["state"],
            job["zone"]
        )

        counts[key] = (
            counts.get(key, 0) + 1
        )

    summary = [

        {
            "city": city,
            "state": state,
            "zone": zone,
            "openings": openings
        }

        for (
            city,
            state,
            zone
        ), openings in counts.items()
    ]

    summary.sort(
        key=lambda item: (
            -item["openings"],
            item["city"]
        )
    )

    return summary


# ============================================================================
# ROUTES
# ============================================================================

@app.route("/")
def home():

    return send_from_directory(
        STATIC_DIR,
        "index.html"
    )


@app.route("/<path:filename>")
def static_files(filename):

    return send_from_directory(
        STATIC_DIR,
        filename
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route("/api/health")
def health():

    return jsonify(
        {
            "status": "ok",
            "app": APP_NAME,
            "version": APP_VERSION,
            "roles": len(ROLES),
            "cities": len(CITIES)
        }
    )


# ============================================================================
# ANALYZE RESUME
# ============================================================================

@app.route("/api/analyze", methods=["POST"])
def analyze():

    # ------------------------------------------------------------
    # 1. Check uploaded file
    # ------------------------------------------------------------

    if "resume" not in request.files:

        return jsonify(
            {
                "success": False,
                "error": "No file was uploaded."
            }
        ), 400

    uploaded = request.files["resume"]

    if not uploaded.filename:

        return jsonify(
            {
                "success": False,
                "error": "No file was selected."
            }
        ), 400

    extension = (
        uploaded.filename
        .rsplit(".", 1)[-1]
        .lower()
    )

    if extension not in ALLOWED_EXTENSIONS:

        return jsonify(
            {
                "success": False,
                "error": (
                    "Invalid file type. "
                    "Please upload a PDF, DOC or DOCX resume."
                )
            }
        ), 400

    # ------------------------------------------------------------
    # 2. Extract text
    # ------------------------------------------------------------

    try:

        text = extract_text(uploaded)

    except ValueError as err:

        return jsonify(
            {
                "success": False,
                "error": str(err)
            }
        ), 400

    except Exception:

        app.logger.exception(
            "Text extraction failed"
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    "This file could not be read. "
                    "Please upload a valid resume."
                )
            }
        ), 400

    # ------------------------------------------------------------
    # 3. IMPORTANT:
    #    Validate that the document is actually a resume
    # ------------------------------------------------------------

    validation = resume_validation(text)

    if not validation["valid"]:

        return jsonify(
            {
                "success": False,

                "is_resume": False,

                "error": (
                    "This file does not appear to be a resume."
                ),

                "message": validation["reason"],

                "validation": {
                    "score": validation["score"],
                    "sections_found": validation["sections"]
                }
            }
        ), 400

    # ------------------------------------------------------------
    # 4. Analyze ONLY after resume validation succeeds
    # ------------------------------------------------------------

    try:

        found = find_skills(text)

        matches = match_roles(found)

        score, breakdown, missing_sections, words = (
            score_resume(
                text,
                found
            )
        )

        jobs = build_jobs(
            matches[:6],
            found,
            per_role=6
        )

    except Exception as err:

        app.logger.exception(
            "Analysis failed"
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    "Analysis error: "
                    + str(err)
                )
            }
        ), 500

    # ------------------------------------------------------------
    # 5. Career recommendation
    # ------------------------------------------------------------

    if matches:

        best = matches[0]["role"]["title"]

        to_improve = (
            matches[0]["missing"][:8]
        )

        if not to_improve:

            extra = []

            for nxt in matches[1:4]:

                for skill in nxt["missing"]:

                    if skill not in extra:
                        extra.append(skill)

            to_improve = extra[:6]

    else:

        best = "Entry Level Roles"

        # These are only general improvement areas.
        # They are NOT used for fake analysis.
        to_improve = [
            "Python",
            "SQL",
            "Communication",
            "Excel"
        ]

    # ------------------------------------------------------------
    # 6. Summary
    # ------------------------------------------------------------

    summary = (
        "We found "
        + str(len(found))
        + " skills in your resume. "
        + "The closest career match is "
        + best
        + ", and "
        + str(len(jobs))
        + " job listings are available "
        + "across "
        + str(
            len(
                {
                    job["city"]
                    for job in jobs
                }
            )
        )
        + " cities in India."
    )

    # ------------------------------------------------------------
    # 7. Final response
    # ------------------------------------------------------------

    return jsonify(
        {

            "success": True,

            "is_resume": True,

            "resume_validation": {
                "score": validation["score"],
                "sections_found": validation["sections"]
            },

            "resume_score": score,

            "score_breakdown": breakdown,

            "word_count": words,

            "summary": summary,

            "skills_found": found,

            "skills_to_improve": to_improve,

            "suggestions": build_suggestions(
                score,
                found,
                missing_sections,
                matches,
                words
            ),

            "career_matches": [

                {
                    "title": m["role"]["title"],

                    "match_score": m["score"],

                    "salary": m["role"]["salary"],

                    "matched_skills": (
                        m["matched"][:6]
                    )
                }

                for m in matches[:5]
            ],

            "jobs": jobs,

            "cities": city_summary(jobs),

            "total_jobs": len(jobs)
        }
    )


# ============================================================================
# JOB API
# ============================================================================

@app.route("/api/jobs")
def jobs_across_india():

    city = (
        request.args.get("city")
        or ""
    ).strip().lower()

    role_id = (
        request.args.get("role")
        or ""
    ).strip().lower()

    zone = (
        request.args.get("zone")
        or ""
    ).strip().lower()

    matches = [

        {
            "role": role,
            "score": 70,
            "matched": [],
            "missing": []
        }

        for role in ROLES

        if (
            not role_id
            or role["id"] == role_id
        )
    ]

    if not matches:

        return jsonify(
            {
                "success": False,
                "error": "Unknown role id."
            }
        ), 400

    pool = CITIES

    if city:

        pool = [
            c
            for c in CITIES
            if city in c["city"].lower()
        ]

    if zone:

        pool = [
            c
            for c in pool
            if zone == c["zone"].lower()
        ]

    if not pool:

        return jsonify(
            {
                "success": True,
                "total_jobs": 0,
                "jobs": [],
                "cities": []
            }
        )

    jobs = build_jobs(
        matches,
        [],
        per_role=6,
        only_cities=(
            pool
            if city or zone
            else None
        )
    )

    return jsonify(
        {
            "success": True,
            "total_jobs": len(jobs),
            "jobs": jobs,
            "cities": city_summary(jobs)
        }
    )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(413)
def too_large(_):

    return jsonify(
        {
            "success": False,
            "error": (
                "File is larger than "
                + str(MAX_FILE_MB)
                + " MB."
            )
        }
    ), 413


@app.errorhandler(404)
def not_found(_):

    return jsonify(
        {
            "success": False,
            "error": (
                "That address does not exist "
                "on this server."
            )
        }
    ), 404


@app.errorhandler(405)
def bad_method(_):

    return jsonify(
        {
            "success": False,
            "error": (
                "Wrong request method for this address."
            )
        }
    ), 405


@app.errorhandler(500)
def server_error(_):

    return jsonify(
        {
            "success": False,
            "error": (
                "The server hit an unexpected error. "
                "Check the terminal."
            )
        }
    ), 500


# ============================================================================
# PORT
# ============================================================================

def free_port(preferred=5000):

    import socket

    for port in (
        preferred,
        5001,
        5050,
        8000
    ):

        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        ) as probe:

            if probe.connect_ex(
                ("127.0.0.1", port)
            ) != 0:

                return port

    return 0


# ============================================================================
# START SERVER
# ============================================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT")
        or free_port()
    )

    print("")
    print("=" * 45)
    print("       AI RESUME ANALYZER")
    print("=" * 45)
    print("")
    print(
        "Open in browser: "
        "http://127.0.0.1:"
        + str(port)
    )
    print("")
    print(
        "Health check: "
        "http://127.0.0.1:"
        + str(port)
        + "/api/health"
    )
    print("")
    print(
        "Keep this terminal open "
        "while using the application."
    )
    print("")

    debug = (
        os.environ.get("FLASK_DEBUG")
        == "1"
    )

    app.run(
        debug=debug,
        host="127.0.0.1",
        port=port
    )