import json
import math
from datetime import date

import requests


# ==========================================
# CONFIGURATION
# ==========================================

# Code postal de référence pour calculer les distances
CODE_POSTAL_REFERENCE = "37000"

# Disciplines que l'on souhaite conserver
DISCIPLINES_AUTORISEES = {
    "Tir à 18m",
    "Tir 3D",
    "Tir Nature",
    "Tir Campagne",
    "Tir à l'Arc Extérieur",
    "Loisir Confirmé",
    "Tir Beursault"
}

# Conversion des noms FFTA vers les noms utilisés par Yapla
DISCIPLINES_YAPLA = {
    "Tir à l'Arc Extérieur": "TAE",
    "Tir Campagne": "Campagne",
    "Tir 3D": "3D",
    "Tir Nature": "Nature",
    "Tir Beursault": "Beursault",
    "Tir à 18m": "18m",
    "Loisir Confirmé": "Loisir"
}

# Fichiers
FICHIER_ENTREE = "data/competitions.json"
FICHIER_SORTIE_JSON = "data/competitions_traduites.json"
FICHIER_SORTIE_HTML = "data/competitions_yapla.html"


# ==========================================
# OUTILS
# ==========================================

def normaliser_texte(texte):
    """
    Normalise légèrement un texte pour faciliter les comparaisons.
    """

    if not texte:
        return ""

    return " ".join(texte.strip().split())


def distance_km(lat1, lon1, lat2, lon2):
    """
    Calcule la distance à vol d'oiseau entre deux coordonnées
    avec la formule de Haversine.
    """

    rayon_terre = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return rayon_terre * c


# ==========================================
# GÉOLOCALISATION D'UN CODE POSTAL
# ==========================================

