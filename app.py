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
        Path("output/footrate_official_v0_8.csv"),
        Path("output/footrate_official_v0_7.csv"),
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



def find_competition_files() -> tuple[Path | None, Path | None]:
    table_candidates = [
        Path("output/footrate_competitions_table_history_v1_1.csv"),
        Path("output/footrate_ligue1_table_history_v1_0.csv"),
        Path("output/footrate_ligue1_table_v0_9.csv"),
    ]
    results_candidates = [
        Path("output/footrate_competitions_results_history_v1_1.csv"),
        Path("output/footrate_ligue1_results_history_v1_0.csv"),
        Path("output/footrate_ligue1_results_v0_9.csv"),
    ]

    table_path = next((path for path in table_candidates if path.exists()), None)
    results_path = next((path for path in results_candidates if path.exists()), None)
    return table_path, results_path


@st.cache_data(show_spinner=False)
def load_competition_data(
    table_path_text: str | None,
    results_path_text: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not table_path_text:
        return pd.DataFrame(), pd.DataFrame()

    table = pd.read_csv(
        Path(table_path_text),
        sep=";",
        encoding="utf-8-sig",
    )

    if "season" not in table.columns:
        table["season"] = 2024
    if "season_label" not in table.columns:
        table["season_label"] = "2024-2025"
    if "competition_id" not in table.columns:
        table["competition_id"] = 61
    if "competition_name" not in table.columns:
        table["competition_name"] = "Ligue 1"

    table_numeric = [
        "competition_id", "season", "team_id", "rank", "points", "played",
        "wins", "draws", "losses", "goals_for", "goals_against",
        "goal_diff",
    ]
    for column in table_numeric:
        if column not in table.columns:
            table[column] = float("nan")
        table[column] = pd.to_numeric(table[column], errors="coerce")

    for column in [
        "competition_name", "season_label", "team_name",
        "standing_form", "description",
    ]:
        if column not in table.columns:
            table[column] = ""
        table[column] = table[column].fillna("").astype(str)

    results = pd.DataFrame()
    if results_path_text and Path(results_path_text).exists():
        results = pd.read_csv(
            Path(results_path_text),
            sep=";",
            encoding="utf-8-sig",
        )

        if "season" not in results.columns:
            results["season"] = 2024
        if "season_label" not in results.columns:
            results["season_label"] = "2024-2025"
        if "competition_id" not in results.columns:
            results["competition_id"] = 61
        if "competition_name" not in results.columns:
            results["competition_name"] = "Ligue 1"

        result_numeric = [
            "competition_id", "season", "team_id", "fixture_id",
            "opponent_id", "goals_for", "goals_against", "recency_order",
        ]
        for column in result_numeric:
            if column not in results.columns:
                results[column] = float("nan")
            results[column] = pd.to_numeric(results[column], errors="coerce")

        for column in [
            "competition_name", "season_label", "team_name",
            "opponent_name", "opponent_logo", "date", "round",
            "home_away", "result", "score",
        ]:
            if column not in results.columns:
                results[column] = ""
            results[column] = results[column].fillna("").astype(str)

        results["date_parsed"] = pd.to_datetime(
            results["date"],
            errors="coerce",
            utc=True,
        )

    return table, results



def find_team_match_stats_file() -> Path | None:
    candidates = [
        Path("output/sportsrate_team_match_stats_v1_2.csv"),
        Path("output/footrate_team_match_stats_v1_2.csv"),
    ]
    return next((path for path in candidates if path.exists()), None)


@st.cache_data(show_spinner=False)
def load_team_match_stats(path_text: str | None) -> pd.DataFrame:
    if not path_text:
        return pd.DataFrame()

    path = Path(path_text)
    if not path.exists():
        return pd.DataFrame()

    stats = pd.read_csv(path, sep=";", encoding="utf-8-sig")

    numeric_columns = [
        "competition_id", "season", "fixture_id", "matchday",
        "team_id", "opponent_id", "goals_for", "goals_against",
        "possession", "shots_total", "shots_on_target",
        "shots_off_target", "blocked_shots", "shots_inside_box",
        "shots_outside_box", "fouls", "corners", "offsides",
        "yellow_cards", "red_cards", "goalkeeper_saves",
        "passes_total", "passes_accurate", "pass_accuracy",
    ]
    for column in numeric_columns:
        if column not in stats.columns:
            stats[column] = float("nan")
        stats[column] = pd.to_numeric(stats[column], errors="coerce")

    text_columns = [
        "competition_name", "season_label", "round", "date",
        "team_name", "team_logo", "opponent_name", "opponent_logo",
        "home_away", "result", "score",
    ]
    for column in text_columns:
        if column not in stats.columns:
            stats[column] = ""
        stats[column] = stats[column].fillna("").astype(str)

    stats["date_parsed"] = pd.to_datetime(
        stats["date"],
        errors="coerce",
        utc=True,
    )
    return stats


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
        "calibration_adjustment", "overall", "form", "form_trend",
        "matches_in_form", "club_form", "club_form_trend",
    ]
    for column in numeric_columns:
        if column not in df.columns:
            df[column] = float("nan")
        df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)

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

    if "form_label" not in df.columns:
        df["form_label"] = "Non disponible"
    else:
        df["form_label"] = df["form_label"].fillna("Non disponible").astype(str)

    if "form_reliability" not in df.columns:
        df["form_reliability"] = df["matches_in_form"].apply(
            lambda value: (
                "Élevée" if pd.notna(value) and value >= 5
                else "Moyenne" if pd.notna(value) and value >= 3
                else "Faible" if pd.notna(value) and value >= 1
                else "Non disponible"
            )
        )
    else:
        df["form_reliability"] = (
            df["form_reliability"]
            .fillna("Non disponible")
            .astype(str)
        )

    if "club_form_label" not in df.columns:
        df["club_form_label"] = "Non disponible"
    else:
        df["club_form_label"] = df["club_form_label"].fillna("Non disponible").astype(str)
    df["display_name"] = (
        df["player_name"].astype(str)
        + " — "
        + df["team_name"].astype(str)
    )

    df = df.dropna(subset=["overall"]).copy()
    df = df.sort_values(["overall", "minutes"], ascending=[False, False])
    df["rank"] = range(1, len(df) + 1)
    return df



