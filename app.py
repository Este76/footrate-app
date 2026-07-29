from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

import altair as alt
import pandas as pd
import streamlit as st


APP_TITLE = "FootRate"
SKILL_COLUMNS = {
    "shooting": "Frappe",
    "passing": "Passe",
    "creation": "Création",
    "technique": "Dribble et maîtrise",
    "defensive_contribution": "Apport défensif",
    "physical_impact": "Impact physique",
}
POSITION_LABELS = {
    "Attacker": "Attaquant",
    "Midfielder": "Milieu",
    "Defender": "Défenseur",
    "Goalkeeper": "Gardien",
    "Unknown": "Non renseigné",
}


def version_key(path: Path) -> tuple[int, ...]:
    """Transforme v0_6 en (0, 6) pour sélectionner le fichier le plus récent."""
    match = re.search(r"_v(\d+(?:_\d+)*)", path.stem)
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("_"))


def find_data_file() -> Path:
    preferred = [
        Path("output/footrate_official_v0_6.csv"),
        Path("output/footrate_official_v0_5.csv"),
        Path("output/footrate_ratings_v0_6.csv"),
    ]
    for path in preferred:
        if path.exists():
            return path

    candidates = list(Path("output").glob("footrate_official_v*.csv"))
    candidates += list(Path("output").glob("footrate_ratings_v*.csv"))
    if candidates:
        return sorted(candidates, key=version_key, reverse=True)[0]

    raise FileNotFoundError(
        "Aucun fichier FootRate n'a été trouvé dans le dossier output."
    )


def read_bool(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False, "1": True, "0": False})
        .fillna(False)
    )


@st.cache_data(show_spinner=False)
def load_data(path_as_text: str) -> pd.DataFrame:
    path = Path(path_as_text)
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")

    aliases = {
        "defending": "defensive_contribution",
        "physical_im": "physical_impact",
        "overall_prec": "overall_precalibrated",
        "calibration_a": "calibration_adjustment",
    }
    df = df.rename(columns={key: value for key, value in aliases.items() if key in df.columns})

    required_text = ["player_name", "team_name", "position"]
    for column in required_text:
        if column not in df.columns:
            df[column] = "Non renseigné"
        df[column] = df[column].fillna("Non renseigné").astype(str)

    numeric_columns = [
        "player_id", "team_id", "minutes", *SKILL_COLUMNS.keys(),
        "profile_score", "performance_score", "overall_precalibrated",
        "calibration_adjustment", "overall", "form", "matches_in_form",
    ]
    for column in numeric_columns:
        if column not in df.columns:
            df[column] = pd.NA
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if "official_rating" not in df.columns:
        df["official_rating"] = df["minutes"].ge(900)
    else:
        df["official_rating"] = read_bool(df["official_rating"])

    if "provisional" not in df.columns:
        df["provisional"] = df["minutes"].between(450, 899, inclusive="both")
    else:
        df["provisional"] = read_bool(df["provisional"])

    if "reliability" not in df.columns:
        df["reliability"] = pd.cut(
            df["minutes"],
            bins=[-1, 449, 899, 1349, float("inf")],
            labels=["insuffisante", "provisoire", "moyenne", "élevée"],
        ).astype(str)
    else:
        reliability_translation = {
            "high": "élevée",
            "medium": "moyenne",
            "low": "faible",
            "insufficient": "insuffisante",
            "provisional": "provisoire",
        }
        df["reliability"] = (
            df["reliability"]
            .fillna("non renseignée")
            .astype(str)
            .str.strip()
            .str.lower()
            .replace(reliability_translation)
        )

    if "clubs_in_season" not in df.columns:
        df["clubs_in_season"] = df["team_name"]

    df["position_fr"] = df["position"].map(POSITION_LABELS).fillna(df["position"])
    df["display_name"] = (
        df["player_name"].astype(str)
        + " — "
        + df["team_name"].astype(str)
    )

    df = df.dropna(subset=["overall"]).copy()
    df = df.sort_values(["overall", "minutes"], ascending=[False, False])
    df["rank"] = range(1, len(df) + 1)
    return df