def geocoder_code_postal(code_postal):
    """
    Recherche les coordonnées correspondant à un code postal
    via l'API Geo de l'État.
    """

    url = "https://geo.api.gouv.fr/communes"

    params = {
        "codePostal": code_postal,
        "fields": "nom,centre,codesPostaux",
        "format": "json"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return None

        communes = response.json()

        if not communes:
            return None

        commune = communes[0]

        centre = commune.get("centre")

        if not centre:
            return None

        coordinates = centre.get("coordinates")

        if not coordinates or len(coordinates) != 2:
            return None

        return {
            "nom": commune.get("nom"),
            "latitude": coordinates[1],
            "longitude": coordinates[0],
            "code_postal": code_postal
        }

    except requests.RequestException:

        return None


# ==========================================
# GÉOLOCALISATION D'UNE VILLE
# ==========================================

def geocoder_ville(ville):
    """
    Recherche une ville française via l'API Geo de l'État.
    """

    if not ville:
        return None

    url = "https://geo.api.gouv.fr/communes"

    params = {
        "nom": ville,
        "fields": "nom,centre,codesPostaux",
        "format": "json",
        "limit": 5
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return None

        communes = response.json()

        if not communes:
            return None

        commune = communes[0]

        centre = commune.get("centre")
        codes_postaux = commune.get("codesPostaux", [])

        if not centre:
            return None

        coordinates = centre.get("coordinates")

        if not coordinates or len(coordinates) != 2:
            return None

        code_postal = None

        if codes_postaux:
            code_postal = codes_postaux[0]

        return {
            "nom": commune.get("nom"),
            "latitude": coordinates[1],
            "longitude": coordinates[0],
            "code_postal": code_postal
        }

    except requests.RequestException:

        return None


# ==========================================
# ÉCHAPPEMENT JAVASCRIPT
# ==========================================

def echapper_js(texte):
    """
    Protège une chaîne de caractères avant de l'insérer
    dans le JavaScript généré.
    """

    if texte is None:
        return ""

    return (
        str(texte)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "")
        .replace("\n", " ")
    )


# ==========================================
# FORMATAGE DES DATES
# ==========================================

def formater_dates(competition):
    """
    Transforme les dates YYYY-MM-DD du JSON en affichage
    plus lisible pour Yapla.
    """

    date_debut = competition.get("date_debut")
    date_fin = competition.get("date_fin")

    if not date_debut:
        return ""

    mois = {
        "01": "janvier",
        "02": "février",
        "03": "mars",
        "04": "avril",
        "05": "mai",
        "06": "juin",
        "07": "juillet",
        "08": "août",
        "09": "septembre",
        "10": "octobre",
        "11": "novembre",
        "12": "décembre"
    }

    try:

        annee_debut = date_debut[0:4]
        mois_debut = date_debut[5:7]
        jour_debut = int(date_debut[8:10])

        if not date_fin:
            return f"{jour_debut} {mois[mois_debut]}"

        annee_fin = date_fin[0:4]
        mois_fin = date_fin[5:7]
        jour_fin = int(date_fin[8:10])

        # Même jour
        if date_debut == date_fin:
            return f"{jour_debut} {mois[mois_debut]}"

        # Même mois
        if mois_debut == mois_fin and annee_debut == annee_fin:
            return (
                f"{jour_debut}-{jour_fin} "
                f"{mois[mois_debut]}"
            )

        # Mois différents
        return (
            f"{jour_debut} {mois[mois_debut]} - "
            f"{jour_fin} {mois[mois_fin]}"
        )

    except (KeyError, ValueError, TypeError):

        return f"{date_debut} - {date_fin}"


# ==========================================
# GÉNÉRATION DU TABLEAU JAVASCRIPT
# ==========================================

def generer_donnees_javascript(competitions):
    """
    Transforme les compétitions en tableau JavaScript.
    """

    lignes = []

    for competition in competitions:

        nom = echapper_js(
            competition.get("lieu") or
            competition.get("nom") or
            "Compétition"
        )

        dates = echapper_js(
            formater_dates(competition)
        )

        type_yapla = DISCIPLINES_YAPLA.get(
            competition.get("discipline"),
            competition.get("discipline", "")
        )

        type_yapla = echapper_js(type_yapla)

        distance = competition.get("distance_km", 0)

        latitude = competition.get("latitude")
        longitude = competition.get("longitude")

        lien = echapper_js(
            competition.get("lien", "")
        )

        ligne = (
            f'{{ nom: "{nom}", '
            f'dates: "{dates}", '
            f'type: "{type_yapla}", '
            f'distance: {distance}, '
            f'lat: {latitude}, '
            f'lng: {longitude}, '
            f'lien: "{lien}" }}'
        )

        lignes.append(ligne)

    return ",\n".join(lignes)


# ==========================================
# GÉNÉRATION DU HTML YAPLA
# ==========================================

def generer_html_yapla(competitions):
    """
    Génère le bloc HTML/CSS/JavaScript complet
    prêt à être copié dans Yapla.
    """

    donnees_js = generer_donnees_javascript(
        competitions
    )

    html = f'''<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet" />
<link crossorigin="" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" rel="stylesheet" />

<div class="filtres-competitions-wrapper">

<!-- FILTRES -->

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
<span id="distanceValue">250</span> km
</label>

<input id="distanceRange" max="250" min="0" type="range" value="250" />
</div>

</div>
</div>


<!-- CARTE -->

<div id="map" style="height:500px; width:100%; margin:30px auto;">
&nbsp;
</div>


<!-- LISTE DES COMPETITIONS -->

<div class="competitions-wrapper">
<div class="competitions-grid">
&nbsp;
</div>
</div>

</div>


<style type="text/css">

/* ==================== FILTRES ==================== */

.filtres-wrapper {{
  width:100%;
  display:flex;
  justify-content:center;
  margin:20px 0;
  font-family:'Roboto',sans-serif;
}}

.filtres-container {{
  display:flex;
  gap:30px;
  align-items:center;
}}

.filtre {{
  display:flex;
  flex-direction:column;
}}

.filtre-select select {{
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
}}

.filtre-select select::-ms-expand {{
  display:none;
}}

.distance-filtre input {{
  width:260px;
  margin-top:0px;
}}

input[type=range]::-webkit-slider-thumb {{
  -webkit-appearance:none;
  width:18px;
  height:18px;
  border-radius:50%;
  background:#333870;
  cursor:pointer;
}}

.distance-filtre label {{
  color:#333870;
  font-weight:bold;
}}


/* ==================== COMPETITIONS ==================== */

.competitions-wrapper {{
  width:100%;
  display:flex;
  justify-content:center;
  margin-top:30px;
  font-family:'Roboto',sans-serif;
}}

.competitions-grid {{
  max-width:1100px;
  width:100%;
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:25px;
  font-size:0;
}}

.competition-card {{
  border:5px solid #333870;
  border-radius:8px;
  padding:20px;
  text-align:center;
  font-family:'Roboto',sans-serif;
  position:relative;
  font-size:16px;
}}

.competition-title {{
  margin:0;
  color:#333870;
}}

.type {{
  position:absolute;
  top:20px;
  right:20px;
  font-weight:bold;
}}

.distance,
.dates {{
  margin-top:3px;
  color:#333870;
}}


/* ==================== BOUTON FFTA ==================== */

.ffta-button {{
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
}}

.ffta-button:hover {{
  opacity:0.8;
}}


/* ==================== COULEURS ==================== */

.competition-card.type-TAE {{
  border-color:#333870;
}}

.competition-card.type-Campagne {{
  border-color:#F5B61D;
}}

.competition-card.type-3D {{
  border-color:#006400;
}}

.competition-card.type-Nature {{
  border-color:#FF0000;
}}

.competition-card.type-Beursault {{
  border-color:#000000;
}}

.competition-card.type-18m {{
  border-color:#8B4513;
}}

.competition-card.type-Loisir {{
  border-color:#800080;
}}


.type.type-TAE {{
  color:#333870;
}}

.type.type-Campagne {{
  color:#F5B61D;
}}

.type.type-3D {{
  color:#006400;
}}

.type.type-Nature {{
  color:#FF0000;
}}

.type.type-Beursault {{
  color:#000000;
}}

.type.type-18m {{
  color:#8B4513;
}}

.type.type-Loisir {{
  color:#800080;
}}


/* ==================== RESPONSIVE MOBILE ==================== */

@media (max-width:768px) {{

  .filtres-container {{
    flex-direction:column;
    gap:20px;
    align-items:center;
  }}

  .competitions-grid {{
    grid-template-columns:1fr;
    font-size:0;
  }}

  .competition-card {{
    font-size:16px;
  }}

}}

</style>


<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>

<script>

document.addEventListener("DOMContentLoaded", function() {{

  // ==================== DONNÉES ====================

  const competitions = [
{donnees_js}
  ];


  // ==================== DECALAGE DES POINTS IDENTIQUES ====================

  const locationCounts = {{}};

  competitions.forEach(comp => {{

    const key = comp.lat + "," + comp.lng;

    if(!locationCounts[key]) {{

      locationCounts[key] = 0;

    }} else {{

      const offset = 0.0025 * locationCounts[key];

      const angle =
        locationCounts[key] * 45 * Math.PI / 180;

      comp.lat += Math.sin(angle) * offset;
      comp.lng += Math.cos(angle) * offset;

    }}

    locationCounts[key]++;

  }});


  // ==================== CARTE ====================

  const map = L.map('map').setView([46.5, 2],6);

  L.tileLayer(
    'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
    {{
      attribution:'&copy; OpenStreetMap contributors',
      maxZoom:18
    }}
  ).addTo(map);


  // ==================== COULEURS ====================

  const typeColors = {{

    "TAE":"blue",
    "Campagne":"orange",
    "3D":"green",
    "Nature":"red",
    "Beursault":"black",
    "18m":"brown",
    "Loisir":"purple"

  }};


  const markers = [];


  // ==================== MARKERS ====================

  competitions.forEach((comp,index)=>{{

    const marker = L.circleMarker(
      [comp.lat,comp.lng],
      {{

        radius:8,

        fillColor:
          typeColors[comp.type] || "gray",

        color:"#fff",

        weight:1,

        opacity:1,

        fillOpacity:0.9

      }}
    ).addTo(map);


    // ==================== POPUP ====================

    marker.bindPopup(`

      <div style="text-align:center; font-family:Roboto,sans-serif;">

        <strong style="color:#333870;">
          ${{comp.nom}}
        </strong>

        <br>

        <span>
          ${{comp.type}} - ${{comp.dates}}
        </span>

        <br>

        <a
          href="${{comp.lien}}"
          target="_blank"
          rel="noopener noreferrer"
          class="ffta-button"
        >
          Fiche FFTA
        </a>

      </div>

    `);


    marker.competitionIndex = index;


    // ==================== SURVOL ====================

    marker.on("mouseover", () => {{

      marker.openPopup();

      const color =
        marker.options.fillColor || "gray";

      const popupEl =
        marker.getPopup().getElement();

      if(popupEl){{

        popupEl.style.border =
          `3px solid ${{color}}`;

        popupEl.style.borderRadius =
          "15px";


        const content =
          popupEl.querySelector(
            ".leaflet-popup-content"
          );

        if(content){{

          content.style.fontFamily =
            "Roboto, sans-serif";

          content.style.fontSize =
            "12px";

          content.style.fontWeight =
            "500";

          content.style.color =
            "#333870";

        }}

      }}

    }});


    // ==================== SORTIE DU POINT ====================

    marker.on("mouseout", () => {{

      marker.closePopup();

    }});


    // ==================== CLIC SUR LE POINT ====================

    marker.on("click", () => {{

      const card =
        document.querySelectorAll(
          ".competition-card"
        )[marker.competitionIndex];

      if(card) {{

        card.scrollIntoView({{
          behavior:"smooth"
        }});

      }}

    }});


    markers.push(marker);

  }});


  // ==================== GENERATION DES CARDS ====================

  const grid =
    document.querySelector(
      ".competitions-grid"
    );


  competitions.forEach(comp=>{{

    const card =
      document.createElement("div");


    card.className =
      `competition-card type-${{comp.type}}`;


    card.dataset.discipline =
      comp.type;


    card.dataset.distance =
      comp.distance;


    let displayType = comp.type;


    if(comp.type==="Beursault") {{

      displayType = "B";

    }} else if(comp.type==="Campagne") {{

      displayType = "C";

    }} else if(comp.type==="18m") {{

      displayType = "18m";

    }} else if(comp.type==="Loisir") {{

      displayType = "Loisir";

    }}


    card.innerHTML = `

      <h3 class="competition-title">
        ${{comp.nom}}
      </h3>

      <span class="type type-${{comp.type}}">
        ${{displayType}}
      </span>

      <div class="distance">
        ${{comp.distance}} km
      </div>

      <div class="dates">
        ${{comp.dates}}
      </div>

      <a
        href="${{comp.lien}}"
        target="_blank"
        rel="noopener noreferrer"
        class="ffta-button"
      >
        Voir la fiche FFTA
      </a>

    `;


    grid.appendChild(card);

  }});


  // ==================== FILTRAGE ====================

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

  const cards =
    document.querySelectorAll(
      ".competition-card"
    );


  function filterCards() {{

    const discipline =
      selectDiscipline.value;

    const maxDistance =
      parseInt(range.value);


    const bounds =
      L.latLngBounds();


    cards.forEach((card,i)=>{{

      const cardDiscipline =
        card.dataset.discipline;

      const cardDistance =
        parseInt(card.dataset.distance);


      const show =
        (
          discipline === "" ||
          discipline === cardDiscipline
        )
        &&
        cardDistance <= maxDistance;


      card.style.display =
        show ? "block" : "none";


      if(show){{

        if(!map.hasLayer(markers[i])){{

          markers[i].addTo(map);

        }}


        bounds.extend(
          markers[i].getLatLng()
        );


      }} else {{

        if(map.hasLayer(markers[i])){{

          map.removeLayer(markers[i]);

        }}

      }}

    }});


    if(bounds.isValid()){{

      map.fitBounds(
        bounds,
        {{
          padding:[50,50]
        }}
      );

    }}

  }}


  range.addEventListener(
    "input",
    ()=>{{

      value.textContent =
        range.value;

      filterCards();

    }}
  );


  selectDiscipline.addEventListener(
    "change",
    filterCards
  );


  filterCards();

}});

</script>
'''

    return html


# ==========================================
# CHARGEMENT DU JSON
# ==========================================

print("Chargement des compétitions...")

with open(
    FICHIER_ENTREE,
    "r",
    encoding="utf-8"
) as file:

    competitions = json.load(file)


print(
    f"{len(competitions)} compétitions chargées."
)


# ==========================================
# GÉOCODAGE DU CODE POSTAL DE RÉFÉRENCE
# ==========================================

print()

print(
    f"Recherche du code postal de référence : "
    f"{CODE_POSTAL_REFERENCE}"
)

reference = geocoder_code_postal(
    CODE_POSTAL_REFERENCE
)

if not reference:

    print(
        "❌ Impossible de géolocaliser le code postal "
        "de référence."
    )

    exit()


print(
    f"✅ {reference['nom']} "
    f"({reference['latitude']}, "
    f"{reference['longitude']})"
)


# ==========================================
# DATE DU JOUR
# ==========================================

date_aujourd_hui = date.today().isoformat()


# ==========================================
# TRADUCTION
# ==========================================

competitions_traduites = []

stats = {
    "total": 0,
    "discipline": 0,
    "date": 0,
    "comites": 0,
    "geolocalisation": 0,
    "conservees": 0
}


for competition in competitions:

    stats["total"] += 1

    competition_id = competition.get("id")

    print()

    print(
        f"Traitement de la compétition "
        f"{competition_id}..."
    )


    # ==========================================
    # FILTRE DISCIPLINE
    # ==========================================

    discipline = normaliser_texte(
        competition.get("discipline")
    )

    if discipline not in DISCIPLINES_AUTORISEES:

        print(
            f"  ❌ Discipline ignorée : {discipline}"
        )

        continue

    stats["discipline"] += 1


    # ==========================================
    # FILTRE DATE
    # ==========================================

    date_fin = competition.get("date_fin")

    if not date_fin:

        print(
            "  ❌ Date de fin absente"
        )

        continue

    if date_fin < date_aujourd_hui:

        print(
            f"  ❌ Compétition terminée : {date_fin}"
        )

        continue

    stats["date"] += 1


    # ==========================================
    # FILTRE COMITÉS + CODE POSTAL
    # ==========================================

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
        and not comite_departemental
        and not code_postal
    ):

        print(
            "  ❌ Comité régional, comité départemental "
            "et code postal absents"
        )

        continue


    stats["comites"] += 1


    # ==========================================
    # GÉOLOCALISATION
    # ==========================================

    localisation = None


    # ------------------------------------------
    # Cas 1 : code postal disponible
    # ------------------------------------------

    if code_postal:

        print(
            f"  📍 Recherche du code postal "
            f"{code_postal}..."
        )

        localisation = geocoder_code_postal(
            code_postal
        )


    # ------------------------------------------
    # Cas 2 : pas de code postal
    # → recherche par ville
    # ------------------------------------------

    else:

        lieu = competition.get("lieu")

        print(
            f"  📍 Code postal absent, "
            f"recherche de la ville : {lieu}"
        )

        localisation = geocoder_ville(
            lieu
        )

        if localisation:

            code_postal = localisation.get(
                "code_postal"
            )

            print(
                f"  ✅ Code postal trouvé : "
                f"{code_postal}"
            )


    # ------------------------------------------
    # Impossible de géolocaliser
    # ------------------------------------------

    if not localisation:

        print(
            "  ⚠️ Impossible de géolocaliser "
            "la compétition"
        )

        continue


    stats["geolocalisation"] += 1


    # ==========================================
    # DISTANCE
    # ==========================================

    distance = distance_km(
        reference["latitude"],
        reference["longitude"],
        localisation["latitude"],
        localisation["longitude"]
    )

    distance = round(distance, 1)


    # ==========================================
    # LIEN FFTA
    # ==========================================

    lien = (
        f"https://www.ffta.fr/epreuve/{competition_id}"
    )


    # ==========================================
    # NOUVELLE COMPÉTITION
    # ==========================================

    competition_traduite = competition.copy()


    # Code postal
    competition_traduite["code_postal"] = (
        code_postal
    )


    # Distance
    competition_traduite["distance_km"] = (
        distance
    )


    # Coordonnées GPS
    competition_traduite["latitude"] = (
        localisation["latitude"]
    )

    competition_traduite["longitude"] = (
        localisation["longitude"]
    )


    # Lien FFTA
    competition_traduite["lien"] = lien


    competitions_traduites.append(
        competition_traduite
    )

    stats["conservees"] += 1


    print(
        f"  ✅ Conservée - {distance} km "
        f"({localisation['latitude']}, "
        f"{localisation['longitude']})"
    )


