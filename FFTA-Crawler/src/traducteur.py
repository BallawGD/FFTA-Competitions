import json
import math
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

JSON_ENTREE = DATA_DIR / "competitions.json"

JSON_TRADUIT = DATA_DIR / "competitions_traduites.json"

HTML_YAPLA = DATA_DIR / "competitions_yapla.html"

REPO_DIR = BASE_DIR.parent

JSON_PUBLIC = REPO_DIR / "competitions.json"

URL_JSON_PUBLIC = (
    "https://ballawgd.github.io/FFTA-Competitions/competitions.json"
)

CODE_POSTAL_REFERENCE = "37000"


# ============================================================
# DISCIPLINES
# ============================================================

DISCIPLINES_YAPLA = {
    "Tir à l'Arc Extérieur": "TAE",
    "Tir Campagne": "Campagne",
    "Tir 3D": "3D",
    "Tir Nature": "Nature",
    "Tir Beursault": "Beursault",
    "Tir à 18m": "18m",
    "Loisirs Confirmé": "Loisir"
}


# ============================================================
# MOIS FRANÇAIS
# ============================================================

MOIS = {
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


# ============================================================
# SESSION HTTP
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
})


# ============================================================
# NORMALISATION
# ============================================================

def normaliser_texte(texte):

    if not texte:
        return texte

    texte = str(texte)

    texte = re.sub(
        r"\s+",
        " ",
        texte
    )

    return texte.strip()


# ============================================================
# GÉOCODAGE
# ============================================================

def geocoder(recherche):

    if not recherche:
        return None

    print(
        f"      🌍 Requête Nominatim : {recherche}",
        flush=True
    )

    try:

        response = SESSION.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": recherche,
                "format": "json",
                "limit": 1,
                "countrycodes": "fr"
            },
            timeout=(5, 10)
        )

        print(
            f"         📡 HTTP {response.status_code}",
            flush=True
        )

        if response.status_code != 200:

            print(
                f"         ❌ Erreur HTTP {response.status_code}",
                flush=True
            )

            return None

        resultats = response.json()

        if not resultats:

            print(
                "         ❌ Aucun résultat",
                flush=True
            )

            return None

        resultat = resultats[0]

        latitude = float(
            resultat["lat"]
        )

        longitude = float(
            resultat["lon"]
        )

        print(
            f"         ✅ {latitude}, {longitude}",
            flush=True
        )

        return {
            "latitude": latitude,
            "longitude": longitude
        }

    except requests.exceptions.Timeout:

        print(
            "         ⏱️ Timeout Nominatim",
            flush=True
        )

        return None

    except requests.exceptions.RequestException as e:

        print(
            f"         ⚠️ Erreur réseau : {e}",
            flush=True
        )

        return None

    except Exception as e:

        print(
            f"         ⚠️ Erreur : {e}",
            flush=True
        )

        return None


# ============================================================
# DISTANCE HAVERSINE
# ============================================================

def calculer_distance(
    lat1,
    lon1,
    lat2,
    lon2
):

    rayon_terre = 6371

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return rayon_terre * c


# ============================================================
# DATES
# ============================================================

def extraire_dates(competition):

    date_debut = competition.get("date_debut")

    date_fin = competition.get("date_fin")

    return date_debut, date_fin


def formater_dates(competition):

    date_debut = competition.get("date_debut")

    date_fin = competition.get("date_fin")

    if not date_debut:
        return ""

    try:

        debut = datetime.strptime(
            date_debut,
            "%Y-%m-%d"
        )

        if not date_fin:

            return (
                f"{debut.day} "
                f"{list(MOIS.keys())[debut.month - 1]}"
            )

        fin = datetime.strptime(
            date_fin,
            "%Y-%m-%d"
        )

        mois_debut = list(
            MOIS.keys()
        )[debut.month - 1]

        mois_fin = list(
            MOIS.keys()
        )[fin.month - 1]

        if debut == fin:

            return (
                f"{debut.day} "
                f"{mois_debut}"
            )

        if (
            debut.month == fin.month
            and debut.year == fin.year
        ):

            return (
                f"{debut.day}-{fin.day} "
                f"{mois_debut}"
            )

        return (
            f"{debut.day} {mois_debut}"
            f" - "
            f"{fin.day} {mois_fin}"
        )

    except Exception:

        return ""


