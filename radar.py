"""Data access and analysis helpers for the job radar."""

from __future__ import annotations

import html
import os
import re
import sqlite3
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pandas as pd
import requests

DEFAULT_DB_PATH = Path(os.environ.get(
    "RADAR_DB_PATH",
    str(Path(__file__).parent / ".data" / "radar_vagas.db"),
))
API_TIMEOUT = 20
TRANSLATOR_URL = "https://api.cognitive.microsofttranslator.com/translate"
TRANSLATION_CHAR_LIMIT = 50_000

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "C#": ("c#", "c sharp"),
    "C++": ("c++",),
    "Django": ("django",),
    "Docker": ("docker",),
    "FastAPI": ("fastapi",),
    "Flask": ("flask",),
    "GCP": ("gcp", "google cloud"),
    "Git": ("git", "github", "gitlab"),
    "IA generativa": ("generative ai", "ia generativa", "genai"),
    "Java": ("java",),
    "JavaScript": ("javascript", "js"),
    "Kubernetes": ("kubernetes", "k8s"),
    "LLMs": ("llm", "llms", "large language model", "modelos de linguagem"),
    "Machine Learning": ("machine learning", "aprendizado de máquina"),
    "Microsoft .NET": (".net", "dotnet"),
    "Node.js": ("node.js", "nodejs"),
    "Pandas": ("pandas",),
    "PostgreSQL": ("postgresql", "postgres"),
    "Python": ("python",),
    "PyTorch": ("pytorch",),
    "React": ("react", "react.js"),
    "REST APIs": ("rest api", "restful", "api rest"),
    "SQL": ("sql",),
    "Scikit-learn": ("scikit-learn", "sklearn"),
    "Spark": ("apache spark", "spark"),
    "SQLite": ("sqlite",),
    "TensorFlow": ("tensorflow",),
    "TypeScript": ("typescript", "ts"),
}

SOURCES = {
    "Remotive": "https://remotive.com/api/remote-jobs?category=software-dev",
    "Arbeitnow": "https://www.arbeitnow.com/api/job-board-api",
}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def clean_description(value: str | None) -> str:
    """Convert an HTML job description to readable plain text."""
    parser = _HTMLTextExtractor()
    parser.feed(value or "")
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()


def _contains_term(text: str, term: str) -> bool:
    escaped = re.escape(term)
    if term[0].isalnum():
        escaped = r"(?<!\w)" + escaped
    if term[-1].isalnum():
        escaped += r"(?!\w)"
    return re.search(escaped, text, flags=re.IGNORECASE) is not None


def extract_skills(text: str) -> list[str]:
    """Return recognized skills in a description, in stable display order."""
    return [
        skill
        for skill, aliases in SKILL_ALIASES.items()
        if any(_contains_term(text, alias) for alias in aliases)
    ]


def infer_level(text: str) -> str:
    normalized = text.casefold()
    if re.search(r"\b(intern|internship|estágio|estagiário|trainee)\b", normalized):
        return "Estágio"
    if re.search(r"\b(junior|júnior|jr\.?|entry.level|entry level|beginner)\b", normalized):
        return "Júnior"
    if re.search(r"\b(senior|sênior|sr\.?|staff|principal|lead)\b", normalized):
        return "Sênior"
    if re.search(r"\b(mid.level|mid level|pleno|intermediate)\b", normalized):
        return "Pleno"
    return "Não informado"


def infer_modality(remote: bool, text: str) -> str:
    if remote:
        return "Remoto"
    if re.search(r"\b(hybrid|híbrido|hibrido)\b", text, flags=re.IGNORECASE):
        return "Híbrido"
    return "Presencial / não informado"


def normalize_remotive_job(item: dict[str, Any]) -> dict[str, Any]:
    description = clean_description(item.get("description"))
    tags = item.get("tags") or []
    searchable_text = " ".join(
        str(value)
        for value in (
            item.get("title", ""),
            item.get("company_name", ""),
            item.get("candidate_required_location", ""),
            description,
            " ".join(str(tag) for tag in tags),
        )
    )
    return {
        "source": "Remotive",
        "source_id": str(item["id"]),
        "title": str(item.get("title") or "Sem título"),
        "company": str(item.get("company_name") or "Empresa não informada"),
        "location": str(item.get("candidate_required_location") or "Não informada"),
        "url": str(item.get("url") or ""),
        "description": description,
        "tags": ", ".join(str(tag) for tag in tags),
        "published_at": str(item.get("publication_date") or ""),
        "remote": True,
        "level": infer_level(searchable_text),
        "modality": infer_modality(True, searchable_text),
        "skills": extract_skills(searchable_text),
    }


