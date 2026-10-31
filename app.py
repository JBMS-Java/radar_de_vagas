import html
import sqlite3

import requests
import streamlit as st

from radar import (
    DEFAULT_DB_PATH,
    SOURCES,
    SKILL_ALIASES,
    fetch_jobs,
    filter_jobs,
    load_jobs,
    load_user_profile,
    load_user_skills,
    save_jobs,
    save_job_translation,
    save_user_profile,
    save_user_skills,
    skill_demand,
    translate_job_text,
)

st.set_page_config(
    page_title="Radar de vagas",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    dark_mode = st.toggle(
        "Modo escuro",
        help="Altere a aparência da interface.",
    )

theme_variables = (
    ":root {\n"
    f"  color-scheme: {'dark' if dark_mode else 'light'};\n"
    f"  --radar-bg: {'#111827' if dark_mode else '#f7f9fc'};\n"
    f"  --radar-panel: {'#1f2937' if dark_mode else '#ffffff'};\n"
    f"  --radar-sidebar: {'#182233' if dark_mode else '#f0f4f8'};\n"
    f"  --radar-text: {'#e5e7eb' if dark_mode else '#172b4d'};\n"
    f"  --radar-muted: {'#a7b3c5' if dark_mode else '#64748b'};\n"
    f"  --radar-border: {'#374151' if dark_mode else '#e4eaf1'};\n"
    f"  --radar-chip-bg: {'#263b58' if dark_mode else '#edf4ff'};\n"
    f"  --radar-chip-border: {'#3b5578' if dark_mode else '#d9e8fc'};\n"
    f"  --radar-chip-text: {'#bfdbfe' if dark_mode else '#245c9a'};\n"
    "}"
)

st.markdown(
    """
    <style>
    THEME_VARIABLES
    body, [data-testid="stAppViewContainer"] {
        background: var(--radar-bg);
        color: var(--radar-text);
    }
    [data-testid="stAppViewContainer"] .main .block-container {
        max-width: 1440px;
        padding-top: 2rem;
    }
    [data-testid="stHeader"] {
        background: var(--radar-bg);
    }
    [data-testid="stSidebar"] {
        background: var(--radar-sidebar);
        border-right: 1px solid var(--radar-border);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] {
        color: var(--radar-text);
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] {
        color: var(--radar-muted);
    }
    .stApp [data-baseweb="input"] > div,
    .stApp [data-baseweb="select"] > div,
    .stApp textarea {
        background: var(--radar-panel);
        border-color: var(--radar-border);
        color: var(--radar-text);
    }
    .stApp [data-testid="stMultiSelect"] [role="group"],
    .stApp [data-testid="stSelectbox"] [role="group"] {
        background: var(--radar-panel);
        border-color: var(--radar-border);
        color: var(--radar-text);
    }
    .stApp input,
    .stApp textarea,
    .stApp [data-baseweb="select"] *,
    .stApp [data-testid="stMultiSelect"] input,
    .stApp [data-testid="stSelectbox"] input {
        color: var(--radar-text);
    }
    [data-testid="stBaseLinkButton-secondary"] {
        background: var(--radar-panel);
        border-color: var(--radar-border);
        color: var(--radar-text);
    }
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background: var(--radar-panel);
        color: var(--radar-text);
    }
    [data-testid="stExpander"] details {
        border: 1px solid var(--radar-border);
        border-radius: 10px;
    }
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] p {
        color: var(--radar-text);
    }
    [data-testid="stExpander"] summary:hover {
        color: var(--radar-text);
    }
    [data-testid="stMetric"] {
        background: var(--radar-panel);
        border: 1px solid var(--radar-border);
        border-radius: 14px;
        padding: 18px 20px;
        color: var(--radar-text);
    }
    [data-testid="stMetricLabel"] p {
        color: var(--radar-muted);
        font-size: 0.9rem;
    }
    [data-testid="stMetricValue"] {
        color: var(--radar-text);
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--radar-border);
        border-radius: 14px;
    }
    .eyebrow {
        color: var(--radar-muted);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }
    .hero-title {
        color: var(--radar-text);
        font-size: clamp(2rem, 4vw, 2.8rem);
        font-weight: 750;
        letter-spacing: -0.045em;
        line-height: 1.12;
        margin: 0;
    }
    .hero-copy {
        color: var(--radar-muted);
        font-size: 1.05rem;
        margin-top: 0.65rem;
    }
    .section-copy {
        color: var(--radar-muted);
        margin-top: -0.5rem;
        margin-bottom: 1rem;
    }
    .skill-chip {
        display: inline-block;
        background: var(--radar-chip-bg);
        border: 1px solid var(--radar-chip-border);
        border-radius: 999px;
        color: var(--radar-chip-text);
        font-size: 0.84rem;
        margin: 0.2rem 0.25rem 0.2rem 0;
        padding: 0.28rem 0.7rem;
    }
    </style>
    """.replace("THEME_VARIABLES", theme_variables),
    unsafe_allow_html=True,
)

profile = load_user_profile(DEFAULT_DB_PATH)
saved_skills = load_user_skills(DEFAULT_DB_PATH)
jobs = load_jobs(DEFAULT_DB_PATH)
greeting = f", {profile['name']}" if profile["name"] else ""

st.markdown('<div class="eyebrow">Seu próximo passo começa aqui</div>', unsafe_allow_html=True)
st.markdown(
    f'<h1 class="hero-title">Radar de vagas{html.escape(greeting)}</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="hero-copy">Oportunidades de tecnologia e um mapa claro do que aprender a seguir.</p>',
    unsafe_allow_html=True,
)
st.write("")


def refresh_sources(selected_sources: list[str]) -> None:
    for source in selected_sources:
        with st.spinner(f"Buscando vagas no {source}..."):
            imported = save_jobs(fetch_jobs(source), DEFAULT_DB_PATH)
        st.success(f"{imported} vagas do {source} importadas ou atualizadas.")


with st.sidebar:
    st.markdown("### 📡 Radar")
    st.caption("Acompanhe o mercado e evolua no seu ritmo.")
    st.divider()
    st.markdown("#### Fontes de vagas")
    st.caption("Os dados importados ficam salvos neste dispositivo.")
    selected_sources = st.multiselect(
        "APIs para consultar",
        options=list(SOURCES),
        default=list(SOURCES),
    )
    if st.button("↻  Atualizar oportunidades", type="primary", use_container_width=True):
        if not selected_sources:
            st.warning("Selecione ao menos uma fonte.")
        else:
            try:
                refresh_sources(selected_sources)
                st.rerun()
            except (requests.RequestException, ValueError, KeyError, sqlite3.Error) as error:
                st.error(f"Não foi possível atualizar as vagas: {error}")
    st.divider()
    st.caption("Seu perfil e suas vagas são armazenados localmente.")

overview_tab, jobs_tab, profile_tab = st.tabs(
    ["Visão geral", "Explorar vagas", "Meu perfil"]
)

all_skills = sorted(
    {
        skill.strip()
        for listing in jobs.get("skills", [])
        for skill in str(listing or "").split(",")
        if skill.strip()
    }
    | set(saved_skills),
    key=str.casefold,
)

with overview_tab:
    st.subheader("Visão geral")
    st.markdown(
        '<p class="section-copy">Um resumo do mercado e do seu progresso profissional.</p>',
        unsafe_allow_html=True,
    )
    opportunity_metrics = st.columns(2)
    opportunity_metrics[0].metric("Oportunidades", len(jobs))
    opportunity_metrics[1].metric(
        "Empresas",
        jobs["company"].nunique() if not jobs.empty else 0,
    )
    profile_metrics = st.columns(2)
    profile_metrics[0].metric("Habilidades no perfil", len(saved_skills))
    profile_metrics[1].metric(
        "Vagas compatíveis",
        int(jobs["skills"].apply(
            lambda value: bool(
                {item.strip().casefold() for item in str(value or "").split(",")}
                & {skill.casefold() for skill in saved_skills}
            )
        ).sum()) if not jobs.empty and saved_skills else 0,
    )

    chart_column, learning_column = st.columns([1.2, 1])
    with chart_column:
        st.subheader("O que o mercado está pedindo")
        demand = skill_demand(jobs).head(10)
        if demand.empty:
            st.info("Importe oportunidades para descobrir as tecnologias mais procuradas.")
        else:
            st.bar_chart(demand, color="#3b82f6", height=330)
    with learning_column:
        st.subheader("Ideias para aprender")
        gaps = skill_demand(jobs)
        owned = {skill.casefold() for skill in saved_skills}
        gaps = gaps[[skill.casefold() not in owned for skill in gaps.index]].head(6)
        if not saved_skills:
            st.info("Monte seu perfil na aba **Meu perfil** para personalizar suas sugestões.")
        elif gaps.empty:
            st.success("As vagas analisadas já combinam com as habilidades do seu perfil.")
        else:
            st.bar_chart(gaps, color="#8b5cf6", height=280)
            st.caption("Habilidades ainda não cadastradas, ordenadas por frequência nas vagas.")

    if not saved_skills:
        st.info("**Comece pelo seu perfil:** adicione as tecnologias que você já conhece para receber sugestões mais relevantes.")

with jobs_tab:
    st.subheader("Explore oportunidades")
    st.markdown(
        '<p class="section-copy">Filtre as vagas e encontre as que combinam com seus objetivos.</p>',
        unsafe_allow_html=True,
    )
    if jobs.empty:
        st.info("Nenhuma oportunidade importada ainda. Use **Atualizar oportunidades** no menu lateral para começar.")
    else:
        search_filters = st.columns([1.5, 1])
        query = search_filters[0].text_input(
            "Buscar",
            placeholder="Cargo, empresa ou tecnologia",
            key="job_search",
        )
        location_query = search_filters[1].text_input(
            "Localidade",
            placeholder="Ex.: Brasil, São Paulo, Europa",
            key="job_location",
        )
        filters = st.columns(3)
        selected_skill = filters[0].selectbox("Tecnologia", ["Todas", *all_skills])
        selected_level = filters[1].selectbox(
            "Nível",
            ["Todos", "Estágio", "Júnior", "Pleno", "Sênior", "Não informado"],
        )
        selected_modality = filters[2].selectbox(
            "Modalidade",
            ["Todas", "Remoto", "Híbrido", "Presencial / não informado"],
        )
        filtered = filter_jobs(
            jobs,
            query=query,
            skill=selected_skill,
            level=selected_level,
            modality=selected_modality,
            location=location_query,
        )
        st.caption(f"{len(filtered)} oportunidade(s) encontradas")
        if filtered.empty:
            st.warning("Nenhuma vaga corresponde aos filtros atuais. Tente ampliar a busca.")
        else:
            for _, job in filtered.head(50).iterrows():
                with st.container(border=True):
                    heading, action = st.columns([5, 1])
                    title = str(job["translated_title"] or job["title"])
                    heading.markdown(f"#### {title}")
                    heading.markdown(
                        f"**{html.escape(str(job['company']))}** &nbsp; · &nbsp; "
                        f"{html.escape(str(job['location']))}",
                        unsafe_allow_html=True,
                    )
                    action.write("")
                    if job["url"]:
                        action.link_button("Ver vaga ↗", job["url"], use_container_width=True)
                    details = st.columns(3)
                    details[0].caption(f"**Nível**  \n{job['level']}")
                    details[1].caption(f"**Modalidade**  \n{job['modality']}")
                    details[2].caption(f"**Fonte**  \n{job['source']}")
                    listed_skills = [item.strip() for item in job["skills"].split(",") if item.strip()]
                    if listed_skills:
                        chips = "".join(
                            f'<span class="skill-chip">{html.escape(skill)}</span>'
                            for skill in listed_skills
                        )
                        st.markdown(chips, unsafe_allow_html=True)
                    description = str(job["description"] or "")
                    translated_description = str(job["translated_description"] or "")
                    visible_description = translated_description or description
                    if not visible_description:
                        visible_description = "Descrição não disponível."
                    summary = " ".join(visible_description.split())
                    if len(summary) > 280:
                        summary = summary[:277].rstrip() + "..."
                    st.write(summary)
                    with st.expander("Descrição completa"):
                        if translated_description:
                            st.caption("Tradução automática para português.")
                            st.write(translated_description)
                            with st.expander("Ver descrição original"):
                                st.write(description or "Descrição não disponível.")
                        else:
                            st.write(description or "Descrição não disponível.")
                            if description:
                                st.caption(
                                    "O título e a descrição serão enviados ao Microsoft "
                                    "Translator; o serviço pode cobrar pelo uso."
                                )
                                translation_key = (
                                    f"translate_{job['source']}_{job['source_id']}"
                                )
                                if st.button(
                                    "Traduzir título e descrição para português",
                                    key=translation_key,
                                ):
                                    try:
                                        translated_title, translated_description = (
                                            translate_job_text(
                                                str(job["title"]),
                                                description,
                                            )
                                        )
                                        save_job_translation(
                                            str(job["source"]),
                                            str(job["source_id"]),
                                            str(job["title"]),
                                            description,
                                            translated_title,
                                            translated_description,
                                            DEFAULT_DB_PATH,
                                        )
                                    except (
                                        requests.RequestException,
                                        ValueError,
                                        RuntimeError,
                                    ) as error:
                                        st.error(f"Não foi possível traduzir a vaga: {error}")
                                    else:
                                        st.success("Tradução salva. Atualizando a vaga...")
                                        st.rerun()
            if len(filtered) > 50:
                st.caption("Exibindo 50 oportunidades. Refine os filtros para ver resultados mais específicos.")

with profile_tab:
    st.subheader("Seu perfil profissional")
    st.markdown(
        '<p class="section-copy">Conte ao Radar onde você quer chegar e o que já sabe fazer.</p>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        with st.form("profile_form"):
            name = st.text_input(
                "Como podemos chamar você?",
                value=profile["name"],
                placeholder="Seu nome",
                key="profile_name",
            )
            target_role = st.text_input(
                "Qual cargo você está buscando?",
                value=profile["target_role"],
                placeholder="Ex.: Pessoa desenvolvedora Python",
                key="profile_target_role",
            )
            st.markdown("#### Habilidades que você já possui")
            st.caption("Selecione da lista ou adicione outras habilidades no campo abaixo.")
            selected_profile_skills = st.multiselect(
                "Tecnologias e ferramentas",
                options=sorted(set(SKILL_ALIASES) | set(saved_skills), key=str.casefold),
                default=saved_skills,
                placeholder="Comece a digitar, por exemplo, Python ou SQL",
                key="profile_skills",
            )
            additional_skills = st.text_input(
                "Outras habilidades",
                placeholder="Ex.: comunicação, testes automatizados",
                help="Separe por vírgula. Essas habilidades também serão consideradas no seu perfil.",
                key="profile_additional_skills",
            )
            submitted = st.form_submit_button(
                "Salvar meu perfil",
                type="primary",
                use_container_width=True,
            )
        if submitted:
            custom_skills = [skill.strip() for skill in additional_skills.split(",")]
            save_user_profile(
                name,
                target_role,
                DEFAULT_DB_PATH,
            )
            save_user_skills(selected_profile_skills + custom_skills, DEFAULT_DB_PATH)
            st.success("Perfil atualizado. Suas sugestões já levam essas habilidades em conta.")
            st.rerun()

    with right:
        with st.container(border=True):
            st.markdown("#### Resumo do perfil")
            if profile["name"]:
                st.write(profile["name"])
            else:
                st.caption("Seu nome aparece aqui depois que você salvar o perfil.")
            st.write(profile["target_role"] or "Cargo desejado não informado")
            st.divider()
            st.metric("Habilidades cadastradas", len(saved_skills))
            if saved_skills:
                chips = "".join(
                    f'<span class="skill-chip">{html.escape(skill)}</span>'
                    for skill in saved_skills
                )
                st.markdown(chips, unsafe_allow_html=True)
            else:
                st.caption("Suas habilidades aparecerão aqui após salvar.")
        st.caption(
            "Seu perfil fica salvo localmente neste dispositivo e pode ser atualizado a qualquer momento."
        )
