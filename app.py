import streamlit as st
import pdfplumber
import re
import requests
import sqlite3
import json
import time
import pandas as pd
import base64

def get_base64_image(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

st.set_page_config(page_title="JobFit", page_icon="🎯", layout="wide")

st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        html, body, .stApp {
            overscroll-behavior-y: contain;
        }
        div[data-testid="stFileUploaderDropzone"] {
            padding: 6px;
        }
        div[data-testid="stAlert"] {
            padding: 8px 12px;
        }
        div[data-testid="stVerticalBlock"] > div {
            gap: 1rem;
        }
        div.stButton {
            display: flex;
            justify-content: center;
        }
        div[data-testid="stTextArea"] textarea {
            min-height: 50px !important;
            height: 50px !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 1.5rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        li[role="option"]:hover {
            background-color: #14B8A6 !important;
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

def section_header(title):
    st.markdown(f"""
        <div style="background-color:#0F766E; color:white; padding:10px 16px; 
                    border-radius:8px; margin-bottom:12px; 
                    font-size:18px; font-weight:600;">
            {title}
        </div>
    """, unsafe_allow_html=True)

st.markdown('<h1 style="color:#0F766E;">JobFit</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#4B5563; font-size:17px; margin-top:-8px;">See live job openings that match your resume, plus what skills you\'re missing.</p>', unsafe_allow_html=True)

# --- Section 1: PDF Text Extraction ---
def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# --- Section 1.5: Section Splitting ---
section_headers = {
    "summary": ["summary", "professional summary", "profile", "professional profile",
                "career objective", "objective", "about me", "career summary"],
    "skills": ["skills", "technical skills", "core skills", "key skills",
               "skills & abilities", "technical proficiencies", "competencies", "areas of expertise"],
    "experience": ["experience", "work experience", "professional experience",
                   "employment history", "work history"],
    "projects": ["projects", "academic projects", "personal projects", "key projects", "academic work", "selected projects"],
    "education": ["education", "academic background", "qualifications"],
    "certifications": ["certifications", "certificates", "licenses & certifications"],
}

def split_resume_sections(resume_text, section_headers_dict):
    lines = resume_text.split("\n")
    sections = {key: "" for key in section_headers_dict}
    current_section = None
    
    for line in lines:
        clean_line = line.strip().lower()
        matched_section = None
        for section_name, variants in section_headers_dict.items():
            if clean_line in variants:
                matched_section = section_name
                break
        
        if matched_section:
            current_section = matched_section
            continue
        
        if current_section:
            sections[current_section] += line + "\n"
    
    return sections

# --- Section 2: Skill Extraction ---
role_skills = {
    "Data Analyst": ["SQL", "Excel", "Python", "Tableau", "Power BI", "Statistical Analysis", "Data Cleaning", "Google Analytics", "Dashboarding", "Data Visualization"],
    "Data Scientist": ["Python", "R", "SQL", "Machine Learning", "pandas", "NumPy", "Git", "Scikit-learn", "Data Visualization"],
    "Data Engineer": ["Python", "SQL", "ETL", "Relational Databases", "Git", "Linux", "Bash", "Data Warehousing", "SQL Server"],
    "Software Developer": ["Java", "Python", "Data Structures", "Algorithms", "Git", "GitHub", "OOP", "SQL", "HTML5", "CSS3", "REST API", "NoSQL", "Linux"],
    "Web Developer": ["HTML5", "CSS3", "JavaScript", "TypeScript", "React", "Git", "GitHub", "Responsive Design", "REST API", "Vue.js"],
    "UI/UX Designer": ["Figma", "Adobe XD", "Wireframing", "Prototyping", "Typography", "Color Theory", "User Research", "UI Components", "Design Systems", "HTML", "CSS"],
    "QA / Testing": ["Manual Testing", "Jira", "Test Case Writing", "SQL", "Git", "Selenium", "Postman", "JUnit", "TestNG"],
    "DevOps": ["Linux", "Git", "GitHub", "Docker", "AWS", "Bash", "CI/CD", "Networking"],
    "Mobile App Developer": ["Swift", "Kotlin", "Flutter", "React Native", "Git", "REST API", "Firebase", "Java"],
}

def normalize(text):
    text = text.lower()
    text = re.sub(r'[-_]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_skills(sections_dict, roles_skills_dict):
    combined_text = (sections_dict["skills"] + " " + sections_dict["summary"] + " " + sections_dict["projects"] + " " + sections_dict["experience"]) + " " + sections_dict["certifications"]
    norm_resume = normalize(combined_text)
    found_skills = {}
    for role, skills in roles_skills_dict.items():
        matched = []
        for skill in skills:
            norm_skill = normalize(skill)
            pattern = r'\b' + re.escape(norm_skill) + r's?\b'
            if re.search(pattern, norm_resume):
                matched.append(skill)
        found_skills[role] = matched
    return found_skills

def extract_skills_for_role(sections_dict, skill_list):
    combined_text = (sections_dict["skills"] + " " + sections_dict["summary"] + " " +
                      sections_dict["projects"] + " " + sections_dict["experience"] + " " +
                      sections_dict["certifications"])
    norm_resume = normalize(combined_text)
    matched = []
    for skill in skill_list:
        norm_skill = normalize(skill)
        pattern = r'\b' + re.escape(norm_skill) + r's?\b'
        if re.search(pattern, norm_resume):
            matched.append(skill)
    return matched

# --- Section 3: Role Scoring ---
def score_roles(matched_skills_dict, role_skills_dict):
    scores = {}
    for role, matched in matched_skills_dict.items():
        total_skills = len(role_skills_dict[role])
        match_pct = (len(matched) / total_skills) * 100 if total_skills > 0 else 0
        scores[role] = round(match_pct, 1)
    
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked

# --- Section 5: Determine Roles to Search ---
def determine_roles_to_search(ranked_scores, gap_threshold=25, min_threshold=40):
    if not ranked_scores:
        return []
    top_role, top_score = ranked_scores[0]
    selected = [(top_role, top_score)]
    for role, score in ranked_scores[1:]:
        if score >= min_threshold and (top_score - score) <= gap_threshold:
            selected.append((role, score))
        else:
            break
    return selected

# --- Section 5.5: Level Detection ---
senior_skills = {
    "Data Analyst": ["Advanced SQL", "BigQuery", "Snowflake", "Generative AI", "Predictive Modeling", "Data Governance", "Executive Dashboarding", "Looker", "SAS", "R", "Data Warehousing", "ETL"],
    "Data Scientist": ["Deep Learning", "PyTorch", "TensorFlow", "LLM", "MLOps", "Spark", "AWS", "GCP", "NLP", "Computer Vision", "Data Mining", "SQL Server", "ML Pipelines"],
    "Data Engineer": ["Apache Spark", "Snowflake", "BigQuery", "dbt", "AWS", "Azure", "GCP", "Airflow", "Kafka", "PySpark", "Azure Data Factory", "Redshift", "Presto", "Scala", "Data Mesh"],
    "Software Developer": ["System Design", "Docker", "Kubernetes", "Microservices", "GitHub Copilot", "CI/CD", "AWS", "Azure", "C#", "C++", "Go", "Agile", "System Architecture", "Tech Stack Migration"],
    "Web Developer": ["Next.js", "Remix", "Node.js", "Full-Stack Architecture", "Web Performance", "Vercel", "OWASP", "Angular", "Express.js", "MongoDB", "PostgreSQL", "GraphQL", "Webpack", "Serverless"],
    "UI/UX Designer": ["Advanced Design Systems", "Interaction Design", "AI Design Tools", "Usability Testing", "Product Strategy", "Cross-Functional Collaboration", "Design Ops", "Adobe Illustrator", "InVision", "Information Architecture", "Prototyping", "Miro"],
    "QA / Testing": ["Playwright", "Cypress", "Test Automation Frameworks", "CI/CD", "Performance Testing", "API Automation Testing", "Security Testing", "Appium", "Cucumber", "Bugzilla", "API Testing", "Regression Testing"],
    "DevOps": ["Kubernetes", "Terraform", "CI/CD", "Prometheus", "Grafana", "Cloud-Native", "DevSecOps", "Ansible", "Jenkins", "Azure DevOps", "GCP", "Python", "Helm", "CloudFormation", "SRE"],
    "Mobile App Developer": ["Mobile System Architecture", "App Store Publishing", "Mobile DevOps", "App Performance Optimization", "Native-to-Cross-Platform Bridges", "Mobile Security", "Offline-First Architecture", "Objective-C", "Jetpack Compose", "SwiftUI", "CI/CD", "App Store Connect", "Play Console"],
}
hybrid_roles = {
    "Data Analyst": "Data Scientist",
    "Data Scientist": "Data Analyst",
}

def get_combined_skill_list(role, skill_list_dict, senior_dict, level):
    base_list = skill_list_dict[role].copy()
    if role in hybrid_roles:
        base_list += skill_list_dict[hybrid_roles[role]]
    if level == "experienced":
        base_list += senior_dict.get(role, [])
        if role in hybrid_roles:
            base_list += senior_dict.get(hybrid_roles[role], [])
    return list(set(base_list))  # remove any duplicates

def detect_level(sections_dict, role, senior_skills_dict):
    exp_text = sections_dict["experience"].strip().lower()
    is_internship_only = bool(exp_text) and "intern" in exp_text and not any(
        word in exp_text for word in ["full-time", "full time", "permanent"]
    )
    has_real_experience = bool(exp_text) and not is_internship_only
    
    combined_text = sections_dict["skills"] + " " + sections_dict["summary"] + " " + sections_dict["projects"] + " " + sections_dict["experience"] + " " + sections_dict["certifications"]
    norm_resume = normalize(combined_text)
    
    senior_matches = []
    for skill in senior_skills_dict.get(role, []):
        norm_skill = normalize(skill)
        pattern = r'\b' + re.escape(norm_skill) + r'\b'
        if re.search(pattern, norm_resume):
            senior_matches.append(skill)
    
    if not has_real_experience and len(senior_matches) < 2:
        return "entry level"
    return "experienced"

# --- Section 6: API Calls ---
adzuna_app_id = st.secrets["ADZUNA_APP_ID"]
adzuna_app_key = st.secrets["ADZUNA_APP_KEY"]
jooble_key = st.secrets["JOOBLE_KEY"]

def get_adzuna_jobs(role, city, level, app_id, app_key):
    url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
    if level == "entry level":
        exclude_terms = "senior,lead,manager,principal,sr"
    else:
        exclude_terms = "fresher,intern,entry level,trainee,junior"
    params = {
        "app_id": app_id, "app_key": app_key, "title_only": role,
        "what_exclude": exclude_terms, "where": city, "results_per_page": 20
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json().get("results", [])
    except Exception:
        return []
    jobs = []
    for job in data:
        jobs.append({
            "title": job.get("title", ""),
            "company": job.get("company", {}).get("display_name", "Unknown"),
            "location": job.get("location", {}).get("display_name", "Unknown"),
            "salary": job.get("salary_min"),
            "description": job.get("description", ""),
            "apply_link": job.get("redirect_url", ""),
            "source": "Adzuna"
        })
    return jobs

def get_jooble_jobs(role, city, level, jooble_key):
    if level == "entry level":
        exclude_suffix = " -senior -lead -manager -principal"
    else:
        exclude_suffix = " -fresher -intern -trainee -junior"
    url = f"https://jooble.org/api/{jooble_key}"
    payload = {"keywords": role + exclude_suffix, "location": city}
    response = requests.post(url, json=payload)
    data = response.json().get("jobs", [])
    jobs = []
    for job in data:
        jobs.append({
            "title": job.get("title", ""),
            "company": job.get("company", "Unknown"),
            "location": job.get("location", "Unknown"),
            "salary": job.get("salary"),
            "description": job.get("snippet", ""),
            "apply_link": job.get("link", ""),
            "source": "Jooble"
        })
    return jobs

def init_cache_db():
    conn = sqlite3.connect("job_cache.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_cache (
            role TEXT, city TEXT, level TEXT, results TEXT, timestamp REAL,
            PRIMARY KEY (role, city, level)
        )
    """)
    conn.commit()
    conn.close()

def get_cached_results(role, city, level, max_age_hours=2):
    conn = sqlite3.connect("job_cache.db")
    cursor = conn.cursor()
    cursor.execute("SELECT results, timestamp FROM job_cache WHERE role=? AND city=? AND level=?", (role, city, level))
    row = cursor.fetchone()
    conn.close()
    if row:
        results_json, saved_time = row
        age_hours = (time.time() - saved_time) / 3600
        if age_hours < max_age_hours:
            return json.loads(results_json)
    return None

def save_to_cache(role, city, level, results):
    conn = sqlite3.connect("job_cache.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO job_cache (role, city, level, results, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (role, city, level, json.dumps(results), time.time()))
    conn.commit()
    conn.close()

# --- Section 7: Merge & Dedupe ---
def merge_and_clean(jobs_list):
    vague_names = ["reputed company", "confidential", "leading mnc", "top company", "unknown"]
    seen = set()
    cleaned_jobs = []
    for job in jobs_list:
        title_clean = job["title"].lower().strip()
        company_clean = job["company"].lower().strip()
        location_clean = job["location"].lower().strip()
        if company_clean in vague_names or company_clean == "":
            continue
        dedup_key = (title_clean, company_clean, location_clean)
        if dedup_key not in seen:
            seen.add(dedup_key)
            cleaned_jobs.append(job)
    return cleaned_jobs

# --- Section 8: Match % Calculation ---
def calculate_match(resume_matched_skills, job_description, role_skill_list):
    desc_norm = normalize(job_description)
    required_skills = []
    for skill in role_skill_list:
        norm_skill = normalize(skill)
        pattern = r'\b' + re.escape(norm_skill) + r's?\b'
        if re.search(pattern, desc_norm):
            required_skills.append(skill)
    if not required_skills:
        return 0, [], []
    matched = [skill for skill in required_skills if skill in resume_matched_skills]
    missing = [skill for skill in required_skills if skill not in resume_matched_skills]
    match_pct = round((len(matched) / len(required_skills)) * 100, 1)
    return match_pct, matched, missing

# --- Section 9: Display ---
def is_truncated(description):
    return description.strip().endswith(("…", "...")) or len(description) >= 499

def get_match_badge(job, min_skills_threshold=3):
    required_all = job.get("matched_skills", []) + job.get("missing_skills", [])
    required_count = len(required_all)
    
    if required_count == 0:
        return "Unclear", "#6B7280"
    elif required_count < min_skills_threshold:
        return "Limited data", "#6B7280"
    else:
        pct = job["match_pct"]
        if pct >= 70:
            color = "#10B981"
        elif pct >= 40:
            color = "#F59E0B"
        else:
            color = "#EF4444"
        label = f"{pct}%"
        if is_truncated(job["description"]):
            label += " (partial)"
        return label, color

def get_score_color(pct):
    if pct >= 70:
        return "#10B981"
    elif pct >= 40:
        return "#F59E0B"
    else:
        return "#EF4444"

def format_salary(salary):
    if not salary:
        return "Not disclosed"
    
    if salary < 100000:
        return f"₹{salary:,.0f} /month (est.)"
    else:
        lakh = salary / 100000
        return f"₹{lakh:.1f} LPA"

def render_job_card(job):
    label, color = get_match_badge(job)
    salary = format_salary(job["salary"])
    
    card_html = f"""
    <div style="background-color:#FFFFFF; border-radius:12px; padding:18px; margin-bottom:16px; border:1px solid #DCE1E8; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-size:16px; font-weight:600; color:#1F2937;">{job['title']}</div>
          <div style="font-size:14px; color:#6B7280;">{job['company']} • {job['location']}</div>
        </div>
        <div style="background-color:{color}; color:white; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:600;">{label}</div>
      </div>
      <div style="margin-top:10px; font-size:13px; color:#4B5563;">💰 {salary} &nbsp;|&nbsp; 🌐 {job['source']}</div>
      <div style="margin-top:8px; font-size:12px; color:#9CA3AF;">Want the exact skill breakdown? Use "Verify an Exact Match" below.</div>
      <div style="margin-top:10px;">
        <a href="{job['apply_link']}" target="_blank" style="background-color:{color}; color:white; padding:6px 14px; border-radius:6px; text-decoration:none; font-size:13px;">Apply →</a>
      </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def display_results(jobs_list, top_n=10, min_skills_threshold=3):
    display_data = []
    for job in jobs_list[:top_n]:
        required_all = job.get("matched_skills", []) + job.get("missing_skills", [])
        required_count = len(required_all)
        if required_count == 0:
            match_display = "Unclear — description too vague to detect skills"
            requires_display = found_display = missing_display = "N/A"
        elif required_count < min_skills_threshold:
            match_display = "Limited data — few specific skills mentioned"
            requires_display = ", ".join(required_all)
            found_display = ", ".join(job.get("matched_skills", [])) if job.get("matched_skills") else "None"
            missing_display = ", ".join(job["missing_skills"]) if job["missing_skills"] else "None"
        else:
            match_display = f"{job['match_pct']}%"
            if is_truncated(job["description"]):
                match_display += " (partial description)"
            requires_display = ", ".join(required_all)
            found_display = ", ".join(job.get("matched_skills", [])) if job.get("matched_skills") else "None"
            missing_display = ", ".join(job["missing_skills"]) if job["missing_skills"] else "None"
        
        display_data.append({
            "Company": job["company"], "Title": job["title"], "Location": job["location"],
            "Salary": job["salary"] if job["salary"] else "Not disclosed",
            "Match %": match_display, "Job Requires": requires_display,
            "Skills Found": found_display, "Missing Skills": missing_display,
            "Apply Link": f'<a href="{job["apply_link"]}" target="_blank">Apply</a>',
            "Source": job["source"]
        })
    return pd.DataFrame(display_data)

# --- Main app flow ---
col_upload, col_roles = st.columns(2)

with col_upload:
    with st.container(border=True):
        section_header("📄 Upload")
        uploaded_file = st.file_uploader("Choose a PDF resume", type="pdf")
        if uploaded_file is not None:
            if st.session_state.get("last_uploaded_name") != uploaded_file.name:
                st.success("✅ File uploaded successfully!")
                st.session_state.last_uploaded_name = uploaded_file.name

if uploaded_file is not None:
    
    resume_text = extract_text_from_pdf(uploaded_file)
    sections = split_resume_sections(resume_text, section_headers)
    results = extract_skills(sections, role_skills)
    role_scores = score_roles(results, role_skills)
    roles_to_search = determine_roles_to_search(role_scores)

    role_levels = {}
    for role, pct in roles_to_search:
        role_levels[role] = detect_level(sections, role, senior_skills)

    resume_skills_by_role = {}
    full_skill_list_by_role = {}
    for role, pct in roles_to_search:
        level = role_levels[role]
        skill_list = get_combined_skill_list(role, role_skills, senior_skills, level)
        full_skill_list_by_role[role] = skill_list
        resume_skills_by_role[role] = extract_skills_for_role(sections, skill_list)

    with col_roles:
        with st.container(border=True):
            section_header("🎯 Roles")
            role_options = [role for role, pct in roles_to_search]
            selected_roles = st.multiselect(
                "Detected roles — uncheck any that don't fit:",
                options=role_options,
                default=role_options
            )
            for role in selected_roles:
                level_label = "🌱 Entry Level" if role_levels[role] == "entry level" else "⭐ Experienced"
                st.caption(f"**{role}**: {level_label}")

    with st.container(border=True):
                section_header("🛠️ Skills")
                st.caption("Comma-separated")
                edited_skills = {}
                for role in selected_roles:
                    skills_text = st.text_area(f"{role}:", value=", ".join(resume_skills_by_role[role]))
                    edited_skills[role] = [s.strip() for s in skills_text.split(",") if s.strip()]


    city = st.selectbox("Select city", ["Ahmedabad", "Surat", "Mumbai", "Bangalore", "Delhi", "Pune", "Hyderabad"])

    search_clicked = st.button("Find Matching Jobs")
    
    if search_clicked:
        with st.spinner("Searching live job postings..."):
            init_cache_db()
            all_jobs = []
            for role in selected_roles:
                level = role_levels[role]
                cached = get_cached_results(role, city, level)
                if cached is not None:
                    all_jobs += cached
                else:
                    fresh_jobs = get_adzuna_jobs(role, city, level, adzuna_app_id, adzuna_app_key) + get_jooble_jobs(role, city, level, jooble_key)
                    save_to_cache(role, city, level, fresh_jobs)
                    all_jobs += fresh_jobs
        
        cleaned_jobs = merge_and_clean(all_jobs)
        for job in cleaned_jobs:
            job_title_norm = normalize(job["title"])
            matched_role = None
            for role in selected_roles:
                if normalize(role) in job_title_norm:
                    matched_role = role
                    break
            if not matched_role:
                matched_role = selected_roles[0]
            
            skill_list_to_use = get_combined_skill_list(matched_role, role_skills, senior_skills, role_levels.get(matched_role, "entry level"))
            resume_skills_to_use = edited_skills[matched_role]
            
            match_pct, matched, missing = calculate_match(resume_skills_to_use, job["description"], skill_list_to_use)
            job["match_pct"] = match_pct
            job["matched_skills"] = matched
            job["missing_skills"] = missing
        
        cleaned_jobs = sorted(cleaned_jobs, key=lambda x: x["match_pct"], reverse=True)

        st.session_state.cleaned_jobs = cleaned_jobs
        st.session_state.has_searched = True

    if st.session_state.get("has_searched", False):
        cleaned_jobs = st.session_state.cleaned_jobs
        st.subheader("Matching Jobs")

        if not cleaned_jobs:
            st.warning("No matching jobs found for this role and city right now. Try a different city, or check back later — new postings appear regularly.")
        else:
            valid_matches = [j["match_pct"] for j in cleaned_jobs if len(j.get("matched_skills", [])) + len(j.get("missing_skills", [])) >= 3]
            avg_match = round(sum(valid_matches) / len(valid_matches), 1) if valid_matches else 0
            
            kpi_html = f"""
            <div style="display:flex; gap:16px; margin-bottom:20px;">
                <div style="flex:1; background-color:#14B8A6; border-radius:12px; padding:18px; border:1px solid #0F9488; box-shadow: 0 2px 6px rgba(0,0,0,0.05); text-align:center;">
                    <div style="font-size:15px; color:#E6FFFA; font-weight:500;">📋 Jobs Found</div>
                    <div style="font-size:28px; font-weight:700; color:#FFFFFF; margin-top:4px;">{len(cleaned_jobs)}</div>
                </div>
                <div style="flex:1; background-color:#14B8A6; border-radius:12px; padding:18px; border:1px solid #0F9488; box-shadow: 0 2px 6px rgba(0,0,0,0.05); text-align:center;">
                    <div style="font-size:15px; color:#E6FFFA; font-weight:500;">🎯 Avg Match %</div>
                    <div style="font-size:28px; font-weight:700; color:#FFFFFF; margin-top:4px;">{f"{avg_match}%" if valid_matches else "N/A"}</div>
                </div>
                <div style="flex:1; background-color:#14B8A6; border-radius:12px; padding:18px; border:1px solid #0F9488; box-shadow: 0 2px 6px rgba(0,0,0,0.05); text-align:center;">
                    <div style="font-size:15px; color:#E6FFFA; font-weight:500;">📍 City</div>
                    <div style="font-size:28px; font-weight:700; color:#FFFFFF; margin-top:4px;">{city}</div>
                </div>
            </div>
            """
            st.markdown(kpi_html, unsafe_allow_html=True)

            st.info("⚠️ Match percentages are estimates based on available job data, which is sometimes incomplete. For an exact score, use the 'Verify an Exact Match' section below and paste the full job description.")
            for job in cleaned_jobs[:10]:
                render_job_card(job)
                
            st.markdown("---")
            with st.container(border=True):
                section_header("🔍 Verify an Exact Match")
                job_labels = ["None"] + [f"{job['company']} — {job['title']}" for job in cleaned_jobs[:10]]
                selected_job_label = st.selectbox("Select a job to verify", job_labels)

                if selected_job_label == "None":
                    if len(selected_roles) == 1:
                        matched_role = selected_roles[0]
                    else:
                        matched_role = st.selectbox("Which of your roles is this job for?", selected_roles)
                else:
                    selected_index = job_labels.index(selected_job_label) - 1
                    selected_job = cleaned_jobs[selected_index]
                    job_title_norm = normalize(selected_job["title"])
                    matched_role = None
                    for role in selected_roles:
                        if normalize(role) in job_title_norm:
                            matched_role = role
                            break
                    if not matched_role:
                        matched_role = selected_roles[0]

                if "paste_key" not in st.session_state:
                    st.session_state.paste_key = 0
        
                pasted_description = st.text_area(
                    "Paste the full job description here", 
                    height=250, 
                    key=f"paste_{st.session_state.paste_key}"
                )
        
                col_verify, col_clear = st.columns([2, 1])
                with col_verify:
                    verify_clicked = st.button("Recalculate Exact Match")
                with col_clear:
                    if st.button("Clear"):
                        st.session_state.paste_key += 1
                        st.rerun()
        
                if verify_clicked:
                    if not pasted_description.strip():
                        st.warning("Please paste the job description first.")
                    else:
                        skill_list_to_use = get_combined_skill_list(matched_role, role_skills, senior_skills, role_levels.get(matched_role, "entry level"))
                        resume_skills_to_use = edited_skills[matched_role]

                        verified_pct, verified_matched, verified_missing = calculate_match(resume_skills_to_use, pasted_description, skill_list_to_use)

                        verified_color = get_score_color(verified_pct)
                        st.markdown(f"""
                            <div style="background-color:{verified_color}; color:white; padding:12px 16px; border-radius:8px; font-size:16px; font-weight:600; margin-bottom:12px;">
                                ✅ Verified Match: {verified_pct}%
                            </div>
                        """, unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**✅ Skills Found:**")
                            st.write(', '.join(verified_matched) if verified_matched else 'None')
                        with col2:
                            st.markdown(f"**❌ Missing Skills:**")
                            st.write(', '.join(verified_missing) if verified_missing else 'None')

st.markdown('<hr style="margin-top:40px; border-color:#DCE1E8;">', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; color:#9CA3AF; font-size:13px;">Created by Yukti Patel | Data via Adzuna & Jooble APIs | Match accuracy depends on job posting detail</p>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; color:#9CA3AF; font-size:13px;"><a href="https://github.com/yuktipatel72-design" target="_blank" style="color:#0F766E;">GitHub</a> &nbsp;|&nbsp; <a href="www.linkedin.com/in/yuktipatel0472" target="_blank" style="color:#0F766E;">LinkedIn</a></p>', unsafe_allow_html=True)