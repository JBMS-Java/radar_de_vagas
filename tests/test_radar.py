import pandas as pd

from radar import (
    extract_skills,
    filter_jobs,
    infer_level,
    normalize_arbeitnow_job,
    normalize_remotive_job,
    save_jobs,
    load_jobs,
    load_user_profile,
    save_user_skills,
    save_user_profile,
    load_user_skills,
    skill_demand,
)


def test_extract_skills_recognizes_known_technologies_without_partial_matches():
    assert extract_skills("Python, FastAPI, and machine learning") == [
        "FastAPI",
        "Machine Learning",
        "Python",
    ]
    assert "Java" not in extract_skills("JavaScript developer")


def test_infer_level_detects_junior_and_internship():
    assert infer_level("Vaga para pessoa desenvolvedora júnior") == "Júnior"
    assert infer_level("Software engineering internship") == "Estágio"


def test_normalizers_clean_descriptions_and_detect_remote_status():
    remotive = normalize_remotive_job(
        {
            "id": 42,
            "title": "Junior Python Developer",
            "company_name": "Acme",
            "description": "<p>Use <strong>Python</strong> and SQL</p>",
            "candidate_required_location": "Worldwide",
            "tags": ["Python"],
            "url": "https://example.com/job",
        }
    )
    arbeitnow = normalize_arbeitnow_job(
        {
            "slug": "hybrid-role",
            "title": "Data Engineer",
            "description": "Hybrid role using Spark",
            "company_name": "Example",
            "location": "Berlin",
            "remote": False,
            "tags": [],
        }
    )
    assert remotive["description"] == "Use Python and SQL"
    assert remotive["level"] == "Júnior"
    assert remotive["modality"] == "Remoto"
    assert arbeitnow["modality"] == "Híbrido"


def test_jobs_and_profile_round_trip_in_sqlite(tmp_path):
    database = tmp_path / "jobs.sqlite"
    job = normalize_remotive_job(
        {
            "id": 1,
            "title": "Python Developer",
            "company_name": "Acme",
            "description": "Python and Docker",
            "url": "https://example.com/job",
        }
    )
    assert save_jobs([job], database) == 1
    assert save_jobs([job], database) == 1
    assert len(load_jobs(database)) == 1
    save_user_skills([" Python ", "SQL", "python"], database)
    assert load_user_skills(database) == ["Python", "SQL"]
    save_user_profile(" Joana ", "Python Developer ", database)
    assert load_user_profile(database) == {
        "name": "Joana",
        "target_role": "Python Developer",
    }


def test_profile_is_empty_before_user_creates_it(tmp_path):
    assert load_user_profile(tmp_path / "empty.sqlite") == {
        "name": "",
        "target_role": "",
    }


def test_filtering_and_skill_demand():
    jobs = pd.DataFrame(
        [
            {"title": "Junior Python", "company": "A", "location": "Remote",
             "description": "Build APIs", "tags": "", "skills": "Python, SQL",
             "level": "Júnior", "modality": "Remoto"},
            {"title": "Senior Java", "company": "B", "location": "Office",
             "description": "Build services", "tags": "", "skills": "Java, SQL",
             "level": "Sênior", "modality": "Presencial / não informado"},
        ]
    )
    filtered = filter_jobs(jobs, skill="Python", level="Júnior", modality="Remoto")
    assert len(filtered) == 1
    assert skill_demand(filtered).to_dict() == {"Python": 1, "SQL": 1}