def score_color(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "#64748B"
    value = float(value)
    if value >= 90:
        return "#D4AF37"
    if value >= 85:
        return "#22C55E"
    if value >= 80:
        return "#3B82F6"
    if value >= 75:
        return "#8B5CF6"
    if value >= 65:
        return "#F59E0B"
    return "#EF4444"


def score_badge(value: float | int | None, label: str = "") -> str:
    if value is None or pd.isna(value):
        shown = "—"
    else:
        shown = f"{float(value):.1f}"
    color = score_color(value)
    return f"""
    <div class="score-wrapper">
        <div class="score-circle" style="border-color:{color}; box-shadow:0 0 22px {color}44;">
            <span>{shown}</span>
        </div>
        <div class="score-caption">{label}</div>
    </div>
    """


def image_url(player_id: float | int | None) -> str | None:
    if player_id is None or pd.isna(player_id):
        return None
    return f"https://media.api-sports.io/football/players/{int(player_id)}.png"


def team_logo_url(team_id: float | int | None) -> str | None:
    if team_id is None or pd.isna(team_id):
        return None
    return f"https://media.api-sports.io/football/teams/{int(team_id)}.png"


def safe_options(values: Iterable[str]) -> list[str]:
    return sorted({str(value) for value in values if str(value).strip()})


def skill_dataframe(player: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Compétence": list(SKILL_COLUMNS.values()),
            "Note": [
                float(player[column]) if pd.notna(player[column]) else 0.0
                for column in SKILL_COLUMNS
            ],
        }
    )


def skill_chart(data: pd.DataFrame, color: str | None = None) -> alt.Chart:
    bar_color = color or "#22D3A7"
    bars = (
        alt.Chart(data)
        .mark_bar(cornerRadiusEnd=7, color=bar_color)
        .encode(
            x=alt.X("Note:Q", scale=alt.Scale(domain=[0, 100]), title=None),
            y=alt.Y("Compétence:N", sort=None, title=None),
            tooltip=[
                alt.Tooltip("Compétence:N"),
                alt.Tooltip("Note:Q", format=".1f"),
            ],
        )
    )
    labels = (
        alt.Chart(data)
        .mark_text(align="left", dx=6, color="#F8FAFC", fontWeight="bold")
        .encode(
            x=alt.X("Note:Q", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Compétence:N", sort=None),
            text=alt.Text("Note:Q", format=".1f"),
        )
    )
    return (bars + labels).properties(height=260)


def status_text(player: pd.Series) -> str:
    if bool(player.get("provisional", False)):
        return "Note provisoire"
    if bool(player.get("official_rating", False)):
        return "Note officielle"
    return "Données insuffisantes"


def render_header(data_file: Path) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <div>
                <div class="brand-row">
                    <div class="brand-ball">⚽</div>
                    <div>
                        <div class="brand-name">FootRate</div>
                        <div class="brand-subtitle">Les performances réelles transformées en notes simples</div>
                    </div>
                </div>
            </div>
            <div class="data-pill">Données : {data_file.name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ranking(df: pd.DataFrame) -> None:
    st.subheader("Classement des joueurs")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.4, 1, 1, 1])
    with filter_col1:
        search = st.text_input(
            "Rechercher",
            placeholder="Nom d'un joueur ou d'un club",
            key="ranking_search",
        )
    with filter_col2:
        position = st.selectbox(
            "Poste",
            ["Tous"] + safe_options(df["position_fr"]),
        )
    with filter_col3:
        club = st.selectbox(
            "Club",
            ["Tous"] + safe_options(df["team_name"]),
        )
    with filter_col4:
        minimum_minutes = st.selectbox(
            "Minutes minimum",
            [0, 450, 900, 1350],
            index=2,
        )

    filtered = df.copy()
    if search:
        mask = (
            filtered["player_name"].str.contains(search, case=False, na=False)
            | filtered["team_name"].str.contains(search, case=False, na=False)
        )
        filtered = filtered[mask]
    if position != "Tous":
        filtered = filtered[filtered["position_fr"] == position]
    if club != "Tous":
        filtered = filtered[filtered["team_name"] == club]
    filtered = filtered[filtered["minutes"].fillna(0) >= minimum_minutes]
    filtered = filtered.sort_values(["overall", "minutes"], ascending=[False, False]).copy()
    filtered["Rang"] = range(1, len(filtered) + 1)

    display = filtered[
        [
            "Rang", "player_name", "team_name", "position_fr",
            "minutes", "overall", "reliability",
        ]
    ].rename(
        columns={
            "player_name": "Joueur",
            "team_name": "Club",
            "position_fr": "Poste",
            "minutes": "Minutes",
            "overall": "Note",
            "reliability": "Fiabilité",
        }
    )
    display["Minutes"] = display["Minutes"].round(0).astype("Int64")
    display["Note"] = display["Note"].round(1)

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=620,
        column_config={
            "Rang": st.column_config.NumberColumn(width="small"),
            "Joueur": st.column_config.TextColumn(width="medium"),
            "Club": st.column_config.TextColumn(width="medium"),
            "Poste": st.column_config.TextColumn(width="small"),
            "Minutes": st.column_config.NumberColumn(format="%d"),
            "Note": st.column_config.ProgressColumn(
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
        },
    )
    st.caption(f"{len(filtered)} joueur(s) affiché(s).")