def normalize_arbeitnow_job(item: dict[str, Any]) -> dict[str, Any]:
    description = clean_description(item.get("description"))
    tags = item.get("tags") or []
    remote = bool(item.get("remote", False))
    searchable_text = " ".join(
        str(value)
        for value in (
            item.get("title", ""),
            item.get("company_name", ""),
            item.get("location", ""),
            description,
            " ".join(str(tag) for tag in tags),
        )
    )
    return {
        "source": "Arbeitnow",
        "source_id": str(item.get("slug") or item.get("url") or ""),
        "title": str(item.get("title") or "Sem título"),
        "company": str(item.get("company_name") or "Empresa não informada"),
        "location": str(item.get("location") or "Não informada"),
        "url": str(item.get("url") or ""),
        "description": description,
        "tags": ", ".join(str(tag) for tag in tags),
        "published_at": str(item.get("created_at") or ""),
        "remote": remote,
        "level": infer_level(searchable_text),
        "modality": infer_modality(remote, searchable_text),
        "skills": extract_skills(searchable_text),
    }


def fetch_jobs(source: str) -> list[dict[str, Any]]:
    """Fetch and normalize listings from a supported public job API."""
    if source not in SOURCES:
        raise ValueError(f"Fonte não suportada: {source}")
    response = requests.get(SOURCES[source], timeout=API_TIMEOUT)
    response.raise_for_status()
    payload = response.json()

    if source == "Remotive":
        items = payload.get("jobs", [])
        normalize = normalize_remotive_job
    else:
        items = payload.get("data", [])
        normalize = normalize_arbeitnow_job
    if not isinstance(items, list):
        raise ValueError(f"A API {source} retornou uma lista de vagas inválida.")
    return [normalize(item) for item in items if isinstance(item, dict)]


def translate_job_text(title: str, description: str) -> tuple[str, str]:
    """Translate a job title and description to Brazilian Portuguese."""
    api_key = os.environ.get("AZURE_TRANSLATOR_KEY")
    if not api_key:
        raise RuntimeError(
            "Configure a variável de ambiente AZURE_TRANSLATOR_KEY para traduzir vagas."
        )
    if len(title) + len(description) > TRANSLATION_CHAR_LIMIT:
        raise ValueError(
            "O texto desta vaga excede o limite de caracteres aceito pelo tradutor."
        )

    texts = [title, description]
    included = [(index, text) for index, text in enumerate(texts) if text]
    if not included:
        return title, description

    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "application/json; charset=UTF-8",
    }
    region = os.environ.get("AZURE_TRANSLATOR_REGION")
    if region:
        headers["Ocp-Apim-Subscription-Region"] = region

    response = requests.post(
        TRANSLATOR_URL,
        params={"api-version": "3.0", "to": "pt-BR"},
        headers=headers,
        json=[{"Text": text} for _, text in included],
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) != len(included):
        raise ValueError("O serviço de tradução retornou uma resposta inválida.")

    translated = list(texts)
    for (index, _), result in zip(included, payload):
        if not isinstance(result, dict):
            raise ValueError("O serviço de tradução retornou uma resposta inválida.")
        translations = result.get("translations")
        if (
            not isinstance(translations, list)
            or not translations
            or not isinstance(translations[0], dict)
            or not isinstance(translations[0].get("text"), str)
        ):
            raise ValueError("O serviço de tradução retornou uma resposta inválida.")
        translated[index] = translations[0]["text"]
    return translated[0], translated[1]


