import re
import json
import requests
from bs4 import BeautifulSoup


def scrape_competition(competition_id):
    url = f"https://www.ffta.fr/epreuve/{competition_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/140.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)

    # ==========================================
    # GESTION DE LA RÉPONSE HTTP
    # ==========================================

    if response.status_code == 404:
        return "not_found"

    if response.status_code != 200:
        return "error"

    soup = BeautifulSoup(response.text, "html.parser")


    # ==========================================
    # NOM
    # ==========================================

    title = soup.find("h1")

    if not title:
        return "not_found"

    competition_name = title.get_text(strip=True)


    # ==========================================
    # FONCTION POUR RÉCUPÉRER LES CHAMPS
    # ==========================================

    def get_field(label):
        for element in soup.find_all("p"):
            if label in element.get_text():
                strong = element.find("strong")

                if strong:
                    return strong.get_text(strip=True)

        return None


    # ==========================================
    # DATE
    # ==========================================

    date_element = soup.select_one(".competition_detail__dates")

    date_debut = None
    date_fin = None

    if date_element:

        date_text = date_element.get_text(" ", strip=True)

        months = {
            "janvier": "01",
            "février": "02",
            "mars": "03",
            "avril": "04",
            "mai": "05",
            "juin": "06",
            "juillet": "07",
            "août": "08",
            "septembre": "09",
            "octobre": "10",
            "novembre": "11",
            "décembre": "12"
        }


        # ------------------------------------------
        # Format : "Le 06 septembre 2026"
        # ------------------------------------------

        match_single = re.search(
            r"Le\s+(\d{1,2})\s+([a-zéûàô]+)\s+(\d{4})",
            date_text,
            re.IGNORECASE
        )


        # ------------------------------------------
        # Format : "Du 11 au 13 septembre 2026"
        # ------------------------------------------

        match_same_month = re.search(
            r"Du\s+(\d{1,2})\s+au\s+(\d{1,2})\s+([a-zéûàô]+)\s+(\d{4})",
            date_text,
            re.IGNORECASE
        )


        # ------------------------------------------
        # Format : "Du 17 avril au 15 mai 2026"
        # ------------------------------------------

        match_different_month = re.search(
            r"Du\s+(\d{1,2})\s+([a-zéûàô]+)\s+au\s+(\d{1,2})\s+([a-zéûàô]+)\s+(\d{4})",
            date_text,
            re.IGNORECASE
        )


        # ==========================================
        # TRAITEMENT DES DATES
        # ==========================================

        if match_different_month:

            day_debut = match_different_month.group(1)
            month_debut_name = match_different_month.group(2).lower()

            day_fin = match_different_month.group(3)
            month_fin_name = match_different_month.group(4).lower()

            year = match_different_month.group(5)

            month_debut = months.get(month_debut_name)
            month_fin = months.get(month_fin_name)

            if month_debut and month_fin:

                date_debut = (
                    f"{year}-{month_debut}-{day_debut.zfill(2)}"
                )

                date_fin = (
                    f"{year}-{month_fin}-{day_fin.zfill(2)}"
                )


        elif match_same_month:

            day_debut = match_same_month.group(1)
            day_fin = match_same_month.group(2)

            month_name = match_same_month.group(3).lower()

            year = match_same_month.group(4)

            month = months.get(month_name)

            if month:

                date_debut = (
                    f"{year}-{month}-{day_debut.zfill(2)}"
                )

                date_fin = (
                    f"{year}-{month}-{day_fin.zfill(2)}"
                )


        elif match_single:

            day = match_single.group(1)
            month_name = match_single.group(2).lower()
            year = match_single.group(3)

            month = months.get(month_name)

            if month:

                date_debut = (
                    f"{year}-{month}-{day.zfill(2)}"
                )

                date_fin = date_debut


        else:

            print(
                f"  ⚠️ Format de date inconnu : {date_text}"
            )


    # ==========================================
    # AUTRES INFORMATIONS
    # ==========================================

    discipline = get_field("Discipline :")

    comite_regional = get_field(
        "Comité régional :"
    )

    comite_departemental = get_field(
        "Comité départemental :"
    )

    organisateur = get_field(
        "Organisateur :"
    )

    lieu = get_field(
        "Lieu :"
    )


    # ==========================================
    # CODE POSTAL
    # ==========================================

    code_postal = None

    lieu_element = None

    for element in soup.find_all("p"):

        if "Lieu :" in element.get_text():

            lieu_element = element
            break


    if lieu_element:

        container = lieu_element.parent

        text = container.get_text(
            " ",
            strip=True
        )

        match = re.search(
            r"\b\d{5}\b",
            text
        )

        if match:

            code_postal = match.group()


    # ==========================================
    # RÉSULTAT
    # ==========================================

    competition = {

        "id": competition_id,

        "nom": competition_name,

        "date_debut": date_debut,

        "date_fin": date_fin,

        "discipline": discipline,

        "comite_regional": comite_regional,

        "comite_departemental": comite_departemental,

        "organisateur": organisateur,

        "lieu": lieu,

        "code_postal": code_postal
    }

    return competition


# ==========================================
# CRAWLER
# ==========================================

start_id = 25201

# Nombre maximum d'IDs inexistantes consécutivement
max_consecutive_missing = 100

competitions = []

competition_id = start_id

consecutive_missing = 0

total_ids_tested = 0


while consecutive_missing < max_consecutive_missing:

    print(
        f"Recherche de la compétition {competition_id}..."
    )

    competition = scrape_competition(
        competition_id
    )

    total_ids_tested += 1


    # ==========================================
    # ID INEXISTANTE
    # ==========================================

    if competition == "not_found":

        consecutive_missing += 1

        print(
            f"  ⚪ ID inexistante "
            f"({consecutive_missing}/{max_consecutive_missing})"
        )


    # ==========================================
    # ERREUR SERVEUR
    # ==========================================

    elif competition == "error":

        print(
            "  🔴 Erreur lors de la récupération"
        )

        # Une erreur serveur ne compte pas comme
        # une ID inexistante.
        # On pourra donc retenter cette zone.


    # ==========================================
    # COMPÉTITION TROUVÉE
    # ==========================================

    else:

        competitions.append(
            competition
        )

        consecutive_missing = 0

        print(
            f"  ✅ {competition['nom']}"
        )

        print(
            f"     {len(competitions)} compétition(s) trouvée(s)"
        )


    competition_id += 1


# ==========================================
# SAUVEGARDE JSON
# ==========================================

with open(
    "data/competitions.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        competitions,
        file,
        ensure_ascii=False,
        indent=4
    )


# ==========================================
# RÉSUMÉ
# ==========================================

print()

print(
    "=========================================="
)

print(
    "CRAWLER TERMINÉ"
)

print(
    "=========================================="
)

print(
    f"IDs testées : {total_ids_tested}"
)

print(
    f"Compétitions trouvées : {len(competitions)}"
)

print(
    f"Dernière ID testée : {competition_id - 1}"
)

print(
    f"IDs inexistantes consécutives : "
    f"{consecutive_missing}"
)

print(
    "JSON créé dans data/competitions.json"
)