def trend_icon(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "•"
    value = float(value)
    if value >= 3:
        return "↗"
    if value <= -3:
        return "↘"
    return "→"


def trend_text(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "Non disponible"
    value = float(value)
    if value >= 3:
        return "En hausse"
    if value <= -3:
        return "En baisse"
    return "Stable"


def trend_badge(value: float | int | None) -> str:
    label = trend_text(value)
    icon = trend_icon(value)
    if value is None or pd.isna(value):
        css_class = "trend-neutral"
        shown = ""
    else:
        numeric = float(value)
        css_class = (
            "trend-up" if numeric >= 3
            else "trend-down" if numeric <= -3
            else "trend-neutral"
        )
        shown = f" {numeric:+.1f}"
    return f'<span class="trend-pill {css_class}">{icon} {label}{shown}</span>'


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



def player_form_tile(player: pd.Series) -> str:
    """Construit une carte HTML compacte, sans ligne vide Markdown."""
    photo = image_url(player.get("player_id")) or ""
    logo = team_logo_url(player.get("team_id")) or ""

    form_value = player.get("form")
    overall_value = player.get("overall")
    matches_value = player.get("matches_in_form")
    reliability = player.get("form_reliability", "Non disponible")

    form_shown = "—" if pd.isna(form_value) else f"{float(form_value):.1f}"
    overall_shown = (
        "—" if pd.isna(overall_value) else f"{float(overall_value):.1f}"
    )
    matches_shown = (
        "—" if pd.isna(matches_value) else f"{int(matches_value)}/5 matchs"
    )

    form_colour = score_color(form_value)
    trend_html = trend_badge(player.get("form_trend"))

    return (
        f'<div class="form-player-card">'
        f'<div class="form-card-label">🔥 Forme récente</div>'
        f'<div class="form-card-main">'
        f'<img class="form-card-photo" src="{photo}" '
        f'alt="{player["player_name"]}">'
        f'<div class="form-score-block">'
        f'<div class="form-score-circle" '
        f'style="border-color:{form_colour}; '
        f'box-shadow:0 0 22px {form_colour}44;">'
        f'<span>{form_shown}</span>'
        f'</div>'
        f'<div class="form-score-caption">Forme récente</div>'
        f'</div>'
        f'</div>'
        f'<div class="form-card-name">{player["player_name"]}</div>'
        f'<div class="form-card-club">'
        f'<img src="{logo}" alt="{player["team_name"]}">'
        f'<span>{player["team_name"]}</span>'
        f'</div>'
        f'<div class="form-card-details">'
        f'<div class="form-detail-box">'
        f'<span>Note générale</span>'
        f'<strong>{overall_shown}</strong>'
        f'</div>'
        f'<div class="form-detail-box">'
        f'<span>Fiabilité</span>'
        f'<strong>{reliability}</strong>'
        f'</div>'
        f'</div>'
        f'<div class="form-card-footer">'
        f'<span>{matches_shown}</span>'
        f'{trend_html}'
        f'</div>'
        f'</div>'
    )


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

    form_available = df["form"].notna().sum() > 0
    if form_available:
        st.markdown("### Joueurs en forme")
        st.caption(
            "Le grand score correspond à la forme récente. "
            "La note générale de saison est affichée séparément."
        )
        in_form = (
            df[df["form"].notna() & df["matches_in_form"].ge(3)]
            .sort_values(["form", "overall"], ascending=[False, False])
            .head(3)
        )
        if not in_form.empty:
            form_columns = st.columns(3)
            for column, (_, player) in zip(form_columns, in_form.iterrows()):
                with column:
                    st.markdown(
                        player_form_tile(player),
                        unsafe_allow_html=True,
                    )

        club_dynamics = (
            df[["team_id", "team_name", "club_form", "club_form_trend"]]
            .dropna(subset=["club_form"])
            .drop_duplicates(subset=["team_id"])
            .sort_values(["club_form", "club_form_trend"], ascending=[False, False])
            .head(3)
        )
        if not club_dynamics.empty:
            st.markdown("#### Clubs les plus en forme")
            club_columns = st.columns(3)
            for column, (_, club) in zip(club_columns, club_dynamics.iterrows()):
                with column:
                    logo = team_logo_url(club.get("team_id")) or ""
                    st.markdown(
                        f"""
                        <div class="club-form-card">
                            <img src="{logo}" alt="{club['team_name']}">
                            <div>
                                <strong>{club['team_name']}</strong>
                                <span>Forme : {club['club_form']:.1f}</span>
                            </div>
                            {trend_badge(club.get("club_form_trend"))}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

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




def french_standing_form(raw_form: str) -> str:
    translation = {"W": "V", "D": "N", "L": "D"}
    letters = [translation.get(letter.upper(), letter.upper()) for letter in raw_form]
    return " ".join(letters) if letters else "—"


def performance_gap_label(gap: float | int | None) -> str:
    if gap is None or pd.isna(gap):
        return "Non comparable"
    gap = float(gap)
    if gap >= 2:
        return "Surperformance sportive"
    if gap <= -2:
        return "Sous-performance sportive"
    return "Conforme à l'effectif"


def result_css_class(result: str) -> str:
    return {
        "V": "match-win",
        "N": "match-draw",
        "D": "match-loss",
    }.get(str(result).upper(), "match-neutral")


def recent_result_card(result: pd.Series) -> str:
    date_value = result.get("date_parsed")
    if pd.notna(date_value):
        date_text = pd.Timestamp(date_value).strftime("%d/%m/%Y")
    else:
        date_text = str(result.get("date", ""))[:10]

    opponent_logo = result.get("opponent_logo", "") or ""
    result_letter = str(result.get("result", "—")).upper()
    css_class = result_css_class(result_letter)
    location = "Domicile" if result.get("home_away") == "home" else "Extérieur"

    return (
        f'<div class="recent-match-card">'
        f'<div class="recent-match-top">'
        f'<span class="match-result-pill {css_class}">{result_letter}</span>'
        f'<span>{date_text}</span>'
        f'</div>'
        f'<div class="recent-opponent">'
        f'<img src="{opponent_logo}" alt="{result.get("opponent_name", "")}">'
        f'<strong>{result.get("opponent_name", "")}</strong>'
        f'</div>'
        f'<div class="recent-score">{result.get("score", "—")}</div>'
        f'<div class="recent-location">{location}</div>'
        f'</div>'
    )


def render_recent_results(
    recent_results: pd.DataFrame,
    team_id: float | int | None,
    heading: str = "Cinq derniers résultats",
) -> None:
    if (
        recent_results.empty
        or team_id is None
        or pd.isna(team_id)
    ):
        st.caption("Résultats récents non disponibles.")
        return

    team_results = (
        recent_results[
            pd.to_numeric(recent_results["team_id"], errors="coerce")
            == int(team_id)
        ]
        .sort_values("recency_order")
        .head(5)
    )

    if team_results.empty:
        st.caption("Résultats récents non disponibles.")
        return

    st.markdown(f"### {heading}")
    columns = st.columns(len(team_results))
    for column, (_, result) in zip(columns, team_results.iterrows()):
        with column:
            st.markdown(
                recent_result_card(result),
                unsafe_allow_html=True,
            )


def build_sporting_comparison(
    player_data: pd.DataFrame,
    competition_table: pd.DataFrame,
) -> pd.DataFrame:
    if competition_table.empty:
        return pd.DataFrame()

    club_summary = build_club_summary(player_data)
    official_summary = club_summary[
        club_summary["eligible_for_ranking"]
    ].copy()

    comparison = competition_table.merge(
        official_summary[
            ["team_id", "rank", "squad_score", "coverage_status"]
        ].rename(columns={"rank": "footrate_rank"}),
        on="team_id",
        how="left",
    )

    comparison["rank_gap"] = (
        pd.to_numeric(comparison["footrate_rank"], errors="coerce")
        - pd.to_numeric(comparison["rank"], errors="coerce")
    )
    comparison["performance_reading"] = comparison["rank_gap"].apply(
        performance_gap_label
    )
    return comparison.sort_values("rank").reset_index(drop=True)


def render_league(
    player_data: pd.DataFrame,
    competition_table: pd.DataFrame,
    recent_results: pd.DataFrame,
) -> None:
    st.subheader("Championnats européens")

    if competition_table.empty:
        st.warning(
            "Les données multi-compétitions ne sont pas encore présentes. "
            "Exécute `footrate_multileague_update.py`, puis ajoute les deux CSV "
            "v1.1 dans le dossier `output` de GitHub."
        )
        return

    competition_labels = {
        "Ligue 1": "🇫🇷 Ligue 1",
        "Premier League": "🏴 Premier League",
        "La Liga": "🇪🇸 Liga",
        "Serie A": "🇮🇹 Serie A",
        "Bundesliga": "🇩🇪 Bundesliga",
    }
    competition_order = {
        "Ligue 1": 1,
        "Premier League": 2,
        "La Liga": 3,
        "Serie A": 4,
        "Bundesliga": 5,
    }

    competition_options = (
        competition_table[
            ["competition_id", "competition_name"]
        ]
        .drop_duplicates()
        .copy()
    )
    competition_options["display_name"] = competition_options[
        "competition_name"
    ].map(competition_labels).fillna(
        competition_options["competition_name"]
    )
    competition_options["display_order"] = competition_options[
        "competition_name"
    ].map(competition_order).fillna(99)
    competition_options = competition_options.sort_values(
        ["display_order", "competition_name"]
    )

    default_index = 0
    ligue_1_matches = competition_options.index[
        competition_options["competition_name"].eq("Ligue 1")
    ].tolist()
    if ligue_1_matches:
        default_index = competition_options.index.tolist().index(
            ligue_1_matches[0]
        )

    selector_col1, selector_col2 = st.columns(2)
    with selector_col1:
        selected_competition_display = st.selectbox(
            "Compétition",
            competition_options["display_name"].tolist(),
            index=default_index,
            key="multi_competition_selector",
        )

    selected_competition_row = competition_options.loc[
        competition_options["display_name"].eq(
            selected_competition_display
        )
    ].iloc[0]
    selected_competition_id = int(
        selected_competition_row["competition_id"]
    )
    selected_competition_name = str(
        selected_competition_row["competition_name"]
    )

    competition_seasons = (
        competition_table[
            competition_table["competition_id"].eq(
                selected_competition_id
            )
        ][["season", "season_label"]]
        .drop_duplicates()
        .sort_values("season", ascending=False)
    )
    season_labels = competition_seasons["season_label"].tolist()

    with selector_col2:
        selected_label = st.selectbox(
            "Saison",
            season_labels,
            index=0,
            key=f"multi_season_{selected_competition_id}",
        )

    selected_season = int(
        competition_seasons.loc[
            competition_seasons["season_label"].eq(selected_label),
            "season",
        ].iloc[0]
    )

    standings = (
        competition_table[
            competition_table["competition_id"].eq(
                selected_competition_id
            )
            & competition_table["season"].eq(selected_season)
        ]
        .sort_values("rank")
        .copy()
    )

    selected_results = (
        recent_results[
            recent_results["competition_id"].eq(
                selected_competition_id
            )
            & recent_results["season"].eq(selected_season)
        ].copy()
        if not recent_results.empty
        else pd.DataFrame()
    )

    if standings.empty:
        st.error(
            f"Aucune donnée trouvée pour {selected_competition_name} "
            f"{selected_label}."
        )
        return

    st.caption(
        f"Classement final, résultats récents et historique de "
        f"{selected_competition_name} pour la saison {selected_label}."
    )

    leader = standings.iloc[0]
    best_attack = standings.sort_values(
        ["goals_for", "goal_diff"],
        ascending=[False, False],
    ).iloc[0]
    best_defence = standings.sort_values(
        ["goals_against", "goal_diff"],
        ascending=[True, False],
    ).iloc[0]

    summary_cards = [
        (
            "Champion",
            leader["team_name"],
            f"{int(leader['points'])} points",
        ),
        (
            "Meilleure attaque",
            best_attack["team_name"],
            f"{int(best_attack['goals_for'])} buts",
        ),
        (
            "Meilleure défense",
            best_defence["team_name"],
            f"{int(best_defence['goals_against'])} buts encaissés",
        ),
        (
            "Différence de buts du champion",
            f"{int(leader['goal_diff']):+d}",
            selected_label,
        ),
    ]

    card_columns = st.columns(4)
    for column, (label, value, detail) in zip(
        card_columns,
        summary_cards,
    ):
        with column:
            st.markdown(
                f"""
                <div class="season-summary-card">
                    <span>{label}</span>
                    <strong>{value}</strong>
                    <small>{detail}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

    (
        standings_tab,
        analysis_tab,
        results_tab,
        history_tab,
    ) = st.tabs(
        [
            "Classement sportif",
            "Sportif vs FootRate",
            "Résultats récents",
            "Évolution sur 3 saisons",
        ]
    )

    with standings_tab:
        display = standings[
            [
                "rank", "team_name", "played", "wins", "draws",
                "losses", "goals_for", "goals_against",
                "goal_diff", "points", "standing_form",
            ]
        ].rename(
            columns={
                "rank": "Rang",
                "team_name": "Club",
                "played": "J",
                "wins": "V",
                "draws": "N",
                "losses": "D",
                "goals_for": "BP",
                "goals_against": "BC",
                "goal_diff": "Diff.",
                "points": "Pts",
                "standing_form": "5 derniers",
            }
        )

        for column in [
            "Rang", "J", "V", "N", "D", "BP", "BC", "Diff.", "Pts",
        ]:
            display[column] = pd.to_numeric(
                display[column],
                errors="coerce",
            ).astype("Int64")

        display["5 derniers"] = display["5 derniers"].apply(
            french_standing_form
        )

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=650,
            column_config={
                "Rang": st.column_config.NumberColumn(width="small"),
                "Club": st.column_config.TextColumn(width="medium"),
                "J": st.column_config.NumberColumn(width="small"),
                "V": st.column_config.NumberColumn(width="small"),
                "N": st.column_config.NumberColumn(width="small"),
                "D": st.column_config.NumberColumn(width="small"),
                "BP": st.column_config.NumberColumn(width="small"),
                "BC": st.column_config.NumberColumn(width="small"),
                "Diff.": st.column_config.NumberColumn(width="small"),
                "Pts": st.column_config.NumberColumn(width="small"),
                "5 derniers": st.column_config.TextColumn(
                    width="medium"
                ),
            },
        )

    with analysis_tab:
        if not (
            selected_competition_id == 61
            and selected_season == 2024
        ):
            st.info(
                "La comparaison avec les notes d'effectif FootRate est "
                "actuellement disponible uniquement pour la Ligue 1 "
                "2024-2025. Les notes de joueurs des autres championnats "
                "seront ajoutées progressivement."
            )
        else:
            comparison = build_sporting_comparison(
                player_data,
                standings,
            )

            if comparison.empty:
                st.caption("Comparaison indisponible.")
            else:
                display = comparison[
                    [
                        "rank", "team_name", "points",
                        "footrate_rank", "squad_score",
                        "rank_gap", "performance_reading",
                    ]
                ].rename(
                    columns={
                        "rank": "Rang sportif",
                        "team_name": "Club",
                        "points": "Points",
                        "footrate_rank": "Rang FootRate",
                        "squad_score": "Note d'effectif",
                        "rank_gap": "Écart de rang",
                        "performance_reading": "Lecture",
                    }
                )

                for column in [
                    "Rang sportif", "Points",
                    "Rang FootRate", "Écart de rang",
                ]:
                    display[column] = pd.to_numeric(
                        display[column],
                        errors="coerce",
                    ).astype("Int64")

                display["Note d'effectif"] = pd.to_numeric(
                    display["Note d'effectif"],
                    errors="coerce",
                ).round(1)

                st.dataframe(
                    display,
                    use_container_width=True,
                    hide_index=True,
                    height=610,
                    column_config={
                        "Rang sportif":
                            st.column_config.NumberColumn(
                                width="small"
                            ),
                        "Club":
                            st.column_config.TextColumn(
                                width="medium"
                            ),
                        "Points":
                            st.column_config.NumberColumn(
                                width="small"
                            ),
                        "Rang FootRate":
                            st.column_config.NumberColumn(
                                width="small"
                            ),
                        "Note d'effectif":
                            st.column_config.ProgressColumn(
                                min_value=0,
                                max_value=100,
                                format="%.1f",
                            ),
                        "Écart de rang":
                            st.column_config.NumberColumn(
                                width="small"
                            ),
                        "Lecture":
                            st.column_config.TextColumn(
                                width="medium"
                            ),
                    },
                )

                chart_data = comparison.dropna(
                    subset=["squad_score", "points"]
                ).copy()

                scatter = (
                    alt.Chart(chart_data)
                    .mark_circle(size=125, opacity=0.84)
                    .encode(
                        x=alt.X(
                            "squad_score:Q",
                            title="Note d'effectif FootRate",
                            scale=alt.Scale(zero=False),
                        ),
                        y=alt.Y(
                            "points:Q",
                            title="Points au classement",
                            scale=alt.Scale(zero=False),
                        ),
                        color=alt.Color(
                            "performance_reading:N",
                            title=None,
                            legend=alt.Legend(orient="bottom"),
                        ),
                        tooltip=[
                            alt.Tooltip(
                                "team_name:N",
                                title="Club",
                            ),
                            alt.Tooltip(
                                "squad_score:Q",
                                title="Note d'effectif",
                                format=".1f",
                            ),
                            alt.Tooltip(
                                "points:Q",
                                title="Points",
                            ),
                            alt.Tooltip(
                                "rank:Q",
                                title="Rang sportif",
                            ),
                            alt.Tooltip(
                                "footrate_rank:Q",
                                title="Rang FootRate",
                            ),
                            alt.Tooltip(
                                "performance_reading:N",
                                title="Lecture",
                            ),
                        ],
                    )
                    .properties(height=440)
                )

                labels = (
                    alt.Chart(chart_data)
                    .mark_text(
                        align="left",
                        dx=7,
                        dy=-6,
                        color="#F8FAFC",
                        fontSize=11,
                    )
                    .encode(
                        x=alt.X("squad_score:Q"),
                        y=alt.Y("points:Q"),
                        text="team_name:N",
                    )
                )

                st.altair_chart(
                    scatter + labels,
                    use_container_width=True,
                )

    with results_tab:
        selected_team = st.selectbox(
            "Choisir un club",
            standings["team_name"].tolist(),
            key=(
                f"competition_results_team_"
                f"{selected_competition_id}_{selected_season}"
            ),
        )

        selected_row = standings[
            standings["team_name"].eq(selected_team)
        ].iloc[0]

        render_recent_results(
            selected_results,
            selected_row["team_id"],
        )

    with history_tab:
        competition_history = competition_table[
            competition_table["competition_id"].eq(
                selected_competition_id
            )
        ].copy()

        available_clubs = sorted(
            competition_history["team_name"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_history_club = st.selectbox(
            "Club à suivre",
            available_clubs,
            key=f"competition_history_club_{selected_competition_id}",
        )

        club_history = (
            competition_history[
                competition_history["team_name"].eq(
                    selected_history_club
                )
            ]
            .sort_values("season")
            .copy()
        )

        if club_history.empty:
            st.caption("Historique indisponible pour ce club.")
        else:
            history_display = club_history[
                [
                    "season_label", "rank", "points",
                    "wins", "draws", "losses",
                    "goals_for", "goals_against", "goal_diff",
                ]
            ].rename(
                columns={
                    "season_label": "Saison",
                    "rank": "Rang",
                    "points": "Points",
                    "wins": "V",
                    "draws": "N",
                    "losses": "D",
                    "goals_for": "BP",
                    "goals_against": "BC",
                    "goal_diff": "Diff.",
                }
            )

            for column in [
                "Rang", "Points", "V", "N", "D", "BP", "BC", "Diff.",
            ]:
                history_display[column] = pd.to_numeric(
                    history_display[column],
                    errors="coerce",
                ).astype("Int64")

            st.dataframe(
                history_display,
                use_container_width=True,
                hide_index=True,
            )

            season_sort = club_history["season_label"].tolist()

            points_chart = (
                alt.Chart(club_history)
                .mark_line(
                    point=True,
                    strokeWidth=3,
                    color="#22D3A7",
                )
                .encode(
                    x=alt.X(
                        "season_label:N",
                        title="Saison",
                        sort=season_sort,
                    ),
                    y=alt.Y(
                        "points:Q",
                        title="Points",
                        scale=alt.Scale(zero=False),
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "season_label:N",
                            title="Saison",
                        ),
                        alt.Tooltip(
                            "points:Q",
                            title="Points",
                        ),
                        alt.Tooltip(
                            "rank:Q",
                            title="Rang",
                        ),
                    ],
                )
                .properties(height=310)
            )
            st.altair_chart(
                points_chart,
                use_container_width=True,
            )

            rank_chart = (
                alt.Chart(club_history)
                .mark_line(
                    point=True,
                    strokeWidth=3,
                    color="#7DD3FC",
                )
                .encode(
                    x=alt.X(
                        "season_label:N",
                        title="Saison",
                        sort=season_sort,
                    ),
                    y=alt.Y(
                        "rank:Q",
                        title="Classement",
                        scale=alt.Scale(
                            domain=[
                                int(
                                    competition_history[
                                        "rank"
                                    ].max()
                                ),
                                1,
                            ]
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "season_label:N",
                            title="Saison",
                        ),
                        alt.Tooltip(
                            "rank:Q",
                            title="Rang",
                        ),
                        alt.Tooltip(
                            "points:Q",
                            title="Points",
                        ),
                    ],
                )
                .properties(height=310)
            )
            st.altair_chart(
                rank_chart,
                use_container_width=True,
            )



TEAM_STAT_OPTIONS = {
    "Possession (%)": {
        "column": "possession",
        "unit": "%",
        "kind": "average",
    },
    "Tirs": {
        "column": "shots_total",
        "unit": "",
        "kind": "average",
    },
    "Tirs cadrés": {
        "column": "shots_on_target",
        "unit": "",
        "kind": "average",
    },
    "Tirs non cadrés": {
        "column": "shots_off_target",
        "unit": "",
        "kind": "average",
    },
    "Tirs bloqués": {
        "column": "blocked_shots",
        "unit": "",
        "kind": "average",
    },
    "Tirs dans la surface": {
        "column": "shots_inside_box",
        "unit": "",
        "kind": "average",
    },
    "Corners": {
        "column": "corners",
        "unit": "",
        "kind": "average",
    },
    "Fautes": {
        "column": "fouls",
        "unit": "",
        "kind": "average",
    },
    "Hors-jeu": {
        "column": "offsides",
        "unit": "",
        "kind": "average",
    },
    "Cartons jaunes": {
        "column": "yellow_cards",
        "unit": "",
        "kind": "average",
    },
    "Cartons rouges": {
        "column": "red_cards",
        "unit": "",
        "kind": "average",
    },
    "Arrêts du gardien": {
        "column": "goalkeeper_saves",
        "unit": "",
        "kind": "average",
    },
    "Passes tentées": {
        "column": "passes_total",
        "unit": "",
        "kind": "average",
    },
    "Passes réussies": {
        "column": "passes_accurate",
        "unit": "",
        "kind": "average",
    },
    "Précision des passes (%)": {
        "column": "pass_accuracy",
        "unit": "%",
        "kind": "average",
    },
}


def result_label(result: str) -> str:
    return {
        "V": "Victoire",
        "N": "Nul",
        "D": "Défaite",
    }.get(str(result).upper(), "Non renseigné")


def home_away_label(value: str) -> str:
    return {
        "home": "Domicile",
        "away": "Extérieur",
    }.get(str(value).lower(), "Non renseigné")


def prepare_team_analysis(
    all_stats: pd.DataFrame,
    competition_id: int,
    season: int,
    team_id: int,
    matchday_range: tuple[int, int],
    venue_filter: str,
    opponent_filter: str,
) -> pd.DataFrame:
    selected = all_stats[
        all_stats["competition_id"].eq(competition_id)
        & all_stats["season"].eq(season)
        & all_stats["team_id"].eq(team_id)
        & all_stats["matchday"].between(
            matchday_range[0],
            matchday_range[1],
            inclusive="both",
        )
    ].copy()

    if venue_filter == "Domicile":
        selected = selected[selected["home_away"].eq("home")]
    elif venue_filter == "Extérieur":
        selected = selected[selected["home_away"].eq("away")]

    if opponent_filter != "Tous":
        selected = selected[selected["opponent_name"].eq(opponent_filter)]

    return selected.sort_values(["matchday", "date_parsed"])


def merge_opponent_stat(
    selected: pd.DataFrame,
    all_stats: pd.DataFrame,
    stat_column: str,
) -> pd.DataFrame:
    if selected.empty:
        return selected.copy()

    opponent_values = all_stats[
        ["fixture_id", "team_id", stat_column]
    ].rename(
        columns={
            "team_id": "opponent_row_team_id",
            stat_column: "opponent_value",
        }
    )

    merged = selected.merge(
        opponent_values,
        left_on=["fixture_id", "opponent_id"],
        right_on=["fixture_id", "opponent_row_team_id"],
        how="left",
    )
    merged["team_value"] = pd.to_numeric(
        merged[stat_column],
        errors="coerce",
    )
    merged["opponent_value"] = pd.to_numeric(
        merged["opponent_value"],
        errors="coerce",
    )
    merged["difference"] = (
        merged["team_value"] - merged["opponent_value"]
    )
    return merged


def render_advanced_analysis(team_match_stats: pd.DataFrame) -> None:
    st.subheader("Analyse avancée des clubs")
    st.caption(
        "Filtre les données match par match par championnat, saison, équipe "
        "et plage de journées."
    )

    if team_match_stats.empty:
        st.warning(
            "Aucune statistique détaillée n'est encore disponible. "
            "Exécute `sportsrate_team_stats_update.py`, puis ajoute "
            "`output/sportsrate_team_match_stats_v1_2.csv` sur GitHub."
        )
        st.info(
            "Exemple : récupère toute la saison du PSG, puis analyse sa "
            "possession entre la J3 et la J14."
        )
        return

    competitions = (
        team_match_stats[["competition_id", "competition_name"]]
        .drop_duplicates()
        .sort_values("competition_name")
    )
    competition_names = competitions["competition_name"].tolist()

    filter_1, filter_2, filter_3 = st.columns(3)
    with filter_1:
        selected_competition_name = st.selectbox(
            "Compétition",
            competition_names,
            key="advanced_competition",
        )

    selected_competition_id = int(
        competitions.loc[
            competitions["competition_name"].eq(
                selected_competition_name
            ),
            "competition_id",
        ].iloc[0]
    )

    seasons = (
        team_match_stats[
            team_match_stats["competition_id"].eq(
                selected_competition_id
            )
        ][["season", "season_label"]]
        .drop_duplicates()
        .sort_values("season", ascending=False)
    )
    with filter_2:
        selected_season_label = st.selectbox(
            "Saison",
            seasons["season_label"].tolist(),
            key="advanced_season",
        )
    selected_season = int(
        seasons.loc[
            seasons["season_label"].eq(selected_season_label),
            "season",
        ].iloc[0]
    )

    team_options = (
        team_match_stats[
            team_match_stats["competition_id"].eq(
                selected_competition_id
            )
            & team_match_stats["season"].eq(selected_season)
        ][["team_id", "team_name"]]
        .drop_duplicates()
        .sort_values("team_name")
    )
    with filter_3:
        selected_team_name = st.selectbox(
            "Équipe",
            team_options["team_name"].tolist(),
            key="advanced_team",
        )
    selected_team_id = int(
        team_options.loc[
            team_options["team_name"].eq(selected_team_name),
            "team_id",
        ].iloc[0]
    )

    team_season = team_match_stats[
        team_match_stats["competition_id"].eq(selected_competition_id)
        & team_match_stats["season"].eq(selected_season)
        & team_match_stats["team_id"].eq(selected_team_id)
    ].copy()

    valid_matchdays = sorted(
        int(value)
        for value in team_season["matchday"].dropna().unique()
    )
    if not valid_matchdays:
        st.error("Aucune journée exploitable n'a été trouvée pour cette équipe.")
        return

    available_stats = [
        label
        for label, config in TEAM_STAT_OPTIONS.items()
        if config["column"] in team_season.columns
        and team_season[config["column"]].notna().any()
    ]
    if not available_stats:
        st.error("Les statistiques de cette équipe sont vides.")
        return

    advanced_1, advanced_2, advanced_3, advanced_4 = st.columns(
        [1.3, 1.5, 1, 1.2]
    )
    with advanced_1:
        stat_label = st.selectbox(
            "Statistique étudiée",
            available_stats,
            index=(
                available_stats.index("Possession (%)")
                if "Possession (%)" in available_stats
                else 0
            ),
            key="advanced_stat",
        )

    min_day = min(valid_matchdays)
    max_day = max(valid_matchdays)
    default_start = 3 if min_day <= 3 <= max_day else min_day
    default_end = 14 if min_day <= 14 <= max_day else max_day
    if default_start > default_end:
        default_start, default_end = min_day, max_day

    with advanced_2:
        matchday_range = st.slider(
            "Plage de journées",
            min_value=min_day,
            max_value=max_day,
            value=(default_start, default_end),
            key="advanced_matchdays",
        )

    with advanced_3:
        venue_filter = st.selectbox(
            "Lieu",
            ["Tous", "Domicile", "Extérieur"],
            key="advanced_venue",
        )

    opponents = ["Tous"] + sorted(
        team_season["opponent_name"].dropna().unique().tolist()
    )
    with advanced_4:
        opponent_filter = st.selectbox(
            "Adversaire",
            opponents,
            key="advanced_opponent",
        )

    selected = prepare_team_analysis(
        team_match_stats,
        selected_competition_id,
        selected_season,
        selected_team_id,
        matchday_range,
        venue_filter,
        opponent_filter,
    )

    stat_config = TEAM_STAT_OPTIONS[stat_label]
    stat_column = stat_config["column"]
    unit = stat_config["unit"]

    selected = merge_opponent_stat(
        selected,
        team_match_stats,
        stat_column,
    )
    selected = selected[selected["team_value"].notna()].copy()

    if selected.empty:
        st.warning(
            "Aucun match ne correspond aux filtres choisis ou la statistique "
            "n'est pas renseignée sur cette période."
        )
        return

    average_value = float(selected["team_value"].mean())
    minimum_value = float(selected["team_value"].min())
    maximum_value = float(selected["team_value"].max())
    opponent_average = (
        float(selected["opponent_value"].mean())
        if selected["opponent_value"].notna().any()
        else float("nan")
    )
    average_difference = (
        float(selected["difference"].mean())
        if selected["difference"].notna().any()
        else float("nan")
    )

    metric_1, metric_2, metric_3, metric_4, metric_5 = st.columns(5)
    metric_1.metric(
        "Moyenne sur la période",
        f"{average_value:.1f}{unit}",
    )
    metric_2.metric(
        "Minimum",
        f"{minimum_value:.1f}{unit}",
    )
    metric_3.metric(
        "Maximum",
        f"{maximum_value:.1f}{unit}",
    )
    metric_4.metric(
        "Moyenne adverse",
        "—" if pd.isna(opponent_average)
        else f"{opponent_average:.1f}{unit}",
        delta=(
            None if pd.isna(average_difference)
            else f"{average_difference:+.1f}{unit} d'écart"
        ),
    )
    metric_5.metric(
        "Matchs analysés",
        len(selected),
        delta=(
            f"J{matchday_range[0]} à J{matchday_range[1]}"
        ),
        delta_color="off",
    )

    chart_data = selected[
        [
            "matchday", "date", "opponent_name", "result",
            "home_away", "team_value", "opponent_value",
        ]
    ].copy()
    chart_data["Équipe"] = selected_team_name
    chart_data["Adversaire"] = chart_data["opponent_name"]

    team_line = (
        alt.Chart(chart_data)
        .mark_line(point=True, strokeWidth=3, color="#22D3A7")
        .encode(
            x=alt.X(
                "matchday:Q",
                title="Journée",
                axis=alt.Axis(tickMinStep=1),
            ),
            y=alt.Y(
                "team_value:Q",
                title=stat_label,
                scale=alt.Scale(zero=False),
            ),
            tooltip=[
                alt.Tooltip("matchday:Q", title="Journée"),
                alt.Tooltip("date:N", title="Date"),
                alt.Tooltip("opponent_name:N", title="Adversaire"),
                alt.Tooltip("team_value:Q", title=selected_team_name, format=".1f"),
                alt.Tooltip("opponent_value:Q", title="Adversaire", format=".1f"),
                alt.Tooltip("result:N", title="Résultat"),
            ],
        )
    )
    opponent_line = (
        alt.Chart(chart_data[chart_data["opponent_value"].notna()])
        .mark_line(
            point=True,
            strokeWidth=2,
            strokeDash=[6, 4],
            color="#7DD3FC",
        )
        .encode(
            x=alt.X("matchday:Q"),
            y=alt.Y("opponent_value:Q"),
        )
    )
    average_rule = (
        alt.Chart(pd.DataFrame({"average": [average_value]}))
        .mark_rule(color="#F59E0B", strokeDash=[4, 4])
        .encode(y="average:Q")
    )

    st.markdown(f"### Évolution de {stat_label.lower()}")
    st.altair_chart(
        (team_line + opponent_line + average_rule).properties(height=430),
        use_container_width=True,
    )
    st.caption(
        f"Ligne verte : {selected_team_name}. Ligne bleue pointillée : "
        "adversaire. Ligne orange : moyenne de la période."
    )

    result_summary = (
        selected.assign(
            Résultat=selected["result"].apply(result_label),
            Lieu=selected["home_away"].apply(home_away_label),
        )
        .groupby("Résultat", as_index=False)
        .agg(
            Matchs=("fixture_id", "count"),
            Moyenne=("team_value", "mean"),
            Moyenne_adverse=("opponent_value", "mean"),
        )
    )

    place_summary = (
        selected.assign(
            Lieu=selected["home_away"].apply(home_away_label),
        )
        .groupby("Lieu", as_index=False)
        .agg(
            Matchs=("fixture_id", "count"),
            Moyenne=("team_value", "mean"),
            Moyenne_adverse=("opponent_value", "mean"),
        )
    )

    result_col, place_col = st.columns(2)
    with result_col:
        st.markdown("### Selon le résultat")
        if not result_summary.empty:
            result_summary["Moyenne"] = result_summary["Moyenne"].round(1)
            result_summary["Moyenne adverse"] = result_summary.pop(
                "Moyenne_adverse"
            ).round(1)
            st.dataframe(
                result_summary,
                use_container_width=True,
                hide_index=True,
            )

    with place_col:
        st.markdown("### Domicile / extérieur")
        if not place_summary.empty:
            place_summary["Moyenne"] = place_summary["Moyenne"].round(1)
            place_summary["Moyenne adverse"] = place_summary.pop(
                "Moyenne_adverse"
            ).round(1)
            st.dataframe(
                place_summary,
                use_container_width=True,
                hide_index=True,
            )

    detailed = selected[
        [
            "matchday", "date_parsed", "opponent_name", "home_away",
            "score", "result", "team_value", "opponent_value", "difference",
        ]
    ].copy()
    detailed["Journée"] = detailed.pop("matchday").astype("Int64")
    detailed["Date"] = detailed.pop("date_parsed").dt.strftime("%d/%m/%Y")
    detailed["Adversaire"] = detailed.pop("opponent_name")
    detailed["Lieu"] = detailed.pop("home_away").apply(home_away_label)
    detailed["Score"] = detailed.pop("score")
    detailed["Résultat"] = detailed.pop("result").apply(result_label)
    detailed[selected_team_name] = detailed.pop("team_value").round(1)
    detailed["Adversaire - statistique"] = detailed.pop(
        "opponent_value"
    ).round(1)
    detailed["Écart"] = detailed.pop("difference").round(1)

    st.markdown("### Matchs utilisés dans le calcul")
    st.dataframe(
        detailed,
        use_container_width=True,
        hide_index=True,
        height=min(650, 90 + len(detailed) * 36),
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

        players_count = int(len(group))
        players_used = min(players_count, 11)
        top_players = group.head(players_used)

        if players_count >= 11:
            coverage_status = "Officielle"
            coverage_order = 1
        elif players_count >= 7:
            coverage_status = "Provisoire"
            coverage_order = 2
        else:
            coverage_status = "Données insuffisantes"
            coverage_order = 3

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
                "squad_score": float(top_players["overall"].mean()),
                "average_score": float(group["overall"].mean()),
                "players_count": players_count,
                "players_used": players_used,
                "coverage_status": coverage_status,
                "coverage_order": coverage_order,
                "eligible_for_ranking": players_count >= 7,
                "official_club_rating": players_count >= 11,
                "provisional_club_rating": 7 <= players_count <= 10,
                "attack_score": position_scores["Attacker"],
                "midfield_score": position_scores["Midfielder"],
                "defence_score": position_scores["Defender"],
                "best_player": best_player["player_name"],
                "best_player_score": float(best_player["overall"]),
                "best_player_id": best_player["player_id"],
                "minutes_total": float(group["minutes"].sum()),
                "club_form": (
                    float(group["club_form"].dropna().iloc[0])
                    if group["club_form"].notna().any()
                    else float("nan")
                ),
                "club_form_trend": (
                    float(group["club_form_trend"].dropna().iloc[0])
                    if group["club_form_trend"].notna().any()
                    else float("nan")
                ),
            }
        )

    summary = pd.DataFrame(records)
    summary = summary.sort_values(
        ["coverage_order", "squad_score", "average_score"],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    ranked_mask = summary["eligible_for_ranking"]
    summary["rank"] = pd.NA
    summary.loc[ranked_mask, "rank"] = range(1, int(ranked_mask.sum()) + 1)
    return summary



def club_status_badge(status: str) -> str:
    status_classes = {
        "Officielle": "status-official",
        "Provisoire": "status-provisional",
        "Données insuffisantes": "status-insufficient",
    }
    css_class = status_classes.get(status, "status-insufficient")
    return f'<div class="status-pill {css_class}">{status}</div>'


def club_score_caption(club_row: pd.Series) -> str:
    players_used = int(club_row["players_used"])
    if club_row["coverage_status"] == "Officielle":
        return f"Moyenne des {players_used} joueurs les mieux notés"
    if club_row["coverage_status"] == "Provisoire":
        return (
            f"Note provisoire calculée sur {players_used} joueurs "
            "au lieu des 11 requis"
        )
    return (
        f"Indicateur calculé sur seulement {players_used} joueurs ; "
        "non classé"
    )


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


def render_club_comparison(
    summary: pd.DataFrame,
    competition_table: pd.DataFrame,
) -> None:
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
        st.markdown(
            club_status_badge(club_a["coverage_status"]),
            unsafe_allow_html=True,
        )
        st.caption(club_score_caption(club_a))

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
        st.markdown(
            club_status_badge(club_b["coverage_status"]),
            unsafe_allow_html=True,
        )
        st.caption(club_score_caption(club_b))

    if (
        club_a["coverage_status"] != "Officielle"
        or club_b["coverage_status"] != "Officielle"
    ):
        st.warning(
            "Au moins l'un des deux clubs ne dispose pas de 11 joueurs notés. "
            "La comparaison de sa note d'effectif doit être considérée avec prudence."
        )

    comparison_rows = []
    criteria = [
        ("Note d'effectif", "squad_score"),
        ("Moyenne des joueurs", "average_score"),
        ("Attaque", "attack_score"),
        ("Milieu", "midfield_score"),
        ("Défense", "defence_score"),
        ("Forme récente", "club_form"),
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

    if not competition_table.empty:
        sports = competition_table[
            competition_table["team_name"].isin(
                [club_a["team_name"], club_b["team_name"]]
            )
        ].copy()

        if len(sports) == 2:
            sports_display = sports[
                [
                    "team_name", "rank", "points", "played",
                    "wins", "draws", "losses", "goal_diff",
                ]
            ].rename(
                columns={
                    "team_name": "Club",
                    "rank": "Rang",
                    "points": "Points",
                    "played": "J",
                    "wins": "V",
                    "draws": "N",
                    "losses": "D",
                    "goal_diff": "Diff.",
                }
            )
            st.markdown("### Bilan sportif")
            st.dataframe(
                sports_display,
                use_container_width=True,
                hide_index=True,
            )


def render_clubs(
    df: pd.DataFrame,
    competition_table: pd.DataFrame,
    recent_results: pd.DataFrame,
) -> None:
    st.subheader("Clubs")
    st.caption(
        "La note d'effectif correspond à la moyenne des onze joueurs les mieux "
        "notés du club. Elle est officielle à partir de 11 joueurs évalués."
    )

    summary = build_club_summary(df)
    ranking_tab, profile_tab, comparison_tab = st.tabs(
        ["Classement des clubs", "Fiche club", "Comparateur"]
    )

    with ranking_tab:
        ranked_clubs = summary[summary["eligible_for_ranking"]].copy()
        insufficient_clubs = summary[~summary["eligible_for_ranking"]].copy()

        display = ranked_clubs[
            [
                "rank",
                "team_name",
                "players_used",
                "squad_score",
                "coverage_status",
                "club_form",
                "club_form_trend",
                "average_score",
                "best_player",
            ]
        ].rename(
            columns={
                "rank": "Rang",
                "team_name": "Club",
                "players_used": "Joueurs pris en compte",
                "squad_score": "Note d'effectif",
                "coverage_status": "Statut",
                "club_form": "Forme",
                "club_form_trend": "Tendance",
                "average_score": "Moyenne",
                "best_player": "Meilleur joueur",
            }
        )
        display["Rang"] = display["Rang"].astype("Int64")
        display["Note d'effectif"] = display["Note d'effectif"].round(1)
        display["Moyenne"] = display["Moyenne"].round(1)
        display["Forme"] = pd.to_numeric(
            display["Forme"], errors="coerce"
        ).round(1)
        display["Tendance"] = pd.to_numeric(
            display["Tendance"], errors="coerce"
        ).apply(
            lambda value: (
                "↗ En hausse" if pd.notna(value) and value >= 3
                else "↘ En baisse" if pd.notna(value) and value <= -3
                else "→ Stable" if pd.notna(value)
                else "—"
            )
        )

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=570,
            column_config={
                "Rang": st.column_config.NumberColumn(width="small"),
                "Club": st.column_config.TextColumn(width="medium"),
                "Joueurs pris en compte": st.column_config.NumberColumn(width="small"),
                "Note d'effectif": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Statut": st.column_config.TextColumn(width="small"),
                "Forme": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%.1f",
                ),
                "Tendance": st.column_config.TextColumn(width="small"),
                "Moyenne": st.column_config.NumberColumn(format="%.1f"),
                "Meilleur joueur": st.column_config.TextColumn(width="medium"),
            },
        )

        official_count = int((ranked_clubs["coverage_status"] == "Officielle").sum())
        provisional_count = int((ranked_clubs["coverage_status"] == "Provisoire").sum())
        metric_1, metric_2, metric_3, metric_4 = st.columns(4)
        metric_1.metric("Notes officielles", official_count)
        metric_2.metric("Notes provisoires", provisional_count)
        metric_3.metric("Clubs non classés", len(insufficient_clubs))

        st.info(
            "Officielle : au moins 11 joueurs pris en compte. "
            "Provisoire : 7 à 10 joueurs. Les clubs sous 7 joueurs ne sont pas classés."
        )

        if not insufficient_clubs.empty:
            with st.expander("Clubs aux données insuffisantes"):
                insufficient_display = insufficient_clubs[
                    [
                        "team_name",
                        "players_used",
                        "squad_score",
                        "best_player",
                    ]
                ].rename(
                    columns={
                        "team_name": "Club",
                        "players_used": "Joueurs pris en compte",
                        "squad_score": "Indicateur partiel",
                        "best_player": "Meilleur joueur",
                    }
                )
                insufficient_display["Indicateur partiel"] = (
                    insufficient_display["Indicateur partiel"].round(1)
                )
                st.dataframe(
                    insufficient_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Club": st.column_config.TextColumn(width="medium"),
                        "Joueurs pris en compte": st.column_config.NumberColumn(
                            width="small"
                        ),
                        "Indicateur partiel": st.column_config.NumberColumn(
                            format="%.1f"
                        ),
                        "Meilleur joueur": st.column_config.TextColumn(width="medium"),
                    },
                )
                st.caption(
                    "Ces indicateurs ne sont pas intégrés au classement des clubs."
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
            st.write(
                f"**{int(club_row['players_used'])} joueurs pris en compte "
                f"sur {int(club_row['players_count'])} évalués**"
            )
            st.caption(
                f"Meilleur joueur : {club_row['best_player']} "
                f"({club_row['best_player_score']:.1f})"
            )

        with note_col:
            st.markdown(
                score_badge(club_row["squad_score"], "Note d'effectif"),
                unsafe_allow_html=True,
            )
            st.markdown(
                club_status_badge(club_row["coverage_status"]),
                unsafe_allow_html=True,
            )
            st.caption(club_score_caption(club_row))

        with chart_col:
            st.altair_chart(
                club_score_chart(club_row),
                use_container_width=True,
            )

        if club_row["coverage_status"] == "Provisoire":
            st.warning(
                "Cette note d'effectif est provisoire : moins de 11 joueurs sont "
                "disponibles dans les données."
            )
        elif club_row["coverage_status"] == "Données insuffisantes":
            st.error(
                "Ce club n'est pas intégré au classement : moins de 7 joueurs "
                "sont disponibles dans les données."
            )

        metric_1, metric_2, metric_3 = st.columns(3)
        metric_1.metric("Moyenne des joueurs", f"{club_row['average_score']:.1f}")
        metric_2.metric(
            "Joueurs pris en compte",
            f"{int(club_row['players_used'])}/11",
        )
        metric_3.metric(
            "Meilleure note individuelle",
            f"{club_row['best_player_score']:.1f}",
        )
        metric_4.metric(
            "Forme du club",
            "—" if pd.isna(club_row.get("club_form"))
            else f"{club_row['club_form']:.1f}",
            delta=(
                None if pd.isna(club_row.get("club_form_trend"))
                else f"{club_row['club_form_trend']:+.1f}"
            ),
        )

        if not competition_table.empty:
            sporting_rows = competition_table[
                pd.to_numeric(
                    competition_table["team_id"],
                    errors="coerce",
                )
                == int(club_row["team_id"])
            ]
            if not sporting_rows.empty:
                sporting = sporting_rows.iloc[0]
                st.markdown("### Bilan sportif 2024-2025")
                sport_1, sport_2, sport_3, sport_4 = st.columns(4)
                sport_1.metric(
                    "Classement",
                    f"{int(sporting['rank'])}e",
                )
                sport_2.metric(
                    "Points",
                    int(sporting["points"]),
                )
                sport_3.metric(
                    "Victoires / Nuls / Défaites",
                    (
                        f"{int(sporting['wins'])} / "
                        f"{int(sporting['draws'])} / "
                        f"{int(sporting['losses'])}"
                    ),
                )
                sport_4.metric(
                    "Différence de buts",
                    f"{int(sporting['goal_diff']):+d}",
                )

                render_recent_results(
                    recent_results,
                    club_row["team_id"],
                    heading="Cinq derniers matchs du club",
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
        render_club_comparison(summary, competition_table)


def render_ranking(df: pd.DataFrame) -> None:
    st.subheader("Classement des joueurs")

    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(
        [1.4, 1, 1, 1, 1]
    )
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
    with filter_col5:
        sort_choice = st.selectbox(
            "Trier par",
            ["Note générale", "Forme récente"],
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
    if (
        sort_choice == "Forme récente"
        and pd.to_numeric(filtered["form"], errors="coerce").notna().any()
    ):
        filtered = filtered.sort_values(
            ["form", "overall", "minutes"],
            ascending=[False, False, False],
        ).copy()
    else:
        filtered = filtered.sort_values(
            ["overall", "minutes"],
            ascending=[False, False],
        ).copy()
    filtered["Rang"] = range(1, len(filtered) + 1)

    display = filtered[
        [
            "Rang", "player_name", "team_name", "position_fr",
            "minutes", "overall", "form", "form_trend", "reliability",
        ]
    ].rename(
        columns={
            "player_name": "Joueur",
            "team_name": "Club",
            "position_fr": "Poste",
            "minutes": "Minutes",
            "overall": "Note",
            "form": "Forme",
            "form_trend": "Tendance",
            "reliability": "Fiabilité",
        }
    )
    display["Minutes"] = display["Minutes"].round(0).astype("Int64")
    display["Note"] = display["Note"].round(1)
    display["Forme"] = pd.to_numeric(
        display["Forme"], errors="coerce"
    ).round(1)
    display["Tendance"] = pd.to_numeric(
        display["Tendance"], errors="coerce"
    ).apply(
        lambda value: (
            "↗ En hausse" if pd.notna(value) and value >= 3
            else "↘ En baisse" if pd.notna(value) and value <= -3
            else "→ Stable" if pd.notna(value)
            else "—"
        )
    )

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
            "Forme": st.column_config.ProgressColumn(
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Tendance": st.column_config.TextColumn(width="small"),
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

    metric1, metric2, metric3, metric4, metric5, metric6 = st.columns(6)
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
    metric5.metric(
        "Forme récente",
        "—" if pd.isna(player.get("form")) else f"{player['form']:.1f}",
        delta=(
            None if pd.isna(player.get("form_trend"))
            else f"{player['form_trend']:+.1f}"
        ),
    )
    metric6.metric(
        "Fiabilité de la forme",
        player.get("form_reliability", "Non disponible"),
        delta=(
            "—" if pd.isna(player.get("matches_in_form"))
            else f"{int(player['matches_in_form'])}/5 matchs"
        ),
        delta_color="off",
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
            "Critère": [
                "Note générale",
                "Forme récente",
                "Tendance",
                "Minutes",
                "Profil",
                "Performance",
            ],
            player_a["player_name"]: [
                player_a["overall"],
                player_a.get("form"),
                trend_text(player_a.get("form_trend")),
                player_a["minutes"],
                player_a.get("profile_score"),
                player_a.get("performance_score"),
            ],
            player_b["player_name"]: [
                player_b["overall"],
                player_b.get("form"),
                trend_text(player_b.get("form_trend")),
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

        La **forme récente d'un joueur** est calculée à partir de ses notes
        API-Football lors des cinq derniers matchs de son club, avec davantage de
        poids pour les rencontres les plus récentes et le temps réellement joué.
        Lorsque moins de cinq matchs individuels sont disponibles, la note est
        progressivement rapprochée de 70 afin de limiter les conclusions sur un
        échantillon trop faible.

        La **forme d'un club** combine les résultats de ses cinq derniers matchs et
        leur différence de buts sur une échelle volontairement modérée. La tendance
        compare les deux matchs les plus récents aux trois précédents et reste limitée
        à ±15 points.

        Les **analyses avancées** utilisent une ligne par équipe et par match.
        Cette structure permet de filtrer une statistique par journée, lieu,
        adversaire et période, puis de la comparer à la valeur de l'adversaire.

        Le **classement sportif réel** et les résultats sont récupérés séparément
        depuis API-Football. Ils ne modifient pas la note d'effectif : ils servent à
        comparer la qualité statistique estimée d'un groupe à ses résultats réels.

        La **note d'effectif d'un club** correspond à la moyenne des onze joueurs
        les mieux notés du club. Elle est officielle avec au moins 11 joueurs évalués,
        provisoire avec 7 à 10 joueurs et non classée sous 7 joueurs. Elle mesure la
        qualité statistique de l'effectif et non ses résultats sportifs réels.
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
        .status-insufficient {
            color: #fecaca;
            background: rgba(239, 68, 68, 0.14);
            border: 1px solid rgba(239, 68, 68, 0.34);
        }
        .trend-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            padding: 0.3rem 0.55rem;
            font-size: 0.76rem;
            font-weight: 800;
            white-space: nowrap;
        }
        .trend-up {
            color: #bbf7d0;
            background: rgba(34, 197, 94, 0.14);
            border: 1px solid rgba(34, 197, 94, 0.32);
        }
        .trend-down {
            color: #fecaca;
            background: rgba(239, 68, 68, 0.14);
            border: 1px solid rgba(239, 68, 68, 0.32);
        }
        .trend-neutral {
            color: #cbd5e1;
            background: rgba(100, 116, 139, 0.14);
            border: 1px solid rgba(100, 116, 139, 0.32);
        }
        .form-player-card {
            position: relative;
            min-height: 340px;
            padding: 1rem;
            border: 1px solid var(--footrate-border);
            border-radius: 18px;
            background:
                linear-gradient(
                    155deg,
                    rgba(17, 28, 47, 0.98),
                    rgba(10, 20, 35, 0.94)
                );
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.22);
        }
        .form-card-label {
            display: inline-flex;
            align-items: center;
            padding: 0.32rem 0.58rem;
            border-radius: 999px;
            color: #fde68a;
            background: rgba(245, 158, 11, 0.14);
            border: 1px solid rgba(245, 158, 11, 0.32);
            font-size: 0.76rem;
            font-weight: 850;
        }
        .form-card-main {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.8rem;
            margin-top: 0.9rem;
        }
        .form-card-photo {
            width: 122px;
            height: 122px;
            object-fit: cover;
            object-position: top;
            border-radius: 15px;
            background: #ffffff;
        }
        .form-score-block {
            flex: 1;
            text-align: center;
        }
        .form-score-circle {
            display: grid;
            place-items: center;
            width: 88px;
            height: 88px;
            margin: 0 auto;
            border: 6px solid;
            border-radius: 50%;
            background: rgba(7, 16, 31, 0.92);
        }
        .form-score-circle span {
            color: #f8fafc;
            font-size: 1.65rem;
            font-weight: 900;
        }
        .form-score-caption {
            margin-top: 0.42rem;
            color: #94a3b8;
            font-size: 0.72rem;
            font-weight: 700;
        }
        .form-card-name {
            margin-top: 0.8rem;
            color: #f8fafc;
            font-size: 1.1rem;
            font-weight: 850;
        }
        .form-card-club {
            display: flex;
            align-items: center;
            gap: 0.42rem;
            margin-top: 0.42rem;
            color: #cbd5e1;
            font-size: 0.84rem;
        }
        .form-card-club img {
            width: 24px;
            height: 24px;
            object-fit: contain;
        }
        .form-card-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.55rem;
            margin-top: 0.85rem;
        }
        .form-detail-box {
            padding: 0.58rem 0.62rem;
            border-radius: 11px;
            background: rgba(7, 16, 31, 0.62);
            border: 1px solid rgba(148, 163, 184, 0.16);
        }
        .form-detail-box span,
        .form-detail-box strong {
            display: block;
        }
        .form-detail-box span {
            color: #94a3b8;
            font-size: 0.68rem;
        }
        .form-detail-box strong {
            margin-top: 0.18rem;
            color: #f8fafc;
            font-size: 0.92rem;
        }
        .form-card-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.6rem;
            margin-top: 0.78rem;
            color: #94a3b8;
            font-size: 0.74rem;
        }
        .season-summary-card {
            min-height: 125px;
            padding: 0.85rem;
            border: 1px solid var(--footrate-border);
            border-radius: 14px;
            background: rgba(17, 28, 47, 0.9);
        }
        .season-summary-card span,
        .season-summary-card strong,
        .season-summary-card small {
            display: block;
        }
        .season-summary-card span {
            color: #94a3b8;
            font-size: 0.72rem;
            font-weight: 750;
        }
        .season-summary-card strong {
            margin-top: 0.45rem;
            color: #f8fafc;
            font-size: 1.15rem;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }
        .season-summary-card small {
            margin-top: 0.35rem;
            color: #22d3a7;
            font-size: 0.72rem;
        }
        .recent-match-card {
            min-height: 170px;
            padding: 0.78rem;
            border: 1px solid var(--footrate-border);
            border-radius: 14px;
            background: rgba(17, 28, 47, 0.88);
            text-align: center;
        }
        .recent-match-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.4rem;
            color: #94a3b8;
            font-size: 0.69rem;
        }
        .match-result-pill {
            display: grid;
            place-items: center;
            width: 25px;
            height: 25px;
            border-radius: 50%;
            font-weight: 900;
        }
        .match-win {
            color: #bbf7d0;
            background: rgba(34, 197, 94, 0.18);
            border: 1px solid rgba(34, 197, 94, 0.35);
        }
        .match-draw {
            color: #fde68a;
            background: rgba(245, 158, 11, 0.18);
            border: 1px solid rgba(245, 158, 11, 0.35);
        }
        .match-loss {
            color: #fecaca;
            background: rgba(239, 68, 68, 0.18);
            border: 1px solid rgba(239, 68, 68, 0.35);
        }
        .match-neutral {
            color: #cbd5e1;
            background: rgba(100, 116, 139, 0.18);
            border: 1px solid rgba(100, 116, 139, 0.35);
        }
        .recent-opponent {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.45rem;
            margin-top: 0.8rem;
            min-height: 43px;
            color: #f8fafc;
            font-size: 0.82rem;
        }
        .recent-opponent img {
            width: 35px;
            height: 35px;
            object-fit: contain;
        }
        .recent-score {
            margin-top: 0.55rem;
            color: #22d3a7;
            font-size: 1.35rem;
            font-weight: 900;
        }
        .recent-location {
            margin-top: 0.35rem;
            color: #94a3b8;
            font-size: 0.7rem;
        }
        .club-form-card {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            min-height: 72px;
            padding: 0.7rem;
            border: 1px solid var(--footrate-border);
            border-radius: 14px;
            background: rgba(17, 28, 47, 0.88);
        }
        .club-form-card img {
            width: 42px;
            height: 42px;
            object-fit: contain;
        }
        .club-form-card > div {
            min-width: 0;
            flex: 1;
        }
        .club-form-card strong,
        .club-form-card span {
            display: block;
        }
        .club-form-card strong {
            color: #f8fafc;
        }
        .club-form-card span {
            color: #94a3b8;
            font-size: 0.78rem;
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
            .form-player-card {
                min-height: 315px;
            }
            .form-card-photo {
                width: 100px;
                height: 100px;
            }
            .form-score-circle {
                width: 76px;
                height: 76px;
            }
            .form-score-circle span {
                font-size: 1.4rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    data_file = find_data_file()
    data = load_data(str(data_file))
    competition_table_path, competition_results_path = find_competition_files()
    team_match_stats_path = find_team_match_stats_file()
    team_match_stats = load_team_match_stats(
        str(team_match_stats_path) if team_match_stats_path is not None else None
    )
    competition_table, recent_results = load_competition_data(
        (
            str(competition_table_path)
            if competition_table_path is not None
            else None
        ),
        (
            str(competition_results_path)
            if competition_results_path is not None
            else None
        ),
    )

    footrate_competition_table = (
        competition_table[
            competition_table["competition_id"].eq(61)
            & competition_table["season"].eq(2024)
        ].copy()
        if not competition_table.empty
        else pd.DataFrame()
    )
    footrate_recent_results = (
        recent_results[
            recent_results["competition_id"].eq(61)
            & recent_results["season"].eq(2024)
        ].copy()
        if not recent_results.empty
        else pd.DataFrame()
    )
except Exception as exc:
    st.error("Impossible de charger les données FootRate.")
    st.code(str(exc))
    st.info(
        "Vérifie que le fichier footrate_official_v0_6.csv se trouve dans le dossier output."
    )
    st.stop()

render_header(data_file)

(
    tab_home,
    tab_ranking,
    tab_clubs,
    tab_league,
    tab_analysis,
    tab_profile,
    tab_compare,
    tab_method,
) = st.tabs(
    [
        "🏠 Accueil",
        "🏆 Joueurs",
        "⚽ Clubs",
        "🌍 Championnats",
        "🔎 Analyse avancée",
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
    render_clubs(
        data,
        footrate_competition_table,
        footrate_recent_results,
    )

with tab_league:
    render_league(
        data,
        competition_table,
        recent_results,
    )

with tab_analysis:
    render_advanced_analysis(team_match_stats)

with tab_profile:
    render_player_profile(data)

with tab_compare:
    render_comparison(data)

with tab_method:
    render_methodology()