def render_player_card(player: pd.Series) -> None:
    identity_col, note_col, details_col = st.columns([1.1, 1, 1.8])

    with identity_col:
        photo = image_url(player.get("player_id"))
        if photo:
            st.image(photo, width=175)
        st.markdown(f"### {player['player_name']}")
        st.write(f"**{player['team_name']}**")
        st.write(f"{player['position_fr']} · {int(player['minutes'])} minutes")

    with note_col:
        st.markdown(score_badge(player["overall"], "Note FootRate"), unsafe_allow_html=True)
        status = status_text(player)
        status_class = "status-official" if status == "Note officielle" else "status-provisional"
        st.markdown(
            f'<div class="status-pill {status_class}">{status}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Fiabilité : {player.get('reliability', '—')}")

    with details_col:
        st.altair_chart(skill_chart(skill_dataframe(player)), use_container_width=True)

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric(
        "Profil statistique",
        "—" if pd.isna(player.get("profile_score")) else f"{player['profile_score']:.1f}",
    )
    metric2.metric(
        "Performance",
        "—" if pd.isna(player.get("performance_score")) else f"{player['performance_score']:.1f}",
    )
    metric3.metric(
        "Avant calibration",
        "—" if pd.isna(player.get("overall_precalibrated")) else f"{player['overall_precalibrated']:.1f}",
    )
    calibration = player.get("calibration_adjustment")
    metric4.metric(
        "Ajustement",
        "—" if pd.isna(calibration) else f"{calibration:+.1f}",
    )

    with st.expander("Comment lire cette fiche ?"):
        st.write(
            "La note générale combine le profil statistique, la performance moyenne "
            "et un ajustement limité lié à la position du joueur dans la population. "
            "La compétence « Dribble et maîtrise » peut être marquée par des données "
            "partielles lorsque l'API ne renseigne pas tous les dribbles réussis."
        )


def render_player_profile(df: pd.DataFrame) -> None:
    st.subheader("Fiche joueur")
    selected = st.selectbox(
        "Choisir un joueur",
        df["display_name"].tolist(),
        key="profile_player",
    )
    player = df.loc[df["display_name"] == selected].iloc[0]
    render_player_card(player)


def render_comparison(df: pd.DataFrame) -> None:
    st.subheader("Comparer deux joueurs")
    options = df["display_name"].tolist()
    left_col, right_col = st.columns(2)
    with left_col:
        player_a_name = st.selectbox(
            "Joueur 1",
            options,
            index=0,
            key="compare_a",
        )
    with right_col:
        default_second = 1 if len(options) > 1 else 0
        player_b_name = st.selectbox(
            "Joueur 2",
            options,
            index=default_second,
            key="compare_b",
        )

    player_a = df.loc[df["display_name"] == player_a_name].iloc[0]
    player_b = df.loc[df["display_name"] == player_b_name].iloc[0]

    head_a, versus, head_b = st.columns([1, 0.25, 1])
    with head_a:
        st.markdown(score_badge(player_a["overall"], player_a["player_name"]), unsafe_allow_html=True)
        st.caption(f"{player_a['team_name']} · {player_a['position_fr']}")
    with versus:
        st.markdown("<div class='versus'>VS</div>", unsafe_allow_html=True)
    with head_b:
        st.markdown(score_badge(player_b["overall"], player_b["player_name"]), unsafe_allow_html=True)
        st.caption(f"{player_b['team_name']} · {player_b['position_fr']}")

    comparison_rows = []
    for column, label in SKILL_COLUMNS.items():
        comparison_rows.extend(
            [
                {
                    "Compétence": label,
                    "Joueur": player_a["player_name"],
                    "Note": float(player_a[column]) if pd.notna(player_a[column]) else 0.0,
                },
                {
                    "Compétence": label,
                    "Joueur": player_b["player_name"],
                    "Note": float(player_b[column]) if pd.notna(player_b[column]) else 0.0,
                },
            ]
        )

    comparison_df = pd.DataFrame(comparison_rows)
    player_domain = [player_a["player_name"], player_b["player_name"]]
    player_colors = ["#7DD3FC", "#0EA5E9"]

    grouped_bars = (
        alt.Chart(comparison_df)
        .mark_bar(cornerRadiusEnd=5)
        .encode(
            x=alt.X(
                "Note:Q",
                scale=alt.Scale(domain=[0, 100]),
                title="Note sur 100",
            ),
            y=alt.Y(
                "Compétence:N",
                sort=list(SKILL_COLUMNS.values()),
                title=None,
                axis=alt.Axis(labelLimit=180),
            ),
            yOffset=alt.YOffset("Joueur:N"),
            color=alt.Color(
                "Joueur:N",
                scale=alt.Scale(domain=player_domain, range=player_colors),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Joueur:N"),
                alt.Tooltip("Compétence:N"),
                alt.Tooltip("Note:Q", format=".1f"),
            ],
        )
        .properties(height=420)
    )

    labels = (
        alt.Chart(comparison_df)
        .mark_text(align="left", dx=5, color="#F8FAFC", fontWeight="bold")
        .encode(
            x=alt.X("Note:Q", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Compétence:N", sort=list(SKILL_COLUMNS.values())),
            yOffset=alt.YOffset("Joueur:N"),
            text=alt.Text("Note:Q", format=".1f"),
        )
    )

    st.altair_chart(grouped_bars + labels, use_container_width=True)

    table = pd.DataFrame(
        {
            "Critère": ["Note générale", "Minutes", "Profil", "Performance"],
            player_a["player_name"]: [
                player_a["overall"],
                player_a["minutes"],
                player_a.get("profile_score"),
                player_a.get("performance_score"),
            ],
            player_b["player_name"]: [
                player_b["overall"],
                player_b["minutes"],
                player_b.get("profile_score"),
                player_b.get("performance_score"),
            ],
        }
    )
    st.dataframe(table, hide_index=True, use_container_width=True)


def render_methodology() -> None:
    st.subheader("Méthodologie")
    st.markdown(
        """
        **FootRate v0.6** transforme les statistiques cumulées de Ligue 1 en six compétences
        et une note générale sur 100.

        - **Frappe** : tirs, tirs cadrés, buts et efficacité.
        - **Passe** : volume et précision des passes.
        - **Création** : passes clés, passes décisives et actions créatrices.
        - **Dribble et maîtrise** : dribbles, maîtrise du ballon et fautes provoquées.
        - **Contribution défensive** : tacles, interceptions et duels défensifs.
        - **Impact physique** : duels gagnés, activité et disponibilité.

        Une note est **officielle à partir de 900 minutes**. Entre 450 et 899 minutes,
        elle est considérée comme provisoire. La calibration finale est limitée afin
        que le classement relatif ne déforme pas excessivement la performance brute.
        """
    )
    st.warning(
        "Le prototype ne mesure pas encore la vitesse réelle, les déplacements sans ballon "
        "ou le niveau technique complet. Ces dimensions nécessitent des données de tracking."
    )


st.set_page_config(
    page_title="FootRate",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        :root {
            --footrate-bg: #07101f;
            --footrate-card: #111c2f;
            --footrate-border: #22324b;
            --footrate-text: #f8fafc;
            --footrate-muted: #94a3b8;
            --footrate-accent: #22d3a7;
        }
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(34, 211, 167, 0.10), transparent 30%),
                linear-gradient(180deg, #07101f 0%, #0b1322 100%);
        }
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 1320px;
        }
        .hero {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            padding: 1.2rem 1.4rem;
            margin-bottom: 1.4rem;
            border: 1px solid var(--footrate-border);
            border-radius: 20px;
            background: linear-gradient(135deg, rgba(17, 28, 47, 0.96), rgba(13, 25, 42, 0.88));
            box-shadow: 0 18px 60px rgba(0, 0, 0, 0.22);
        }
        .brand-row {
            display: flex;
            align-items: center;
            gap: 0.9rem;
        }
        .brand-ball {
            display: grid;
            place-items: center;
            width: 54px;
            height: 54px;
            border-radius: 17px;
            background: rgba(34, 211, 167, 0.12);
            border: 1px solid rgba(34, 211, 167, 0.35);
            font-size: 28px;
        }
        .brand-name {
            color: var(--footrate-text);
            font-size: 2rem;
            font-weight: 850;
            line-height: 1;
        }
        .brand-subtitle {
            color: var(--footrate-muted);
            margin-top: 0.35rem;
        }
        .data-pill, .status-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            padding: 0.48rem 0.8rem;
            font-size: 0.82rem;
            font-weight: 700;
        }
        .data-pill {
            color: #9ff3da;
            background: rgba(34, 211, 167, 0.12);
            border: 1px solid rgba(34, 211, 167, 0.30);
        }
        .status-official {
            color: #bbf7d0;
            background: rgba(34, 197, 94, 0.14);
            border: 1px solid rgba(34, 197, 94, 0.34);
        }
        .status-provisional {
            color: #fde68a;
            background: rgba(245, 158, 11, 0.14);
            border: 1px solid rgba(245, 158, 11, 0.34);
        }
        .score-wrapper {
            text-align: center;
            padding: 0.4rem;
        }
        .score-circle {
            width: 112px;
            height: 112px;
            margin: 0 auto;
            border-radius: 50%;
            border: 7px solid;
            display: grid;
            place-items: center;
            background: rgba(15, 23, 42, 0.82);
        }
        .score-circle span {
            color: #f8fafc;
            font-size: 2.25rem;
            font-weight: 850;
        }
        .score-caption {
            color: #cbd5e1;
            font-weight: 750;
            margin-top: 0.6rem;
        }
        .versus {
            height: 155px;
            display: grid;
            place-items: center;
            color: #64748b;
            font-size: 1.4rem;
            font-weight: 900;
        }
        h1, h2, h3, p, label, .stMarkdown {
            color: #f8fafc;
        }
        div[data-testid="stMetric"] {
            background: rgba(17, 28, 47, 0.88);
            border: 1px solid var(--footrate-border);
            padding: 0.9rem 1rem;
            border-radius: 15px;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--footrate-border);
            border-radius: 14px;
            overflow: hidden;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.45rem;
        }
        .stTabs [data-baseweb="tab"] {
            background: rgba(17, 28, 47, 0.82);
            border-radius: 12px;
            padding: 0.65rem 1rem;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(34, 211, 167, 0.16);
            color: #9ff3da;
        }
        @media (max-width: 760px) {
            .hero {
                align-items: flex-start;
                flex-direction: column;
            }
            .brand-name {
                font-size: 1.65rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    data_file = find_data_file()
    data = load_data(str(data_file))
except Exception as exc:
    st.error("Impossible de charger les données FootRate.")
    st.code(str(exc))
    st.info(
        "Vérifie que le fichier footrate_official_v0_6.csv se trouve dans le dossier output."
    )
    st.stop()

render_header(data_file)

tab_ranking, tab_profile, tab_compare, tab_method = st.tabs(
    ["🏆 Classement", "👤 Fiche joueur", "⇄ Comparateur", "ℹ️ Méthodologie"]
)

with tab_ranking:
    render_ranking(data)

with tab_profile:
    render_player_profile(data)

with tab_compare:
    render_comparison(data)

with tab_method:
    render_methodology()