# ============================================================
# NOM DE LA COMPÉTITION
# ============================================================

def obtenir_nom(competition):

    nom = (
        competition.get("lieu")
        or competition.get("nom")
        or "Compétition"
    )

    return normaliser_texte(nom)


# ============================================================
# HTML YAPLA
# ============================================================

def generer_html_yapla():

    html = r'''
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet" />
<link crossorigin="" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" rel="stylesheet" />

<div class="filtres-competitions-wrapper">

<div class="filtres-wrapper">
<div class="filtres-container">

<div class="filtre filtre-select">
<select id="discipline">
<option value="">Toutes</option>
<option value="TAE">TAE</option>
<option value="Campagne">Campagne</option>
<option value="3D">3D</option>
<option value="Nature">Nature</option>
<option value="Beursault">Beursault</option>
<option value="18m">18m</option>
<option value="Loisir">Loisir</option>
</select>
</div>

<div class="filtre distance-filtre">

<label>
Distance max :
<span id="distanceValue">Indre-et-Loire</span>
</label>

<input
id="distanceRange"
max="36"
min="0"
step="1"
type="range"
value="0"
/>

</div>

<div class="filtre date-filtre">

<label for="dateDebut">
Du :
</label>

<input
id="dateDebut"
type="date"
/>

</div>

<div class="filtre date-filtre">

<label for="dateFin">
Au :
</label>

<input
id="dateFin"
type="date"
/>

</div>

<div class="filtre reset-filtre">

<button
id="resetDates"
type="button"
>
Réinitialiser
</button>

</div>

</div>
</div>

<div id="map" style="height:500px; width:100%; margin:30px auto;">
&nbsp;
</div>

<div class="competitions-wrapper">
<div class="competitions-grid">
&nbsp;
</div>
</div>

</div>

<style type="text/css">

.filtres-wrapper {
  width:100%;
  display:flex;
  justify-content:center;
  margin:20px 0;
  font-family:'Roboto',sans-serif;
}

.filtres-container {
  display:flex;
  gap:20px;
  align-items:end;
  flex-wrap:wrap;
  justify-content:center;
}

.filtre {
  display:flex;
  flex-direction:column;
}

.filtre-select select {
  padding:0 12px;
  font-size:18px;
  width:220px;
  height:46px;
  border:2px solid #333870;
  border-radius:6px;
  color:#333870;
  background-color:white;
  cursor:pointer;
  appearance:none;
  background-image:url('data:image/svg+xml;utf8,<svg fill="%230063FF" height="24" viewBox="0 0 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5z"/></svg>');
  background-repeat:no-repeat;
  background-position:right 12px center;
  background-size:18px;
}

.filtre-select select::-ms-expand {
  display:none;
}

.distance-filtre input {
  width:260px;
  margin-top:0px;
}

.distance-filtre label {
  color:#333870;
  font-weight:bold;
  margin-bottom:5px;
}

input[type=range]::-webkit-slider-thumb {
  -webkit-appearance:none;
  width:18px;
  height:18px;
  border-radius:50%;
  background:#333870;
  cursor:pointer;
}

.date-filtre label {
  color:#333870;
  font-weight:bold;
  margin-bottom:5px;
}

.date-filtre input {
  width:170px;
  height:42px;
  padding:0 10px;
  font-size:16px;
  border:2px solid #333870;
  border-radius:6px;
  color:#333870;
  background-color:white;
  font-family:'Roboto',sans-serif;
  box-sizing:border-box;
}

.reset-filtre button {
  height:42px;
  padding:0 15px;
  border:2px solid #333870;
  border-radius:6px;
  background:white;
  color:#333870;
  font-family:'Roboto',sans-serif;
  font-size:15px;
  font-weight:bold;
  cursor:pointer;
}

.reset-filtre button:hover {
  background:#333870;
  color:white;
}

.competitions-wrapper {
  width:100%;
  display:flex;
  justify-content:center;
  margin-top:30px;
  font-family:'Roboto',sans-serif;
}

.competitions-grid {
  max-width:1100px;
  width:100%;
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:25px;
  font-size:0;
}

.competition-card {
  border:5px solid #333870;
  border-radius:8px;
  padding:20px;
  text-align:center;
  font-family:'Roboto',sans-serif;
  position:relative;
  font-size:16px;
}

.competition-title {
  margin:0;
  color:#333870;
}

.type {
  position:absolute;
  top:20px;
  right:20px;
  font-weight:bold;
}

.distance,
.dates {
  margin-top:3px;
  color:#333870;
}

.ffta-button {
  display:inline-block;
  margin-top:14px;
  padding:8px 14px;
  background:#333870;
  color:white !important;
  text-decoration:none !important;
  border-radius:5px;
  font-size:13px;
  font-weight:700;
  transition:opacity 0.2s ease;
}

.ffta-button:hover {
  opacity:0.8;
}

.competition-card.type-TAE {
  border-color:#333870;
}

.competition-card.type-Campagne {
  border-color:#F5B61D;
}

.competition-card.type-3D {
  border-color:#006400;
}

.competition-card.type-Nature {
  border-color:#FF0000;
}

.competition-card.type-Beursault {
  border-color:#000000;
}

.competition-card.type-18m {
  border-color:#8B4513;
}

.competition-card.type-Loisir {
  border-color:#800080;
}

.type.type-TAE {
  color:#333870;
}

.type.type-Campagne {
  color:#F5B61D;
}

.type.type-3D {
  color:#006400;
}

.type.type-Nature {
  color:#FF0000;
}

.type.type-Beursault {
  color:#000000;
}

.type.type-18m {
  color:#8B4513;
}

.type.type-Loisir {
  color:#800080;
}

@media (max-width:768px) {

  .filtres-container {
    flex-direction:column;
    gap:20px;
    align-items:center;
  }

  .competitions-grid {
    grid-template-columns:1fr;
    font-size:0;
  }

  .competition-card {
    font-size:16px;
  }

}

</style>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>

<script>

document.addEventListener("DOMContentLoaded", function(){

  fetch("https://ballawgd.github.io/FFTA-Competitions/competitions.json")

    .then(response => {

      if(!response.ok) {

        throw new Error(
          "Erreur HTTP " + response.status
        );

      }

      return response.json();

    })

    .then(competitions => {


      // ==========================================
      // CONVERSION DES DATES
      // ==========================================

      function convertirDate(dateString) {

        if(!dateString) {
          return null;
        }

        const morceaux =
          dateString.split("-");

        if(morceaux.length !== 3) {
          return null;
        }

        const annee =
          Number(morceaux[0]);

        const mois =
          Number(morceaux[1]) - 1;

        const jour =
          Number(morceaux[2]);

        if(
          !Number.isInteger(annee) ||
          !Number.isInteger(mois) ||
          !Number.isInteger(jour)
        ) {

          return null;

        }

        const resultat =
          new Date(
            annee,
            mois,
            jour
          );

        if(
          isNaN(resultat.getTime())
        ) {

          return null;

        }

        return resultat;

      }


      // ==========================================
      // DATE DU JOUR
      // ==========================================

      const aujourdHui =
        new Date();

      aujourdHui.setHours(
        0,
        0,
        0,
        0
      );


      // ==========================================
      // SUPPRESSION DES COMPÉTITIONS TERMINÉES
      // ==========================================

      competitions =
        competitions.filter(
          comp => {

            const dateFin =
              convertirDate(
                comp.date_fin
              );

            if(!dateFin) {

              return true;

            }

            return dateFin >= aujourdHui;

          }
        );


      // ==========================================
      // TRI CHRONOLOGIQUE
      // ==========================================

      competitions.sort(
        (a,b) => {

          const dateA =
            convertirDate(
              a.date_debut
            );

          const dateB =
            convertirDate(
              b.date_debut
            );

          if(!dateA && !dateB) {

            return 0;

          }

          if(!dateA) {

            return 1;

          }

          if(!dateB) {

            return -1;

          }

          return dateA - dateB;

        }
      );


      // ==========================================
      // GESTION DES POSITIONS IDENTIQUES
      // ==========================================

      const locationCounts = {};

      competitions.forEach(comp => {

        const key =
          comp.lat + "," + comp.lng;

        if(!locationCounts[key]) {

          locationCounts[key] = 0;

        } else {

          const offset =
            0.0025 *
            locationCounts[key];

          const angle =
            locationCounts[key] *
            45 *
            Math.PI /
            180;

          comp.lat +=
            Math.sin(angle) *
            offset;

          comp.lng +=
            Math.cos(angle) *
            offset;

        }

        locationCounts[key]++;

      });


      // ==========================================
      // CARTE
      // ==========================================

      const map =
        L.map('map').setView(
          [46.5, 2],
          6
        );


      L.tileLayer(
        'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        {
          attribution:
            '&copy; OpenStreetMap contributors',
          maxZoom:18
        }
      ).addTo(map);


      // ==========================================
      // COULEURS DES DISCIPLINES
      // ==========================================

      const typeColors = {

        "TAE":"blue",
        "Campagne":"orange",
        "3D":"green",
        "Nature":"red",
        "Beursault":"black",
        "18m":"brown",
        "Loisir":"purple"

      };


      // ==========================================
      // MARQUEURS
      // ==========================================

      const markers = [];


      competitions.forEach(
        (comp,index)=>{

          const marker =
            L.circleMarker(
              [comp.lat,comp.lng],
              {

                radius:8,

                fillColor:
                  typeColors[comp.type] ||
                  "gray",

                color:"#fff",

                weight:1,

                opacity:1,

                fillOpacity:0.9

              }
            ).addTo(map);


          marker.bindPopup(`

            <div style="text-align:center; font-family:Roboto,sans-serif;">

              <strong style="color:#333870;">
                ${comp.nom}
              </strong>

              <br>

              <span>
                ${comp.type} - ${comp.dates}
              </span>

              <br>

              <a
                href="${comp.lien}"
                target="_blank"
                rel="noopener noreferrer"
                class="ffta-button"
              >
                Fiche FFTA
              </a>

            </div>

          `);


          marker.competitionIndex =
            index;


          marker.on(
            "mouseover",
            () => {

              marker.openPopup();

              const color =
                marker.options.fillColor ||
                "gray";

              const popupEl =
                marker.getPopup().getElement();


              if(popupEl){

                popupEl.style.border =
                  `3px solid ${color}`;

                popupEl.style.borderRadius =
                  "15px";


                const content =
                  popupEl.querySelector(
                    ".leaflet-popup-content"
                  );


                if(content){

                  content.style.fontFamily =
                    "Roboto, sans-serif";

                  content.style.fontSize =
                    "12px";

                  content.style.fontWeight =
                    "500";

                  content.style.color =
                    "#333870";

                }

              }

            }
          );


          marker.on(
            "mouseout",
            () => {

              marker.closePopup();

            }
          );


          marker.on(
            "click",
            () => {

              const card =
                document.querySelectorAll(
                  ".competition-card"
                )[marker.competitionIndex];


              if(card) {

                card.scrollIntoView({
                  behavior:"smooth"
                });

              }

            }
          );


          markers.push(
            marker
          );

        }
      );


      // ==========================================
      // CRÉATION DES CARTES
      // ==========================================

      const grid =
        document.querySelector(
          ".competitions-grid"
        );


      competitions.forEach(
        comp=>{

          const card =
            document.createElement(
              "div"
            );


          card.className =
            `competition-card type-${comp.type}`;


          card.dataset.discipline =
            comp.type;


          card.dataset.distance =
            comp.distance;


          card.dataset.codePostal =
            comp.code_postal || "";


          card.dataset.dateDebut =
            comp.date_debut;


          card.dataset.dateFin =
            comp.date_fin;


          let displayType =
            comp.type;


          if(
            comp.type === "Beursault"
          ) {

            displayType =
              "B";

          } else if(
            comp.type === "Campagne"
          ) {

            displayType =
              "C";

          } else if(
            comp.type === "18m"
          ) {

            displayType =
              "18m";

          } else if(
            comp.type === "Loisir"
          ) {

            displayType =
              "Loisir";

          }


          card.innerHTML = `

            <h3 class="competition-title">
              ${comp.nom}
            </h3>

            <span class="type type-${comp.type}">
              ${displayType}
            </span>

            <div class="distance">
              ${comp.distance} km
            </div>

            <div class="dates">
              ${comp.dates}
            </div>

            <a
              href="${comp.lien}"
              target="_blank"
              rel="noopener noreferrer"
              class="ffta-button"
            >
              Voir la fiche FFTA
            </a>

          `;


          grid.appendChild(
            card
          );

        }
      );


      // ==========================================
      // FILTRES
      // ==========================================

      const selectDiscipline =
        document.getElementById(
          "discipline"
        );


      const range =
        document.getElementById(
          "distanceRange"
        );


      const value =
        document.getElementById(
          "distanceValue"
        );


      const dateDebutInput =
        document.getElementById(
          "dateDebut"
        );


      const dateFinInput =
        document.getElementById(
          "dateFin"
        );


      const resetDates =
        document.getElementById(
          "resetDates"
        );


      const cards =
        document.querySelectorAll(
          ".competition-card"
        );


      // ==========================================
      // FILTRAGE
      // ==========================================

      function filterCards() {

        const discipline =
          selectDiscipline.value;


        // ======================================
        // FILTRE DISTANCE
        //
        // 0  = Indre-et-Loire
        //      uniquement les codes 37xxx
        //
        // 1  = 60 km
        // 2  = 70 km
        // ...
        // 35 = 400 km
        // 36 = France = 1500 km
        // ======================================

        const sliderValue =
          parseInt(
            range.value
          );


        let maxDistance = 60;

        let indreEtLoire = false;


        if(sliderValue === 0) {

          indreEtLoire = true;

          maxDistance = 60;

        } else if(sliderValue === 36) {

          maxDistance = 1500;

        } else {

          maxDistance =
            50 + (sliderValue * 10);

        }


        const dateDebutRecherche =
          dateDebutInput.value
            ? convertirDate(
                dateDebutInput.value
              )
            : null;


        const dateFinRecherche =
          dateFinInput.value
            ? convertirDate(
                dateFinInput.value
              )
            : null;


        const bounds =
          L.latLngBounds();


        cards.forEach(
          (card,i)=>{

            const cardDiscipline =
              card.dataset.discipline;


            const cardDistance =
              parseFloat(
                card.dataset.distance
              );


            const cardCodePostal =
              card.dataset.codePostal ||
              "";


            const dateDebut =
              convertirDate(
                card.dataset.dateDebut
              );


            const dateFin =
              convertirDate(
                card.dataset.dateFin
              );


            // ==================================
            // FILTRE DATE
            // ==================================

            let competitionActive =
              true;


            if(dateFin){

              competitionActive =
                dateFin >= aujourdHui;

            }


            let correspondDate =
              true;


            if(
              dateDebutRecherche &&
              dateFinRecherche
            ){

              correspondDate =
                dateDebut &&
                dateFin &&
                dateDebut <= dateFinRecherche &&
                dateFin >= dateDebutRecherche;

            } else if(
              dateDebutRecherche
            ){

              correspondDate =
                dateFin &&
                dateFin >= dateDebutRecherche;

            } else if(
              dateFinRecherche
            ){

              correspondDate =
                dateDebut &&
                dateDebut <= dateFinRecherche;

            }


            // ==================================
            // FILTRE INDRE-ET-LOIRE
            // ==================================

            let correspondDistance =
              true;


            if(indreEtLoire){

              correspondDistance =
                /^37\d{3}$/.test(
                  cardCodePostal
                );

            } else {

              correspondDistance =
                cardDistance <= maxDistance;

            }


            // ==================================
            // FILTRE GLOBAL
            // ==================================

            const show =
              competitionActive
              &&
              correspondDate
              &&
              (
                discipline === ""
                ||
                discipline === cardDiscipline
              )
              &&
              correspondDistance;


            card.style.display =
              show
                ? "block"
                : "none";


            if(show){

              if(
                !map.hasLayer(
                  markers[i]
                )
              ){

                markers[i].addTo(
                  map
                );

              }


              bounds.extend(
                markers[i].getLatLng()
              );


            } else {

              if(
                map.hasLayer(
                  markers[i]
                )
              ){

                map.removeLayer(
                  markers[i]
                );

              }

            }

          }
        );


        if(bounds.isValid()){

          map.fitBounds(
            bounds,
            {
              padding:[
                50,
                50
              ]
            }
          );

        }

      }


      // ==========================================
      // SLIDER DISTANCE
      // ==========================================

      range.addEventListener(
        "input",
        ()=>{

          const sliderValue =
            parseInt(
              range.value
            );


          if(sliderValue === 0){

            value.textContent =
              "Indre-et-Loire";

          } else if(sliderValue === 36){

            value.textContent =
              "France";

          } else {

            value.textContent =
              (50 + sliderValue * 10) +
              " km";

          }


          filterCards();

        }
      );


      // ==========================================
      // FILTRE DISCIPLINE
      // ==========================================

      selectDiscipline.addEventListener(
        "change",
        filterCards
      );


      // ==========================================
      // FILTRE DATE DEBUT
      // ==========================================

      dateDebutInput.addEventListener(
        "change",
        ()=>{

          filterCards();

        }
      );


      // ==========================================
      // FILTRE DATE FIN
      // ==========================================

      dateFinInput.addEventListener(
        "change",
        ()=>{

          filterCards();

        }
      );


      // ==========================================
      // RÉINITIALISATION
      // ==========================================

      resetDates.addEventListener(
        "click",
        ()=>{

          dateDebutInput.value = "";
          dateFinInput.value = "";

          range.value = 0;

          value.textContent =
            "Indre-et-Loire";

          filterCards();

        }
      );


      // ==========================================
      // FILTRAGE INITIAL
      // ==========================================

      filterCards();

    })


    // ==========================================
    // ERREUR DE CHARGEMENT
    // ==========================================

    .catch(
      error => {

        console.error(
          "Erreur lors du chargement des compétitions :",
          error
        );


        document.querySelector(
          ".competitions-grid"
        ).innerHTML =
          "<p>Impossible de charger les compétitions.</p>";

      }
    );

});

</script>
'''

    return html


