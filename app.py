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



def player_tile(player: pd.Series, rank_label: str = "") -> str:
    photo = image_url(player.get("player_id")) or ""
    logo = team_logo_url(player.get("team_id")) or ""
    score = "—" if pd.isna(player.get("overall")) else f"{player['overall']:.1f}"
    score_colour = score_color(player.get("overall"))
    rank_html = f'<div class="tile-rank">{rank_label}</div>' if rank_label else ""
    return f"""
    <div class="player-tile">
        {rank_html}
        <div class="tile-top">
            <img class="tile-photo" src="{photo}" alt="{player['player_name']}">
            <div class="tile-score" style="border-color:{score_colour}; color:{score_colour};">
                {score}
            </div>
        </div>
        <div class="tile-name">{player['player_name']}</div>
        <div class="tile-club">
            <img src="{logo}" alt="{player['team_name']}">
            <span>{player['team_name']}</span>
        </div>
        <div class="tile-meta">{player['position_fr']} · {int(player['minutes'])} min</div>
    </div>
    """


def render_home(df: pd.DataFrame) -> None:
    st.subheader("Bienvenue sur FootRate")
    st.caption(
        "Découvrez les joueurs les mieux notés de Ligue 1 2024-2025 "
        "à partir de leurs performances réelles."
    )

    best_player = df.sort_values(["overall", "minutes"], ascending=[False, False]).iloc[0]
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Joueurs évalués", f"{len(df)}")
    metric_2.metric("Clubs représentés", f"{df['team_name'].nunique()}")
    metric_3.metric("Meilleure note", f"{best_player['overall']:.1f}")
    metric_4.metric("Note moyenne", f"{df['overall'].mean():.1f}")

    st.markdown("### Podium général")
    podium = df.sort_values(["overall", "minutes"], ascending=[False, False]).head(3)
    podium_columns = st.columns(3)
    medals = ["🥇 1er", "🥈 2e", "🥉 3e"]
    for column, (_, player), medal in zip(podium_columns, podium.iterrows(), medals):
        with column:
            st.markdown(player_tile(player, medal), unsafe_allow_html=True)

    st.markdown("### Meilleurs joueurs par poste")
    position_columns = st.columns(3)
    position_groups = [
        ("Attaquants", "Attaquant", "Attacker"),
        ("Milieux", "Milieu", "Midfielder"),
        ("Défenseurs", "Défenseur", "Defender"),
    ]
    for column, (title, translated_position, raw_position) in zip(
        position_columns, position_groups
    ):
        with column:
            st.markdown(f"#### {title}")
            group = (
                df[df["position"] == raw_position]
                .sort_values(["overall", "minutes"], ascending=[False, False])
                .head(3)
            )
            for rank, (_, player) in enumerate(group.iterrows(), start=1):
                logo = team_logo_url(player.get("team_id")) or ""
                st.markdown(
                    f"""
                    <div class="mini-ranking">
                        <div class="mini-rank">{rank}</div>
                        <img src="{logo}" alt="{player['team_name']}">
                        <div class="mini-identity">
                            <strong>{player['player_name']}</strong>
                            <span>{player['team_name']}</span>
                        </div>
                        <div class="mini-score">{player['overall']:.1f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.info(
        "Cette version utilise les données de Ligue 1 2024-2025. "
        "La prochaine étape sera l'actualisation vers la saison en cours."
    )



@st.cache_data(show_spinner=False)
def build_club_summary(df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict] = []

    for (team_id, team_name), group in df.groupby(
        ["team_id", "team_name"], dropna=False
    ):
        group = group.sort_values(
            ["overall", "minutes"], ascending=[False, False]
        ).copy()

        top_eleven = group.head(11)
        position_scores: dict[str, float | None] = {}
        position_limits = {
            "Attacker": 3,
            "Midfielder": 4,
            "Defender": 4,
        }

        for position, limit in position_limits.items():
            position_group = (
                group[group["position"] == position]
                .sort_values(["overall", "minutes"], ascending=[False, False])
                .head(limit)
            )
            position_scores[position] = (
                float(position_group["overall"].mean())
                if not position_group.empty
                else None
            )

        best_player = group.iloc[0]
        records.append(
            {
                "team_id": team_id,
                "team_name": team_name,
                "squad_score": float(top_eleven["overall"].mean()),
                "average_score": float(group["overall"].mean()),
                "players_count": int(len(group)),
                "attack_score": position_scores["Attacker"],
                "midfield_score": position_scores["Midfielder"],
                "defence_score": position_scores["Defender"],
                "best_player": best_player["player_name"],
                "best_player_score": float(best_player["overall"]),
                "best_player_id": best_player["player_id"],
                "minutes_total": float(group["minutes"].sum()),
            }
        )

    summary = pd.DataFrame(records)
    summary = summary.sort_values(
        ["squad_score", "average_score"], ascending=[False, False]
    ).reset_index(drop=True)
    summary["rank"] = range(1, len(summary) + 1)
    return summary


def club_score_chart(club_row: pd.Series) -> alt.Chart:
    chart_data = pd.DataFrame(
        {
            "Secteur": ["Attaque", "Milieu", "Défense"],
            "Note": [
                club_row.get("attack_score"),
                club_row.get("midfield_score"),
                club_row.get("defence_score"),
            ],
        }
    ).dropna()

    bars = (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusEnd=7, color="#22D3A7")
        .encode(
            x=alt.X(
                "Note:Q",
                scale=alt.Scale(domain=[0, 100]),
                title="Note sur 100",
            ),
            y=alt.Y("Secteur:N", sort=["Attaque", "Milieu", "Défense"], title=None),
            tooltip=[
                alt.Tooltip("Secteur:N"),
                alt.Tooltip("Note:Q", format=".1f"),
            ],
        )
        .properties(height=190)
    )

    labels = (
        alt.Chart(chart_data)
        .mark_text(align="left", dx=6, color="#F8FAFC", fontWeight="bold")
        .encode(
            x=alt.X("Note:Q", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Secteur:N", sort=["Attaque", "Milieu", "Défense"]),
            text=alt.Text("Note:Q", format=".1f"),
        )
    )
    return bars + labels


def render_club_comparison(summary: pd.DataFrame) -> None:
    st.markdown("### Comparer deux clubs")
    options = summary["team_name"].tolist()

    left_selector, right_selector = st.columns(2)
    with left_selector:
        club_a_name = st.selectbox(
            "Club 1",
            options,
            index=0,
            key="club_compare_a",
        )
    with right_selector:
        club_b_name = st.selectbox(
            "Club 2",
            options,
            index=1 if len(options) > 1 else 0,
            key="club_compare_b",
        )

    club_a = summary.loc[summary["team_name"] == club_a_name].iloc[0]
    club_b = summary.loc[summary["team_name"] == club_b_name].iloc[0]

    head_a, versus, head_b = st.columns([1, 0.25, 1])
    with head_a:
        logo_a = team_logo_url(club_a.get("team_id"))
        if logo_a:
            st.image(logo_a, width=90)
        st.markdown(f"### {club_a['team_name']}")
        st.markdown(
            score_badge(club_a["squad_score"], "Note d'effectif"),
            unsafe_allow_html=True,
        )
    with versus:
        st.markdown("<div class='versus'>VS</div>", unsafe_allow_html=True)
    with head_b:
        logo_b = team_logo_url(club_b.get("team_id"))
        if logo_b:
            st.image(logo_b, width=90)
        st.markdown(f"### {club_b['team_name']}")
        st.markdown(
            score_badge(club_b["squad_score"], "Note d'effectif"),
            unsafe_allow_html=True,
        )

    comparison_rows = []
    criteria = [
        ("Note d'effectif", "squad_score"),
        ("Moyenne des joueurs", "average_score"),
        ("Attaque", "attack_score"),
        ("Milieu", "midfield_score"),
        ("Défense", "defence_score"),
    ]
    for label, column in criteria:
        comparison_rows.extend(
            [
                {
                    "Critère": label,
                    "Club": club_a["team_name"],
                    "Note": club_a[column],
                },
                {
                    "Critère": label,
                    "Club": club_b["team_name"],
                    "Note": club_b[column],
                },
            ]
        )

    comparison_df = pd.DataFrame(comparison_rows).dropna()
    club_domain = [club_a["team_name"], club_b["team_name"]]

    bars = (
        alt.Chart(comparison_df)
        .mark_bar(cornerRadiusEnd=5)
        .encode(
            x=alt.X("Note:Q", scale=alt.Scale(domain=[0, 100]), title="Note sur 100"),
            y=alt.Y("Critère:N", sort=[label for label, _ in criteria], title=None),
            yOffset=alt.YOffset("Club:N"),
            color=alt.Color(
                "Club:N",
                scale=alt.Scale(
                    domain=club_domain,
                    range=["#7DD3FC", "#22D3A7"],
                ),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Club:N"),
                alt.Tooltip("Critère:N"),
                alt.Tooltip("Note:Q", format=".1f"),
            ],
        )
        .properties(height=350)
    )

    labels = (
        alt.Chart(comparison_df)
        .mark_text(align="left", dx=5, color="#F8FAFC", fontWeight="bold")
        .encode(
            x=alt.X("Note:Q", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Critère:N", sort=[label for label, _ in criteria]),
            yOffset=alt.YOffset("Club:N"),
            text=alt.Text("Note:Q", format=".1f"),
        )
    )
    st.altair_chart(bars + labels, use_container_width=True)


def render_clubs(df: pd.DataFrame) -> None:
    st.subheader("Clubs")
    st.caption(
        "La note d'effectif correspond à la moyenne des onze joueurs les mieux "
        "notés du club dans les données disponibles."
    )

    summary = build_club_summary(df)
    ranking_tab, profile_tab, comparison_tab = st.tabs(
        ["Classement des clubs", "Fiche club", "Comparateur"]
    )

    with ranking_tab:
        display = summary[
            [
                "rank",
                "team_name",
                "players_count",
                "squad_score",
                "average_score",
                "best_player",
            ]
        ].rename(
            columns={
                "rank": "Rang",
                "team_name": "Club",
                "players_count": "Joueurs notés",
                "squad_score": "Note d'effectif",
                "average_score": "Moyenne",
                "best_player": "Meilleur joueur",
            }
        )
        display["Note d'effectif"] = display["Note d'effectif"].round(1)
        display["Moyenne"] = display["Moyenne"].round(1)

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=610,
            column_config={
                "Rang": st.column_config.NumberColumn(width="small"),
                "Club": st.column_config.TextColumn(width="medium"),
                "Joueurs notés": st.column_config.NumberColumn(width="small"),
                "Note d'effectif": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Moyenne": st.column_config.NumberColumn(format="%.1f"),
                "Meilleur joueur": st.column_config.TextColumn(width="medium"),
            },
        )
        st.info(
            "Cette note mesure la qualité statistique de l'effectif évalué. "
            "Elle ne remplace pas encore le classement sportif réel du championnat."
        )

    with profile_tab:
        selected_club_name = st.selectbox(
            "Choisir un club",
            summary["team_name"].tolist(),
            key="club_profile_selector",
        )
        club_row = summary.loc[
            summary["team_name"] == selected_club_name
        ].iloc[0]
        club_players = (
            df[df["team_name"] == selected_club_name]
            .sort_values(["overall", "minutes"], ascending=[False, False])
            .copy()
        )

        identity_col, note_col, chart_col = st.columns([1, 1, 1.8])
        with identity_col:
            logo = team_logo_url(club_row.get("team_id"))
            if logo:
                st.image(logo, width=145)
            st.markdown(f"## {club_row['team_name']}")
            st.write(f"**{int(club_row['players_count'])} joueurs notés**")
            st.caption(
                f"Meilleur joueur : {club_row['best_player']} "
                f"({club_row['best_player_score']:.1f})"
            )

        with note_col:
            st.markdown(
                score_badge(club_row["squad_score"], "Note d'effectif"),
                unsafe_allow_html=True,
            )
            st.caption("Moyenne des 11 joueurs les mieux notés")

        with chart_col:
            st.altair_chart(
                club_score_chart(club_row),
                use_container_width=True,
            )

        metric_1, metric_2, metric_3 = st.columns(3)
        metric_1.metric("Moyenne de l'effectif", f"{club_row['average_score']:.1f}")
        metric_2.metric("Joueurs évalués", f"{int(club_row['players_count'])}")
        metric_3.metric(
            "Meilleure note individuelle",
            f"{club_row['best_player_score']:.1f}",
        )

        st.markdown("### Meilleurs joueurs du club")
        top_players = club_players.head(3)
        top_columns = st.columns(3)
        for column, (_, player), rank_label in zip(
            top_columns,
            top_players.iterrows(),
            ["🥇 1er", "🥈 2e", "🥉 3e"],
        ):
            with column:
                st.markdown(
                    player_tile(player, rank_label),
                    unsafe_allow_html=True,
                )

        st.markdown("### Effectif évalué")
        roster = club_players[
            [
                "player_name",
                "position_fr",
                "minutes",
                "overall",
                "reliability",
            ]
        ].rename(
            columns={
                "player_name": "Joueur",
                "position_fr": "Poste",
                "minutes": "Minutes",
                "overall": "Note",
                "reliability": "Fiabilité",
            }
        )
        roster["Minutes"] = roster["Minutes"].round(0).astype("Int64")
        roster["Note"] = roster["Note"].round(1)

        st.dataframe(
            roster,
            use_container_width=True,
            hide_index=True,
            height=440,
            column_config={
                "Joueur": st.column_config.TextColumn(width="medium"),
                "Poste": st.column_config.TextColumn(width="small"),
                "Minutes": st.column_config.NumberColumn(format="%d"),
                "Note": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Fiabilité": st.column_config.TextColumn(width="small"),
            },
        )

    with comparison_tab:
        render_club_comparison(summary)


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
        club_logo = team_logo_url(player.get("team_id"))
        if club_logo:
            club_col1, club_col2 = st.columns([0.22, 1])
            with club_col1:
                st.image(club_logo, width=42)
            with club_col2:
                st.write(f"**{player['team_name']}**")
        else:
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

        La **note d'effectif d'un club** correspond à la moyenne des onze joueurs
        les mieux notés du club dans les données disponibles. Elle mesure la qualité
        statistique de l'effectif et non ses résultats sportifs réels.
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
        .player-tile {
            position: relative;
            min-height: 305px;
            padding: 1rem;
            border: 1px solid var(--footrate-border);
            border-radius: 18px;
            background: linear-gradient(155deg, rgba(17, 28, 47, 0.98), rgba(10, 20, 35, 0.94));
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.22);
            overflow: hidden;
        }
        .tile-rank {
            position: absolute;
            top: 0.75rem;
            left: 0.75rem;
            z-index: 2;
            padding: 0.3rem 0.55rem;
            border-radius: 999px;
            background: rgba(34, 211, 167, 0.14);
            color: #9ff3da;
            font-size: 0.78rem;
            font-weight: 800;
        }
        .tile-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.75rem;
            margin-top: 1.2rem;
        }
        .tile-photo {
            width: 132px;
            height: 132px;
            object-fit: cover;
            object-position: top;
            border-radius: 16px;
            background: #ffffff;
        }
        .tile-score {
            display: grid;
            place-items: center;
            width: 70px;
            height: 70px;
            flex: 0 0 70px;
            border: 5px solid;
            border-radius: 50%;
            background: rgba(7, 16, 31, 0.9);
            font-size: 1.35rem;
            font-weight: 900;
        }
        .tile-name {
            margin-top: 0.85rem;
            color: #f8fafc;
            font-size: 1.2rem;
            font-weight: 850;
        }
        .tile-club {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            margin-top: 0.5rem;
            color: #cbd5e1;
            font-size: 0.9rem;
        }
        .tile-club img {
            width: 25px;
            height: 25px;
            object-fit: contain;
        }
        .tile-meta {
            margin-top: 0.55rem;
            color: #94a3b8;
            font-size: 0.82rem;
        }
        .mini-ranking {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            min-height: 58px;
            margin-bottom: 0.55rem;
            padding: 0.55rem 0.65rem;
            border: 1px solid var(--footrate-border);
            border-radius: 12px;
            background: rgba(17, 28, 47, 0.82);
        }
        .mini-ranking img {
            width: 32px;
            height: 32px;
            object-fit: contain;
        }
        .mini-rank {
            display: grid;
            place-items: center;
            width: 24px;
            height: 24px;
            flex: 0 0 24px;
            border-radius: 50%;
            background: rgba(34, 211, 167, 0.13);
            color: #9ff3da;
            font-weight: 850;
        }
        .mini-identity {
            min-width: 0;
            flex: 1;
        }
        .mini-identity strong, .mini-identity span {
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .mini-identity strong {
            color: #f8fafc;
            font-size: 0.88rem;
        }
        .mini-identity span {
            color: #94a3b8;
            font-size: 0.74rem;
        }
        .mini-score {
            color: #22d3a7;
            font-size: 1rem;
            font-weight: 900;
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
            .player-tile {
                min-height: 275px;
            }
            .tile-photo {
                width: 105px;
                height: 105px;
            }
            .tile-score {
                width: 62px;
                height: 62px;
                flex-basis: 62px;
                font-size: 1.15rem;
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

tab_home, tab_ranking, tab_clubs, tab_profile, tab_compare, tab_method = st.tabs(
    [
        "🏠 Accueil",
        "🏆 Joueurs",
        "⚽ Clubs",
        "👤 Fiche joueur",
        "⇄ Comparateur",
        "ℹ️ Méthodologie",
    ]
)

with tab_home:
    render_home(data)

with tab_ranking:
    render_ranking(data)

with tab_clubs:
    render_clubs(data)

with tab_profile:
    render_player_profile(data)

with tab_compare:
    render_comparison(data)

with tab_method:
    render_methodology()
