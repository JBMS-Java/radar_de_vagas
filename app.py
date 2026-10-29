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
    save_user_profile,
    save_user_skills,
    skill_demand,
)

st.set_page_config(
    page_title="Radar de vagas",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #f7f9fc 0%, #ffffff 40%);
    }
    [data-testid="stHeader"] {
        background: rgba(247, 249, 252, 0.8);
    }
    [data-testid="stSidebar"] {
        background: #f0f4f8;
        border-right: 1px solid #e4eaf1;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e7edf4;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 3px 12px rgba(27, 47, 76, 0.04);
    }
    [data-testid="stMetricLabel"] p {
        color: #64748b;
        font-size: 0.9rem;
    }
    [data-testid="stMetricValue"] {
        color: #172b4d;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #e7edf4;
        border-radius: 14px;
    }
    .eyebrow {
        color: #546b86;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }
    .hero-title {
        color: #172b4d;
        font-size: clamp(2rem, 4vw, 2.8rem);
        font-weight: 750;
        letter-spacing: -0.045em;
        line-height: 1.12;
        margin: 0;
    }
    .hero-copy {
        color: #64748b;
        font-size: 1.05rem;
        margin-top: 0.65rem;
    }
    .section-copy {
        color: #64748b;
        margin-top: -0.5rem;
        margin-bottom: 1rem;
    }
    .skill-chip {
        display: inline-block;
        background: #edf4ff;
        border: 1px solid #d9e8fc;
        border-radius: 999px;
        color: #245c9a;
        font-size: 0.84rem;
        margin: 0.2rem 0.25rem 0.2rem 0;
        padding: 0.28rem 0.7rem;
    }
    </style>
    """,
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
        filters = st.columns([2, 1, 1, 1])
        query = filters[0].text_input(
            "Buscar",
            placeholder="Cargo, empresa ou tecnologia",
            key="job_search",
        )
        selected_skill = filters[1].selectbox("Tecnologia", ["Todas", *all_skills])
        selected_level = filters[2].selectbox(
            "Nível",
            ["Todos", "Estágio", "Júnior", "Pleno", "Sênior", "Não informado"],
        )
        selected_modality = filters[3].selectbox(
            "Modalidade",
            ["Todas", "Remoto", "Híbrido", "Presencial / não informado"],
        )
        filtered = filter_jobs(
            jobs,
            query=query,
            skill=selected_skill,
            level=selected_level,
            modality=selected_modality,
        )
        st.caption(f"{len(filtered)} oportunidade(s) encontradas")
        if filtered.empty:
            st.warning("Nenhuma vaga corresponde aos filtros atuais. Tente ampliar a busca.")
        else:
            for _, job in filtered.head(50).iterrows():
                with st.container(border=True):
                    heading, action = st.columns([5, 1])
                    heading.markdown(f"#### {job['title']}")
                    heading.markdown(
                        f"**{html.escape(str(job['company']))}** &nbsp; · &nbsp; "
                        f"{html.escape(str(job['location']))}",
                        unsafe_allow_html=True,
                    )
                    action.write("")
                    if job["url"]:
                        action.link_button("Ver vaga ↗", job["url"], use_container_width=True)
                    details = st.columns(3)
                    details[0].caption(f"🎯 {job['level']}")
                    details[1].caption(f"📍 {job['modality']}")
                    details[2].caption(f"Fonte: {job['source']}")
                    listed_skills = [item.strip() for item in job["skills"].split(",") if item.strip()]
                    if listed_skills:
                        chips = "".join(
                            f'<span class="skill-chip">{html.escape(skill)}</span>'
                            for skill in listed_skills
                        )
                        st.markdown(chips, unsafe_allow_html=True)
                    with st.expander("Ler descrição"):
                        st.write(job["description"] or "Descrição não disponível.")
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
