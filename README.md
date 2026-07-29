# FootRate

Prototype web de comparaison statistique des joueurs de Ligue 1.

FootRate transforme les performances réelles des joueurs en notes simples sur 100.  
Cette version permet de :

- consulter le classement des joueurs ;
- rechercher par joueur ou par club ;
- filtrer par poste et temps de jeu ;
- afficher une fiche joueur détaillée ;
- comparer deux joueurs ;
- consulter la méthodologie de notation.

## Données utilisées

L'application utilise un instantané statique de la saison de Ligue 1 2024-2025 :

`output/footrate_official_v0_6.csv`

Aucune clé API n'est nécessaire pour faire fonctionner cette version déployée.

## Structure du dépôt

```text
FootRate/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
└── output/
    └── footrate_official_v0_6.csv
```

## Lancement en local

```bash
python -m venv .venv
```

Sous Windows :

```bat
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

L'application s'ouvre généralement sur :

`http://localhost:8501`

## Déploiement sur Streamlit Community Cloud

1. Créer un nouveau dépôt GitHub, par exemple `footrate-app`.
2. Décompresser le ZIP fourni et téléverser **le contenu du dossier**, pas le ZIP lui-même.
3. Vérifier que `app.py` et `requirements.txt` sont à la racine du dépôt.
4. Dans Streamlit Community Cloud, cliquer sur **Create app**.
5. Sélectionner le dépôt, la branche `main` et le fichier principal `app.py`.
6. Dans **Advanced settings**, sélectionner Python 3.13, puis lancer le déploiement.

## Sécurité

Ne jamais publier dans GitHub :

- `.env` ;
- la clé API-Football ;
- `.venv` ;
- le dossier `cache` ;
- `.streamlit/secrets.toml`.

Le fichier `.gitignore` fourni bloque ces éléments lors d'une utilisation normale de Git.