# ==========================================
# SAUVEGARDE DU JSON
# ==========================================

with open(
    FICHIER_SORTIE_JSON,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        competitions_traduites,
        file,
        ensure_ascii=False,
        indent=4
    )


# ==========================================
# GÉNÉRATION DU HTML YAPLA
# ==========================================

print()

print(
    "Génération du bloc Yapla..."
)

html_yapla = generer_html_yapla(
    competitions_traduites
)


with open(
    FICHIER_SORTIE_HTML,
    "w",
    encoding="utf-8"
) as file:

    file.write(html_yapla)


print(
    f"✅ Bloc Yapla généré dans "
    f"{FICHIER_SORTIE_HTML}"
)


# ==========================================
# RÉSUMÉ
# ==========================================

print()

print(
    "=========================================="
)

print(
    "TRADUCTION TERMINÉE"
)

print(
    "=========================================="
)

print(
    f"Compétitions initiales : "
    f"{stats['total']}"
)

print(
    f"Après filtre discipline : "
    f"{stats['discipline']}"
)

print(
    f"Après filtre date : "
    f"{stats['date']}"
)

print(
    f"Après filtre comités : "
    f"{stats['comites']}"
)

print(
    f"Après géolocalisation : "
    f"{stats['geolocalisation']}"
)

print(
    f"Compétitions conservées : "
    f"{stats['conservees']}"
)

print()

print(
    f"JSON créé dans "
    f"{FICHIER_SORTIE_JSON}"
)

print(
    f"HTML Yapla créé dans "
    f"{FICHIER_SORTIE_HTML}"
)