def initialize_database(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                url TEXT NOT NULL,
                description TEXT NOT NULL,
                tags TEXT NOT NULL,
                published_at TEXT NOT NULL,
                remote INTEGER NOT NULL,
                level TEXT NOT NULL,
                modality TEXT NOT NULL,
                skills TEXT NOT NULL,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source, source_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_skills (
                skill TEXT PRIMARY KEY COLLATE NOCASE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL DEFAULT '',
                target_role TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS job_translations (
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                original_title TEXT NOT NULL,
                original_description TEXT NOT NULL,
                translated_title TEXT NOT NULL,
                translated_description TEXT NOT NULL,
                PRIMARY KEY (source, source_id)
            )
            """
        )


def save_jobs(jobs: list[dict[str, Any]], db_path: str | Path = DEFAULT_DB_PATH) -> int:
    initialize_database(db_path)
    rows = [
        (
            job["source"],
            job["source_id"],
            job["title"],
            job["company"],
            job["location"],
            job["url"],
            job["description"],
            job["tags"],
            job["published_at"],
            int(job["remote"]),
            job["level"],
            job["modality"],
            ", ".join(job["skills"]),
        )
        for job in jobs
        if job["source_id"]
    ]
    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO jobs (
                source, source_id, title, company, location, url, description,
                tags, published_at, remote, level, modality, skills
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_id) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                location = excluded.location,
                url = excluded.url,
                description = excluded.description,
                tags = excluded.tags,
                published_at = excluded.published_at,
                remote = excluded.remote,
                level = excluded.level,
                modality = excluded.modality,
                skills = excluded.skills,
                imported_at = CURRENT_TIMESTAMP
            """,
            rows,
        )
    return len(rows)


def load_jobs(db_path: str | Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        return pd.read_sql_query(
            """
            SELECT jobs.*,
                CASE WHEN job_translations.original_title = jobs.title
                    AND job_translations.original_description = jobs.description
                    THEN job_translations.translated_title ELSE '' END
                    AS translated_title,
                CASE WHEN job_translations.original_title = jobs.title
                    AND job_translations.original_description = jobs.description
                    THEN job_translations.translated_description ELSE '' END
                    AS translated_description
            FROM jobs
            LEFT JOIN job_translations
                ON job_translations.source = jobs.source
                AND job_translations.source_id = jobs.source_id
            ORDER BY jobs.published_at DESC, jobs.imported_at DESC
            """,
            connection,
        )


def save_job_translation(
    source: str,
    source_id: str,
    original_title: str,
    original_description: str,
    translated_title: str,
    translated_description: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO job_translations (
                source, source_id, original_title, original_description,
                translated_title, translated_description
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_id) DO UPDATE SET
                original_title = excluded.original_title,
                original_description = excluded.original_description,
                translated_title = excluded.translated_title,
                translated_description = excluded.translated_description
            """,
            (
                source,
                source_id,
                original_title,
                original_description,
                translated_title,
                translated_description,
            ),
        )


def save_user_skills(skills: list[str], db_path: str | Path = DEFAULT_DB_PATH) -> None:
    initialize_database(db_path)
    unique: dict[str, str] = {}
    for skill in skills:
        if skill.strip():
            unique.setdefault(skill.strip().casefold(), skill.strip())
    cleaned = sorted(unique.values(), key=str.casefold)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DELETE FROM user_skills")
        connection.executemany(
            "INSERT INTO user_skills (skill) VALUES (?)",
            [(skill,) for skill in cleaned],
        )


def load_user_skills(db_path: str | Path = DEFAULT_DB_PATH) -> list[str]:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT skill FROM user_skills ORDER BY skill COLLATE NOCASE"
        ).fetchall()
    return [row[0] for row in rows]


def save_user_profile(
    name: str,
    target_role: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO user_profile (id, name, target_role)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                target_role = excluded.target_role
            """,
            (name.strip(), target_role.strip()),
        )


def load_user_profile(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, str]:
    initialize_database(db_path)
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT name, target_role FROM user_profile WHERE id = 1"
        ).fetchone()
    if row is None:
        return {"name": "", "target_role": ""}
    return {"name": row[0], "target_role": row[1]}


def filter_jobs(
    jobs: pd.DataFrame,
    query: str = "",
    skill: str = "Todas",
    level: str = "Todos",
    modality: str = "Todas",
    location: str = "",
) -> pd.DataFrame:
    filtered = jobs.copy()
    if filtered.empty:
        return filtered
    if query.strip():
        mask = filtered.apply(
            lambda row: query.casefold()
            in " ".join(
                str(row[column])
                for column in ("title", "company", "location", "description", "tags")
            ).casefold(),
            axis=1,
        )
        filtered = filtered[mask]
    if location.strip():
        filtered = filtered[
            filtered["location"].fillna("").apply(
                lambda value: location.strip().casefold() in str(value).casefold()
            )
        ]
    if skill != "Todas":
        filtered = filtered[
            filtered["skills"].fillna("").apply(
                lambda value: skill.casefold()
                in {item.strip().casefold() for item in value.split(",")}
            )
        ]
    if level != "Todos":
        filtered = filtered[filtered["level"] == level]
    if modality != "Todas":
        filtered = filtered[filtered["modality"] == modality]
    return filtered.reset_index(drop=True)


def skill_demand(jobs: pd.DataFrame) -> pd.Series:
    if jobs.empty:
        return pd.Series(dtype="int64", name="Vagas")
    counts: dict[str, int] = {}
    for skills in jobs["skills"].fillna(""):
        for skill in skills.split(","):
            normalized = skill.strip()
            if normalized:
                counts[normalized] = counts.get(normalized, 0) + 1
    return pd.Series(counts, dtype="int64").sort_values(ascending=False).rename("Vagas")