# ============================================================
# PUBLICATION GITHUB
# ============================================================

def publier_sur_github():

    print()
    print("📤 Publication du JSON sur GitHub...")

    if not (REPO_DIR / ".git").exists():

        print(
            f"❌ Le dossier suivant n'est pas "
            f"un dépôt Git : {REPO_DIR}"
        )

        return False

    try:

        subprocess.run(
            [
                "git",
                "-C",
                str(REPO_DIR),
                "add",
                "competitions.json"
            ],
            check=True
        )

        result = subprocess.run(
            [
                "git",
                "-C",
                str(REPO_DIR),
                "diff",
                "--cached",
                "--quiet"
            ]
        )

        if result.returncode == 0:

            print(
                "ℹ️ Aucun changement dans "
                "competitions.json."
            )

            return True

        subprocess.run(
            [
                "git",
                "-C",
                str(REPO_DIR),
                "commit",
                "-m",
                "Mise à jour des compétitions"
            ],
            check=True
        )

        subprocess.run(
            [
                "git",
                "-C",
                str(REPO_DIR),
                "push"
            ],
            check=True
        )

        print()
        print(
            "✅ JSON publié sur GitHub."
        )

        print(
            f"🌐 {URL_JSON_PUBLIC}"
        )

        return True

    except subprocess.CalledProcessError as e:

        print()
        print(
            f"❌ Erreur lors de la publication Git : {e}"
        )

        return False


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    print()
    print("=" * 42)
    print("TRADUCTION DES COMPÉTITIONS FFTA")
    print("=" * 42)
    print()


    # ========================================================
    # CHARGEMENT
    # ========================================================

    print(
        f"📂 Lecture : {JSON_ENTREE}"
    )

    with open(
        JSON_ENTREE,
        "r",
        encoding="utf-8"
    ) as fichier:

        competitions = json.load(fichier)


    total_initial = len(
        competitions
    )


    # ========================================================
    # GÉOCODAGE DU CODE POSTAL DE RÉFÉRENCE
    # ========================================================

    print()
    print(
        f"📍 Géocodage du code postal "
        f"de référence : {CODE_POSTAL_REFERENCE}"
    )

    localisation_reference = geocoder(
        CODE_POSTAL_REFERENCE
    )

    if not localisation_reference:

        print(
            "❌ Impossible de géocoder "
            "le code postal de référence."
        )

        return


    lat_reference = localisation_reference["latitude"]

    lng_reference = localisation_reference["longitude"]


    print(
        f"✅ Référence : "
        f"{lat_reference}, "
        f"{lng_reference}"
    )


    # ========================================================
    # VARIABLES
    # ========================================================

    competitions_traduites = []

    compte_discipline = 0

    compte_date = 0

    compte_comites = 0

    compte_geolocalisation = 0


    # ========================================================
    # CACHE GÉOCODAGE
    # ========================================================

    cache_geocodage = {
        CODE_POSTAL_REFERENCE: localisation_reference
    }


    # ========================================================
    # TRAITEMENT
    # ========================================================

    for index, competition in enumerate(
        competitions,
        start=1
    ):

        # ----------------------------------------------------
        # DISCIPLINE
        # ----------------------------------------------------

        discipline = competition.get("discipline")

        if discipline not in DISCIPLINES_YAPLA:

            continue

        compte_discipline += 1


        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        date_debut, date_fin = extraire_dates(
            competition
        )

        if date_fin:

            try:

                date_fin_obj = datetime.strptime(
                    date_fin,
                    "%Y-%m-%d"
                ).date()

                if date_fin_obj < datetime.now().date():

                    continue

            except ValueError:

                pass

        compte_date += 1


        # ----------------------------------------------------
        # FILTRE COMPÉTITIONS ÉTRANGÈRES
        # ----------------------------------------------------

        comite_regional = competition.get(
            "comite_regional"
        )

        comite_departemental = competition.get(
            "comite_departemental"
        )

        code_postal = competition.get(
            "code_postal"
        )


        if (
            not comite_regional
            and
            not comite_departemental
            and
            not code_postal
        ):

            continue

        compte_comites += 1


        # ----------------------------------------------------
        # NORMALISATION DU CODE POSTAL
        # ----------------------------------------------------

        if code_postal:

            code_postal = str(
                code_postal
            ).strip()

        else:

            code_postal = None


        # ----------------------------------------------------
        # GÉOLOCALISATION
        # ----------------------------------------------------

        localisation = None

        print(
            f"[{index}/{total_initial}] "
            f"📍 {competition.get('lieu') or 'Lieu inconnu'}",
            flush=True
        )


        # ----------------------------------------------------
        # PRIORITÉ AU CODE POSTAL
        # ----------------------------------------------------

        if code_postal:

            if code_postal in cache_geocodage:

                localisation = cache_geocodage[
                    code_postal
                ]

                print(
                    f"   💾 Cache : {code_postal}",
                    flush=True
                )

            else:

                localisation = geocoder(
                    code_postal
                )

                cache_geocodage[
                    code_postal
                ] = localisation

                time.sleep(1)


        # ----------------------------------------------------
        # SI ÉCHEC : GÉOCODAGE DU LIEU
        # ----------------------------------------------------

        if not localisation:

            lieu = competition.get(
                "lieu"
            )

            if lieu:

                lieu = normaliser_texte(
                    lieu
                )

                if lieu in cache_geocodage:

                    localisation = cache_geocodage[
                        lieu
                    ]

                    print(
                        f"   💾 Cache lieu : {lieu}",
                        flush=True
                    )

                else:

                    print(
                        f"   🔄 Tentative avec le lieu : {lieu}",
                        flush=True
                    )

                    localisation = geocoder(
                        lieu
                    )

                    cache_geocodage[
                        lieu
                    ] = localisation

                    time.sleep(1)


        # ----------------------------------------------------
        # ÉCHEC DE GÉOLOCALISATION
        # ----------------------------------------------------

        if not localisation:

            print(
                "   ❌ Impossible de géolocaliser",
                flush=True
            )

            continue


        compte_geolocalisation += 1

        print(
            f"   ✅ Géolocalisé "
            f"({compte_geolocalisation} conservées)",
            flush=True
        )


        # ----------------------------------------------------
        # DISTANCE
        # ----------------------------------------------------

        distance = calculer_distance(
            lat_reference,
            lng_reference,
            localisation["latitude"],
            localisation["longitude"]
        )

        distance = round(
            distance,
            1
        )


        # ----------------------------------------------------
        # TYPE YAPLA
        # ----------------------------------------------------

        type_yapla = DISCIPLINES_YAPLA[
            discipline
        ]


        # ----------------------------------------------------
        # NOM
        # ----------------------------------------------------

        nom = obtenir_nom(
            competition
        )


        # ----------------------------------------------------
        # LIEN FFTA
        # ----------------------------------------------------

        competition_id = competition.get(
            "id"
        )

        lien = None

        if competition_id:

            lien = (
                "https://www.ffta.fr/epreuve/"
                f"{competition_id}"
            )


        # ----------------------------------------------------
        # DATES AFFICHÉES
        # ----------------------------------------------------

        dates = formater_dates(
            competition
        )


        # ----------------------------------------------------
        # OBJET FINAL
        # ----------------------------------------------------

        competition_traduite = {
            "nom": nom,
            "dates": dates,
            "type": type_yapla,
            "distance": distance,
            "lat": localisation["latitude"],
            "lng": localisation["longitude"],
            "lien": lien,
            "code_postal": code_postal,
            "date_debut": date_debut,
            "date_fin": date_fin
        }


        competitions_traduites.append(
            competition_traduite
        )


    # ========================================================
    # TRI FINAL
    # ========================================================

    competitions_traduites.sort(
        key=lambda competition: (
            competition.get(
                "date_debut"
            )
            or "9999-12-31"
        )
    )


    # ========================================================
    # ÉCRITURE JSON TRADUIT
    # ========================================================

    with open(
        JSON_TRADUIT,
        "w",
        encoding="utf-8"
    ) as fichier:

        json.dump(
            competitions_traduites,
            fichier,
            ensure_ascii=False,
            indent=2
        )


    # ========================================================
    # COPIE JSON PUBLIC
    # ========================================================

    with open(
        JSON_PUBLIC,
        "w",
        encoding="utf-8"
    ) as fichier:

        json.dump(
            competitions_traduites,
            fichier,
            ensure_ascii=False,
            indent=2
        )


    # ========================================================
    # GÉNÉRATION HTML YAPLA
    # ========================================================

    html_yapla = generer_html_yapla()

    with open(
        HTML_YAPLA,
        "w",
        encoding="utf-8"
    ) as fichier:

        fichier.write(
            html_yapla
        )


    # ========================================================
    # RÉSUMÉ
    # ========================================================

    print()
    print("=" * 42)
    print("TRADUCTION TERMINÉE")
    print("=" * 42)

    print(
        f"Compétitions initiales : "
        f"{total_initial}"
    )

    print(
        f"Après filtre discipline : "
        f"{compte_discipline}"
    )

    print(
        f"Après filtre date : "
        f"{compte_date}"
    )

    print(
        f"Après filtre comités : "
        f"{compte_comites}"
    )

    print(
        f"Après géolocalisation : "
        f"{compte_geolocalisation}"
    )

    print(
        f"Compétitions conservées : "
        f"{len(competitions_traduites)}"
    )

    print()

    print(
        f"JSON traduit : "
        f"{JSON_TRADUIT}"
    )

    print(
        f"JSON public : "
        f"{JSON_PUBLIC}"
    )

    print(
        f"HTML Yapla : "
        f"{HTML_YAPLA}"
    )


    # ========================================================
    # PUBLICATION GITHUB
    # ========================================================

    publication_reussie = publier_sur_github()


    print()
    print("=" * 42)

    if publication_reussie:

        print(
            "✅ TRAITEMENT TERMINÉ "
            "ET GITHUB À JOUR"
        )

    else:

        print(
            "⚠️ TRAITEMENT TERMINÉ "
            "MAIS PUBLICATION GITHUB "
            "NON EFFECTUÉE"
        )

    print("=" * 42)
    print()


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    main()