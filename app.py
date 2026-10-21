import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path
import json

st.set_page_config(page_title="Mi Futuro Jujuy", page_icon="🎓", layout="wide")
st.markdown("""<style>div.st-key-intereses_nuevo button[kind=\"primaryFormSubmit\"] {background:#7138c8;color:white;border:0;font-weight:700;} div.st-key-intereses_nuevo button[kind=\"primaryFormSubmit\"]:hover {background:#5925a7;color:white;}</style>""", unsafe_allow_html=True)
st.title("🎓 Mi Futuro Jujuy")
st.write("Explorá tus intereses y descubrí dónde estudiar en Jujuy.")
st.info("🎓 **¡Tu futuro comienza acá!** Explorá carreras, instituciones y localidades de Jujuy y descubrí opciones relacionadas con tus intereses.")
FILE = Path(__file__).with_name("carreras.xlsx")
if not FILE.exists():
    st.error("Falta cargar el archivo carreras.xlsx en el repositorio. Descargá la base preliminar y subila con Add file > Upload files.")
    st.stop()
@st.cache_data
def load_data():
    return pd.read_excel(FILE, sheet_name="Carreras").fillna("")
df = load_data()
# El archivo histórico no acredita inscripciones abiertas. Excluir entradas con cierre explícito.
df = df[~df.astype(str).apply(lambda col: col.str.contains("inscripciones no habilitadas|inscripciones cerradas|no admite ingresantes", case=False, regex=True)).any(axis=1)].copy()
# Fuente: Facultad de Ingeniería UNJu. En Libertador se cursa solo primer año.
engineering_note = ("SOLO PRIMER AÑO en Libertador. Extensión Áulica FI-UNJu, "
                    "Escuela Técnica Ing. Herminio Arrieta, Mariano Moreno 1368. "
                    "Consultá en la UNJu dónde continuar los años siguientes.")
new_rows = []
for name in ["Ingeniería de Minas", "Ingeniería Química",
             "Ingeniería Informática", "Ingeniería Industrial"]:
    exists = ((df["Carrera / título"].astype(str).str.casefold() == name.casefold()) &
              (df["Localidad"].astype(str).str.casefold() == "libertador general san martín")).any()
    if not exists:
        new_rows.append({
            "Institución": "UNJu – Facultad de Ingeniería (Extensión Áulica)",
            "Localidad": "Libertador General San Martín",
            "Carrera / título": name,
            "Tipo de formación": "Ingeniería (solo primer año en esta sede)",
            "Área principal preliminar": "Tecnología e informática" if "Informática" in name else "Ambiente y producción",
            "Observación": engineering_note
        })
# Nuevas carreras de la Facultad de Ingeniería en San Salvador de Jujuy.
# La duración de dos años no implica ingreso directo desde la secundaria.
for name, kind, url in [
    ("Profesorado Universitario en Informática", "Profesorado universitario",
     "https://fi.unju.edu.ar/carreras/perfil-alcance/puinf.html"),
    ("Licenciatura en Informática Educativa", "Licenciatura universitaria",
     "https://fi.unju.edu.ar/carreras/perfil-alcance/lie.html")
]:
    exists = ((df["Carrera / título"].astype(str).str.casefold() == name.casefold()) &
              (df["Localidad"].astype(str).str.casefold() == "san salvador de jujuy")).any()
    if not exists:
        new_rows.append({
            "Institución": "UNJu – Facultad de Ingeniería",
            "Localidad": "San Salvador de Jujuy",
            "Carrera / título": name,
            "Tipo de formación": kind,
            "Área principal preliminar": "Tecnología e informática",
            "Observación": ("Duración publicada: 2 años (4 cuatrimestres). "
                            "Consultar requisitos de ingreso y título previo con la Facultad. "
                            "Fuente oficial: " + url)
        })
# Oferta FI-UNJu: sede central y extensiones áulicas, según página oficial.
# La oferta publicada no garantiza apertura de inscripciones en cada ciclo.
fi_url = "https://fi.unju.edu.ar/secretarias/sacad/oferta-academica.html"
fi_offerings = [
    ("Ingeniería Química", "Ingeniería", "5 años"),
    ("Ingeniería de Minas", "Ingeniería", "5 años"),
    ("Ingeniería Industrial", "Ingeniería", "5 años"),
    ("Ingeniería Informática", "Ingeniería", "5 años"),
    ("Licenciatura en Sistemas", "Licenciatura", "5 años"),
    ("Licenciatura en Ciencias Geológicas", "Licenciatura", "5 años"),
    ("Licenciatura en Tecnología de los Alimentos", "Licenciatura", "4 años"),
    ("Profesorado Universitario en Informática", "Profesorado universitario", "4 cuatrimestres"),
    ("Licenciatura en Informática Educativa", "Licenciatura", "4 cuatrimestres"),
    ("Analista Programador Universitario", "Pregrado universitario", "3 años"),
    ("Tecnicatura Universitaria en Perforaciones", "Tecnicatura universitaria", "3 años"),
    ("Tecnicatura Universitaria en Diseño Integral de Videojuegos", "Tecnicatura universitaria", "3 años")
]
for name, kind, duration in fi_offerings:
    exists = ((df["Carrera / título"].astype(str).str.casefold() == name.casefold()) &
              (df["Localidad"].astype(str).str.casefold() == "san salvador de jujuy") &
              (df["Institución"].astype(str).str.casefold().str.contains("unju|universidad nacional de jujuy|facultad de ingenier", regex=True))).any()
    if not exists:
        new_rows.append({
            "Institución": "UNJu – Facultad de Ingeniería",
            "Localidad": "San Salvador de Jujuy",
            "Carrera / título": name,
            "Tipo de formación": kind,
            "Área principal preliminar": ("Tecnología e informática" if any(k in name.casefold() for k in
                ["informát", "sistemas", "programador", "videojuegos"]) else "Ambiente y producción"),
            "Observación": ("Sede central: Ítalo Palanca 10. Duración publicada: " + duration +
                            ". Consultar requisitos de ingreso y oferta vigente. Fuente: " + fi_url)
        })
for locality in ["San Pedro", "La Quiaca"]:
    name = "Analista Programador Universitario"
    exists = ((df["Carrera / título"].astype(str).str.casefold() == name.casefold()) &
              (df["Localidad"].astype(str).str.casefold() == locality.casefold())).any()
    if not exists:
        new_rows.append({
            "Institución": "UNJu – Facultad de Ingeniería (Extensión Áulica)",
            "Localidad": locality,
            "Carrera / título": name,
            "Tipo de formación": "Pregrado universitario",
            "Área principal preliminar": "Tecnología e informática",
            "Observación": "Extensión áulica FI-UNJu. Duración publicada: 3 años. Confirmar oferta vigente. Fuente: " + fi_url
        })
# Facultad de Ciencias Agrarias (FCA-UNJu): oferta publicada.
# Una sede/cohorte publicada NO implica inscripción abierta en el año actual.
fca_grad = "https://fca.unju.edu.ar/oferta-academica/grado/"
fca_pre = "https://fca.unju.edu.ar/oferta-academica/pregrado/"
fca_offerings = [
    ("Ingeniería Agronómica", "San Salvador de Jujuy", "Ingeniería", "Ambiente y producción", "Carrera de grado de 5 años. Sede central.", fca_grad),
    ("Ingeniería Agronómica", "San Pedro", "Ingeniería (hasta tercer año en esta sede)", "Ambiente y producción", "Solo hasta 3.º año en San Pedro. Consultar dónde continuar y condiciones de cursado.", fca_grad),
    ("Licenciatura en Ciencias Biológicas", "San Salvador de Jujuy", "Licenciatura", "Ambiente y producción", "Duración: 5 años.", fca_grad),
    ("Licenciatura en Bromatología", "San Salvador de Jujuy", "Licenciatura", "Salud y bienestar", "Duración: 4 años y medio; título intermedio de Bromatólogo/a a los 3 años.", fca_grad),
    ("Licenciatura en Desarrollo Rural", "Abra Pampa", "Licenciatura", "Ambiente y producción", "Cohorte 2024, modalidad especial. Confirmar si admite nuevos ingresantes.", fca_grad),
    ("Licenciatura en Gestión Ambiental", "Humahuaca", "Licenciatura", "Ambiente y producción", "Duración: 5 años. Confirmar oferta vigente.", fca_grad),
    ("Tecnicatura Universitaria en Producción de Animales de Granja", "Monterrico", "Tecnicatura universitaria", "Ambiente y producción", "Duración: 2 años y medio.", fca_pre),
    ("Tecnicatura Universitaria en Mecanización Agrícola", "Perico", "Tecnicatura universitaria", "Ambiente y producción", "Duración: 2 años y medio.", fca_pre),
    ("Tecnicatura Universitaria en Transformación de la Producción Agropecuaria", "Tilcara", "Tecnicatura universitaria", "Ambiente y producción", "Cohorte 2026, modalidad especial. Duración: 2 años y medio; consultar ingreso vigente.", fca_pre),
    ("Tecnicatura Universitaria en Transformación de la Producción Agropecuaria", "Abra Pampa", "Tecnicatura universitaria", "Ambiente y producción", "Cohorte 2026, modalidad especial. Duración: 2 años y medio; consultar ingreso vigente.", fca_pre),
    ("Tecnicatura Universitaria Forestal", "San Pedro", "Tecnicatura universitaria", "Ambiente y producción", "Duración: 2 años y medio.", fca_pre)
]
for name, locality, kind, area, note, source in fca_offerings:
    # Cohortes especiales previas no equivalen a una convocatoria abierta.
    if "Cohorte 2024" in note or "Cohorte 2026" in note:
        continue
    exists = ((df["Carrera / título"].astype(str).str.casefold() == name.casefold()) &
              (df["Localidad"].astype(str).str.casefold() == locality.casefold()) &
              (df["Institución"].astype(str).str.casefold().str.contains("agrarias|fca", regex=True))).any()
    if not exists:
        new_rows.append({
            "Institución": "UNJu – Facultad de Ciencias Agrarias",
            "Localidad": locality, "Carrera / título": name,
            "Tipo de formación": kind, "Área principal preliminar": area,
            "Observación": note + " Fuente: " + source
        })
# Producción Lechera: no se asigna una localidad sin sede confirmada;
# además, la Facultad indica que no tiene inscripciones habilitadas.
# FCE-UNJu: anuncio de ingreso 2027 aportado por la usuaria.
# No inventar plazos ni estado de inscripción. Sede informada: San Salvador de Jujuy.
fce_ingreso_url = "https://www.fce.unju.edu.ar/ingresofceunju"
fce_2027 = ["Contador Público", "Licenciatura en Administración",
            "Licenciatura en Economía Política"]
# FHyCS-UNJu: oferta mostrada en la página oficial de ingreso.
# Ingreso 2027 habilitado según confirmación de la usuaria; fechas individuales por consultar.
fhycs_url = "https://fhycs.unju.edu.ar/ingreso/index.html"
fhycs_offerings = [
    ("Licenciatura en Antropología", ["San Salvador de Jujuy"], "5 años"),
    ("Licenciatura en Ciencias de la Educación", ["San Salvador de Jujuy", "San Pedro"], "5 años"),
    ("Tecnicatura en Turismo", ["Humahuaca", "El Carmen"], "Carrera articulada con Licenciatura en Turismo; duración total indicada: 4 años"),
    ("Licenciatura en Turismo", ["Humahuaca", "El Carmen"], "Duración publicada para la propuesta Turismo: 4 años"),
    ("Licenciatura en Educación para la Salud", ["San Salvador de Jujuy", "San Pedro"], "5 años y medio"),
    ("Licenciatura en Historia", ["San Salvador de Jujuy"], "5 años"),
    ("Profesorado en Filosofía", ["San Salvador de Jujuy"], "4 años; oferta conjunta con Licenciatura en Filosofía"),
    ("Licenciatura en Filosofía", ["San Salvador de Jujuy"], "4 años; oferta conjunta con Profesorado en Filosofía"),
    ("Profesorado en Letras", ["San Salvador de Jujuy"], "5 años"),
    ("Profesorado en Educación para la Salud", ["San Salvador de Jujuy"], "4 años"),
    ("Licenciatura en Trabajo Social", ["San Salvador de Jujuy", "Tilcara"], "5 años"),
    ("Profesorado en Historia", ["San Salvador de Jujuy"], "5 años"),
    ("Tecnicatura Universitaria en Gestión y Producción Editorial", ["San Salvador de Jujuy"], "3 años"),
    ("Licenciatura en Letras", ["San Salvador de Jujuy"], "5 años"),
    ("Licenciatura en Comunicación Social", ["San Salvador de Jujuy"], "4 años"),
    ("Tecnicatura en Comunicación Digital Convergente", ["San Salvador de Jujuy"], "3 años")
]
# Evitar duplicar filas que ya figuran en el Excel. Se mantiene el estado no confirmado.
for name, localities, duration in fhycs_offerings:
    for locality in localities:
        exists = ((df["Carrera / título"].astype(str).str.strip().str.casefold() == name.casefold()) &
                  (df["Localidad"].astype(str).str.strip().str.casefold() == locality.casefold())).any()
        pending = any(row["Carrera / título"].casefold() == name.casefold()
                      and row["Localidad"].casefold() == locality.casefold() for row in new_rows)
        if not exists and not pending:
            new_rows.append({
                "Institución": "UNJu – Facultad de Humanidades y Ciencias Sociales",
                "Localidad": locality, "Carrera / título": name,
                "Tipo de formación": "Profesorado" if name.startswith("Profesorado") else ("Tecnicatura" if name.startswith("Tecnicatura") else "Licenciatura"),
                "Área principal preliminar": "Educación y humanidades" if any(x in name for x in ("Educación", "Historia", "Filosofía", "Letras", "Antropología", "Editorial")) else "Ciencias sociales y comunicación",
                "Observación": duration + ". Ingreso 2027 habilitado según información aportada por la usuaria. Fuente: " + fhycs_url
            })
# Convocatorias de ingreso 2027 comunicadas por el usuario.
# Localidad de cursado indicada por la usuaria: San Salvador de Jujuy.
admission_2027 = [
    {
        "Carrera": "Abogacía",
        "Localidad": "San Salvador de Jujuy",
        "Preinscripción": "1 al 25 de octubre de 2026",
        "Curso": "Virtual por UNJu Virtual. Módulo I: Lectura y comprensión de textos en la práctica del derecho (2–6 nov); Módulo II: Introducción a las Ciencias Sociales (9–13 nov); Módulo III: Nociones básicas de derecho (16–20 nov).",
        "Examen": "23 al 26 de febrero de 2027",
        "Resultados": "Módulos: 27 de noviembre de 2026. Resultados definitivos y orden de mérito: 2 de marzo de 2027."
    },
    {
        "Carrera": "Enfermería Universitaria",
        "Localidad": "San Salvador de Jujuy",
        "Preinscripción": "1 al 25 de octubre de 2026",
        "Curso": "Módulo I: Lectura y comprensión de textos (2–6 nov); Módulo II: Química y Física (9–13 nov); Módulo III: Introducción a la Enfermería (16–20 nov); Módulo IV: Morfofisiología (23–27 nov).",
        "Examen": "18, 19 y 22 de febrero de 2027",
        "Resultados": "Lista habilitada para rendir: 23 de diciembre de 2026. Resultados definitivos y orden de mérito: 24 de febrero de 2027.",
        "Cupo": "140 estudiantes. Inicio de cursado: marzo de 2027."
    }
]
# Escuela Superior de Ciencias Jurídicas y Políticas, UNJu.
juridicas = [
    ("Abogacía", "Abogado/a", "5 años", "https://escuelajuridica.unju.edu.ar/abogacia/"),
    ("Licenciatura en Ciencia Política", "Licenciado/a en Ciencia Política", "4 años", "https://escuelajuridica.unju.edu.ar/licenciatura-en-ciencia-politica/")
]
for name, title, duration, url in juridicas:
    locality = "San Salvador de Jujuy"
    note = ("Título: " + title + ". Duración: " + duration +
            ". Escuela Superior de Ciencias Jurídicas y Políticas, UNJu. "
            "Rectorado UNJu, Av. Bolivia 1239, San Salvador de Jujuy. "
            "Fuente: " + url)
    if name == "Abogacía":
        note += " Ingreso 2027: preinscripción 1 al 25 de octubre de 2026; examen 23 al 26 de febrero de 2027."
    exists = ((df["Carrera / título"].astype(str).str.strip().str.casefold() == name.casefold()) &
              (df["Localidad"].astype(str).str.strip().str.casefold() == locality.casefold())).any()
    pending = any(row["Carrera / título"].casefold() == name.casefold()
                  and row["Localidad"].casefold() == locality.casefold() for row in new_rows)
    if not exists and not pending:
        new_rows.append({
            "Institución": "Universidad Nacional de Jujuy (UNJu)",
            "Facultad": "Escuela Superior de Ciencias Jurídicas y Políticas",
            "Lugar donde se dicta": "Rectorado UNJu - Av. Bolivia 1239",
            "Localidad": locality,
            "Carrera / título": name,
            "Tipo de formación": "Licenciatura" if name.startswith("Licenciatura") else "Carrera universitaria de grado",
            "Área principal preliminar": "Ciencias sociales y comunicación",
            "Observación": note
        })
if new_rows:
    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
# Completar la unidad académica y dirección también para carreras preexistentes.
for name, title, duration, url in juridicas:
    match = ((df["Carrera / título"].astype(str).str.strip().str.casefold() == name.casefold()) &
             (df["Localidad"].astype(str).str.strip().str.casefold() == "san salvador de jujuy"))
    if match.any():
        df.loc[match, "Institución"] = "Universidad Nacional de Jujuy (UNJu)"
        df.loc[match, "Facultad"] = "Escuela Superior de Ciencias Jurídicas y Políticas"
        df.loc[match, "Lugar donde se dicta"] = "Rectorado UNJu - Av. Bolivia 1239"
        df.loc[match, "Observación"] = ("Título: " + title + ". Duración: " + duration +
            ". Rectorado UNJu, Av. Bolivia 1239. Fuente: " + url +
            (" Ingreso 2027: preinscripción del 1 al 25 de octubre de 2026." if name == "Abogacía" else ""))
# Unificamos la escritura de localidades, incluso si el Excel trae mayúsculas.
df["Localidad"] = df["Localidad"].astype(str).str.strip()
df["Localidad"] = df["Localidad"].replace({
    "LIBERTADOR GRAL SAN MARTÍN": "Libertador General San Martín",
    "LIBERTADOR GRAL. SAN MARTÍN": "Libertador General San Martín",
    "LIBERTADOR GENERAL SAN MARTÍN": "Libertador General San Martín",
    "Libertador Gral. San Martín": "Libertador General San Martín"
})
# Unificar el registro general del primer año de Ingeniería en Libertador.
# Las cuatro ingenierías ya figuran por separado con su título específico.
umbrella = df["Carrera / título"].astype(str).str.contains(
    "Cursado de Primer Año de las carreras de Ingeniería de Minas, Química, Informática e Industrial",
    case=False, regex=False
)
df = df.loc[~umbrella].copy()
# Evitar repeticiones de la misma carrera, institución y localidad.
df["_clave_carrera"] = df["Carrera / título"].astype(str).str.strip().str.casefold()
df["_clave_localidad"] = df["Localidad"].astype(str).str.strip().str.casefold()
df["_clave_institucion"] = df["Institución"].astype(str).str.casefold().str.replace(
    r"\\s*\\(extensión áulica\\)", "", regex=True
).str.strip()
df = df.drop_duplicates(subset=["_clave_carrera", "_clave_localidad", "_clave_institucion"])
df = df.drop(columns=["_clave_carrera", "_clave_localidad", "_clave_institucion"])
town = "Localidad"
career = "Carrera / título"
towns = sorted(df[town].astype(str).unique())
coords = {
    "Abra Pampa":(-22.72,-65.70), "El Carmen":(-24.39,-65.26),
    "Fraile Pintado":(-23.94,-64.80), "Humahuaca":(-23.21,-65.35),
    "La Mendieta":(-24.31,-64.97), "La Quiaca":(-22.10,-65.60),
    "Libertador General San Martín":(-23.81,-64.79), "Monterrico":(-24.44,-65.16),
    "Palmasola":(-24.00,-64.30), "Palpalá":(-24.26,-65.21),
    "Perico":(-24.38,-65.12), "San Pedro":(-24.23,-64.87),
    "San Salvador de Jujuy":(-24.19,-65.30), "Susques":(-23.40,-66.36),
    "Tilcara":(-23.58,-65.40), "Tumbaya":(-23.85,-65.47),
    "Yuto":(-23.64,-64.47)
}
def results(frame):
    if frame.empty:
        st.info("No hay coincidencias en esta base preliminar.")
    else:
        st.caption(f"{len(frame)} registros históricos")
        display_cols = ["Institución", town, career, "Tipo de formación", "Área principal preliminar"]
        if "Observación" in frame.columns:
            display_cols.append("Observación")
        st.dataframe(frame[display_cols], hide_index=True, use_container_width=True)
import re
import unicodedata

def normalize(value):
    value = unicodedata.normalize("NFKD", str(value).casefold())
    return "".join(char for char in value if not unicodedata.combining(char))

# Sedes de cursado del IES N.º 10 informadas por la docente.
# No mostrar datos de sede cuando no están confirmados.
def sede_ies10(row):
    institucion = normalize(row.get("Institución", ""))
    if not ("ies 10" in institucion or "instituto de educacion superior n° 10" in institucion or
            "instituto de educacion superior n.º 10" in institucion or
            "instituto de educacion superior n°10" in institucion or
            "instituto de educacion superior nº 10" in institucion):
        return ""
    localidad = normalize(row.get("Localidad", ""))
    titulo = normalize(row.get("Carrera / título", ""))
    if localidad == "fraile pintado":
        return "Escuela N.º 123 Manuel Belgrano"
    if localidad == "yuto":
        return "Fundación Te Ayudamos Hermanos"
    if localidad == "libertador general san martin":
        if ("matematica" in titulo and "profesor" in titulo) or ("administracion" in titulo and "profesor" in titulo):
            return "Escuela Comercial N.º 4 25 de Febrero"
        if any(p in titulo for p in ("quimica", "ingles", "educacion primaria", "educacion especial", "ciencias de la educacion")):
            return "Escuela Normal"
    return ""

df["Sede de cursado confirmada"] = df.apply(sede_ies10, axis=1)

topics = {
    "programación y tecnología": ["program", "software", "inform", "comput", "datos", "sistema", "robot", "tecnolog"],
    "salud": ["salud", "enferm", "medic", "nutric", "kinesi", "laboratorio", "terapia"],
    "educación y docencia": ["profesor", "docen", "educa", "enseñ", "pedagog", "maestr"],
    "arte y comunicación": ["arte", "dise", "comunic", "musica", "teatro", "danza", "visual"],
    "ambiente y producción": ["ambient", "agro", "agrar", "produccion", "natural", "ecolog"],
    "administración y economía": ["administr", "contab", "econom", "gestion", "empresa", "comerc"],
    "turismo": ["turis", "hotel", "gastron"],
    "historia y sociedad": ["historia", "social", "filosof", "derecho", "politic", "sociolog"]
}
ignore = {"donde", "puedo", "estudiar", "carreras", "carrera", "quiero", "tienen", "tiene", "oferta", "ofrecen", "sobre", "relacionadas", "relacionado", "interesa", "gustaria", "saber", "para", "como", "cuales", "jujuy", "instituto", "universidad", "tecnicatura", "profesorado", "estudios", "formacion", "localidad", "hola", "buenas"}

dept_towns = {
    "COCHINOCA": ["Abra Pampa"],
    "EL CARMEN": ["El Carmen", "Monterrico", "Perico"],
    "DOCTOR MANUEL BELGRANO": ["San Salvador de Jujuy"],
    "HUMAHUACA": ["Humahuaca"],
    "LEDESMA": ["Libertador General San Martín", "Fraile Pintado", "Yuto"],
    "PALPALA": ["Palpalá"],
    "RINCONADA": [],
    "SAN ANTONIO": [],
    "SAN PEDRO": ["San Pedro", "La Mendieta"],
    "SANTA BARBARA": ["Palmasola"],
    "SANTA CATALINA": [],
    "SUSQUES": ["Susques"],
    "TILCARA": ["Tilcara"],
    "TUMBAYA": ["Tumbaya"],
    "VALLE GRANDE": [],
    "YAVI": ["La Quiaca"],
}

def career_kind(row):
    title = normalize(row["Carrera / título"])
    formation = normalize(row["Tipo de formación"])
    if "profesor" in title or "profesor" in formation:
        return "Profesorados"
    if "ingenier" in title:
        return "Ingenierías"
    if "tecnic" in title or "tecnic" in formation:
        return "Tecnicaturas"
    if "licenciat" in title or "licenciat" in formation:
        return "Licenciaturas"
    return "Otras formaciones"

def match_localities(message):
    q = normalize(message)
    # Variantes frecuentes en el habla y la escritura local.
    q = re.sub(r"\\bgral\\.?\\b", "general", q)
    aliases = {
        "libertador": "Libertador General San Martín",
        "libertador gral san martin": "Libertador General San Martín",
        "libertador general san martin": "Libertador General San Martín",
        "ledesma ciudad": "Libertador General San Martín",
        "san salvador": "San Salvador de Jujuy",
        "capital de jujuy": "San Salvador de Jujuy",
    }
    matched = []
    for alias, canonical in aliases.items():
        if alias in q and canonical in towns and canonical not in matched:
            matched.append(canonical)
    for loc in towns:
        if normalize(loc) in q and loc not in matched:
            matched.append(loc)
    return matched

def find_careers(message):
    q = normalize(message)
    selected_localities = match_localities(message)
    subset = df[df[town].isin(selected_localities)] if selected_localities else df
    detected = []
    for keywords in topics.values():
        if any(word in q for word in keywords):
            detected.extend(keywords)
    words = [word for word in re.findall(r"[a-z]+", q)
             if len(word) >= 4 and word not in ignore]
    if selected_localities:
        # Si el usuario solo nombra una localidad, mostrar toda su oferta.
        for loc in selected_localities:
            words = [word for word in words if word not in normalize(loc).split()]
        words = [word for word in words if word not in {
            "libertador", "gral", "general", "martin", "ledesma", "ciudad", "capital"}]
    searchable = (subset[career].astype(str).map(normalize) + " " +
                  subset["Área principal preliminar"].astype(str).map(normalize))
    if detected:
        found = subset[searchable.map(lambda value: any(word in value for word in detected))]
    elif words:
        found = subset[searchable.map(lambda value: any(word in value for word in words))]
    else:
        found = subset
    return found.drop_duplicates(subset=[career, town, "Institución"]), selected_localities


st.markdown("""<style>
[data-testid="stSidebar"] {display:none;}
.st-key-cifac_launcher {
    position:fixed; bottom:88px; right:26px; z-index:999999;
    width:auto!important;
}
/* CIFAC asoma por encima del botón de ayuda */
.st-key-cifac_launcher::before {
    content:"";
    position:absolute;
    width:88px;
    height:88px;
    right:38px;
    bottom:calc(100% - 5px);
    background-image:url('data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20160%20160%22%3E%3Cdefs%3E%3ClinearGradient%20id%3D%22g%22%20x2%3D%221%22%20y2%3D%221%22%3E%3Cstop%20stop-color%3D%22%237541d6%22%2F%3E%3Cstop%20offset%3D%221%22%20stop-color%3D%22%2326c6da%22%2F%3E%3C%2FlinearGradient%3E%3C%2Fdefs%3E%3Ccircle%20cx%3D%2280%22%20cy%3D%2280%22%20r%3D%2276%22%20fill%3D%22%23efe8ff%22%2F%3E%3Cpath%20d%3D%22M80%2025V16%22%20stroke%3D%22%23673ab7%22%20stroke-width%3D%226%22%20stroke-linecap%3D%22round%22%2F%3E%3Ccircle%20cx%3D%2280%22%20cy%3D%2213%22%20r%3D%228%22%20fill%3D%22%237c4ddb%22%2F%3E%3Crect%20x%3D%2220%22%20y%3D%2237%22%20width%3D%22120%22%20height%3D%2294%22%20rx%3D%2232%22%20fill%3D%22url(%23g)%22%2F%3E%3Crect%20x%3D%2229%22%20y%3D%2245%22%20width%3D%22102%22%20height%3D%2278%22%20rx%3D%2225%22%20fill%3D%22%23151d3d%22%2F%3E%3Cpath%20d%3D%22M47%2079q12-19%2024%200M89%2079q12-19%2024%200%22%20fill%3D%22none%22%20stroke%3D%22%2364edff%22%20stroke-width%3D%227%22%20stroke-linecap%3D%22round%22%2F%3E%3Cpath%20d%3D%22M68%2096q12%2012%2024%200%22%20fill%3D%22none%22%20stroke%3D%22%2364edff%22%20stroke-width%3D%226%22%20stroke-linecap%3D%22round%22%2F%3E%3Ccircle%20cx%3D%2226%22%20cy%3D%2287%22%20r%3D%2211%22%20fill%3D%22%237047cf%22%2F%3E%3Ccircle%20cx%3D%22134%22%20cy%3D%2287%22%20r%3D%2211%22%20fill%3D%22%237047cf%22%2F%3E%3Cpath%20d%3D%22M48%20128q32%2021%2064%200%22%20fill%3D%22none%22%20stroke%3D%22%237541d6%22%20stroke-width%3D%228%22%20stroke-linecap%3D%22round%22%2F%3E%3C%2Fsvg%3E');
    background-size:contain;
    background-position:center bottom;
    background-repeat:no-repeat;
    pointer-events:none;
    filter:drop-shadow(0 5px 7px #34265a55);
}
.st-key-cifac_launcher button[data-testid="stPopoverButton"] {
    background:linear-gradient(120deg,#6631b9,#8751d7)!important;
    color:white!important;border-radius:32px!important;
    border:2px solid white!important;box-shadow:0 7px 26px #38216455!important;
    font-weight:750!important;font-size:16px!important;padding:15px 25px!important;
}
[data-testid="stPopoverBody"] {
    width:min(560px,calc(100vw - 32px))!important;
    max-width:calc(100vw - 32px)!important;
    max-height:min(75vh,740px)!important;
}
@media(max-width:600px){
    .st-key-cifac_launcher{bottom:85px;right:14px;}
    .st-key-cifac_launcher::before{width:70px;height:70px;right:28px;}
    .st-key-cifac_launcher button[data-testid="stPopoverButton"]{padding:12px 16px!important;font-size:14px!important;}
    [data-testid="stPopoverBody"]{max-height:72vh!important;}
}
</style>""", unsafe_allow_html=True)
with st.container(key="cifac_launcher"):
    with st.popover("🤖 CIFAC · ¿Necesitás ayuda?", use_container_width=False):
        cifac_avatar = str(Path(__file__).with_name("cifac.svg"))
        avatar_col, name_col = st.columns([1, 4], vertical_alignment="center")
        with avatar_col:
            st.image(cifac_avatar, width=65)
        with name_col:
            st.subheader("CIFAC")
        st.caption("Tu guía para explorar carreras y localidades de Jujuy.")
        if "assistant_history" not in st.session_state:
            st.session_state.assistant_history = []
        with st.chat_message("assistant", avatar=cifac_avatar):
            st.markdown("👋 **¡Hola! Soy CIFAC, tu asistente de Mi Futuro Jujuy.**\n\nTe ayudo a buscar qué carreras figuran en nuestra base y dónde podrías estudiarlas. Podés preguntarme por una localidad, una carrera o un tema que te interese.\n\n**¿Qué te gustaría conocer?**")
        for item in st.session_state.assistant_history:
            with st.chat_message(item["role"]):
                st.markdown(item["content"])
        if "cifac_step" not in st.session_state:
            st.session_state.cifac_step = "inicio"
        step = st.session_state.cifac_step
        if step == "inicio" and not st.session_state.assistant_history:
            st.caption("Elegí una opción para empezar:")
            suggestions = ["No sé qué estudiar, ¿me ayudás?", "Quiero buscar carreras por localidad", "Me interesa la tecnología, ¿qué opciones tengo?"]
        elif step == "orientacion":
            st.caption("¿Cómo querés continuar?")
            suggestions = ["Quiero descubrir mis intereses", "Prefiero contarte qué actividades me gustan"]
        elif step == "localidad":
            st.caption("¿En qué localidad querés estudiar?")
            suggestions = []
            chosen = st.selectbox("Localidad", ["Elegí una localidad"] + towns, key="cifac_town_select")
            if st.button("Continuar con esta localidad", key="cifac_town_go", disabled=chosen == "Elegí una localidad", use_container_width=True):
                suggestions = [chosen]
            st.caption("O escribí el nombre de otra localidad abajo.")
        elif step == "tipo":
            loc = st.session_state.get("cifac_locality", "")
            available = df[df[town] == loc].apply(career_kind, axis=1).unique().tolist()
            st.caption("¿Qué tipo de formación querés explorar?")
            suggestions = ["Ver todas las carreras"] + sorted(available)
        elif step == "actividades":
            st.caption("Contame qué actividades te gustan en el cuadro de abajo.")
            suggestions = []
        else:
            st.caption("Podés seguir preguntando o iniciar otra búsqueda:")
            suggestions = ["Buscar carreras por localidad", "Explorar mis intereses"]
        picked = chosen if step == "localidad" and st.session_state.get("cifac_town_go") else None
        for index, example in enumerate(suggestions):
            if st.button(example, key=f"cifac_option_{step}_{index}", use_container_width=True):
                picked = example
        with st.form("cifac_chat_form", clear_on_submit=True):
            question = st.text_input("Tu pregunta", placeholder="Escribí tu consulta...", label_visibility="visible")
            submitted = st.form_submit_button("➤ Enviar", type="primary", use_container_width=True)
        message = picked or (question.strip() if submitted else None)
        if message:
            st.session_state.assistant_history.append({"role": "user", "content": message})
            normalized_message = normalize(message)
            wants_guidance = any(term in normalized_message for term in ["no se que estudiar", "no se que elegir", "no se que carrera", "estoy indeciso", "estoy indecisa", "explorar mis intereses"])
            wants_locality = "buscar carreras por localidad" in normalized_message
            wants_test = "descubrir mis intereses" in normalized_message
            wants_activities = "contarte que actividades" in normalized_message
            if wants_test:
                response = "🧭 ¡Excelente! Abrí la pestaña **Intereses** de esta página y respondé el cuestionario. Al finalizar verás tus tres áreas destacadas. Después podés volver a CIFAC y contarme qué área te interesó."
                st.session_state.cifac_step = "continuar"
            elif wants_activities:
                response = "💜 ¡Te escucho! Escribime qué te gusta hacer, aprender o investigar. Voy a buscar carreras relacionadas en nuestra base preliminar."
                st.session_state.cifac_step = "actividades"
            elif wants_guidance:
                response = "¡Claro! 💜 No necesitás decidir ahora. Podemos empezar con el **test de intereses** o con las actividades que disfrutás. ¿Qué preferís?"
                st.session_state.cifac_step = "orientacion"
            elif wants_locality:
                response = "📍 ¡Vamos a buscar! ¿En qué localidad de Jujuy te gustaría estudiar? Elegí una opción o escribí otra localidad."
                st.session_state.cifac_step = "localidad"
            elif st.session_state.cifac_step == "tipo":
                loc = st.session_state.get("cifac_locality", "")
                local_rows = df[df[town] == loc].copy()
                local_rows["_kind"] = local_rows.apply(career_kind, axis=1)
                if normalized_message == "ver todas las carreras":
                    chosen_rows = local_rows
                else:
                    chosen_rows = local_rows[local_rows["_kind"].map(normalize) == normalized_message]
                if chosen_rows.empty:
                    response = "No encontré esa categoría en esta localidad. Elegí una de las opciones disponibles."
                    st.session_state.cifac_step = "tipo"
                else:
                    chosen_rows = chosen_rows.drop_duplicates(subset=[career, "Institución"])
                    lines = [f"🎓 **{loc} — {message}**", "",
                             f"Encontré **{len(chosen_rows)} carreras registradas** en esta categoría:", ""]
                    for index, (_, item) in enumerate(chosen_rows.sort_values(career).iterrows(), 1):
                        lines.extend([f"**{index}. {item[career]}**",
                                      f"🏫 {item['Institución']}",
                                      ("⚠️ " + str(item.get("Observación", ""))) if str(item.get("Observación", "")).strip() else "", ""])
                    lines.append("*Registros históricos: verificá la oferta actual, sede y gratuidad con la institución.*")
                    response = "\n".join(lines)
                    st.session_state.cifac_step = "continuar"
            else:
                found, selected_localities = find_careers(message)
                if st.session_state.cifac_step == "localidad" and not selected_localities:
                    response = "No encontré esa localidad en nuestra base histórica. Escribí otra localidad de Jujuy."
                elif st.session_state.cifac_step == "localidad" and selected_localities:
                    loc = selected_localities[0]
                    st.session_state.cifac_locality = loc
                    kinds = sorted(df[df[town] == loc].apply(career_kind, axis=1).unique().tolist())
                    response = f"📍 Encontré **{len(df[df[town] == loc])} registros históricos** en **{loc}**. ¿Qué tipo de formación te interesa? Podés elegir: {', '.join(kinds)}, o ver todas las carreras."
                    st.session_state.cifac_step = "tipo"
                elif found.empty:
                    response = "No encontré coincidencias en la base preliminar. Probá con otra localidad o con una palabra del nombre de una carrera."
                else:
                    location_text = f" en {', '.join(selected_localities)}" if selected_localities else " en Jujuy"
                    response = f"Encontré estas opciones registradas{location_text}:\n\n"
                    for _, item in found.head(8).iterrows():
                        response += f"- **{item[career]}** — {item['Institución']} ({item[town]})\n"
                    if len(found) > 8:
                        response += f"\nHay {len(found) - 8} opciones adicionales. Podés precisar tu consulta.\n"
                    response += "\n*Información histórica sin verificar: confirmá carreras, sedes y gratuidad con cada institución.*"
                if st.session_state.cifac_step not in ("tipo", "localidad"):
                    st.session_state.cifac_step = "continuar"
            st.session_state.assistant_history.append({"role": "assistant", "content": response})
            st.rerun()
        if st.button("🗑️ Borrar conversación", key="clear_cifac_chat"):
            st.session_state.assistant_history = []
            st.session_state.cifac_step = "inicio"
            st.rerun()
        st.caption("Buscador conversacional, no IA generativa ni orientación vocacional profesional.")

tab_map,tab_search,tab_test=st.tabs(["🗺️ Mapa","🔎 Carreras","🧭 Intereses"])
with tab_map:
    st.subheader("Explorá Jujuy por departamento")
    st.caption("Seleccioná un departamento en el mapa de colores para conocer las localidades y carreras registradas.")
    dept_towns = {
        "COCHINOCA": ["Abra Pampa"],
        "EL CARMEN": ["El Carmen", "Monterrico", "Perico"],
        "DOCTOR MANUEL BELGRANO": ["San Salvador de Jujuy"],
        "HUMAHUACA": ["Humahuaca"],
        "LEDESMA": ["Libertador General San Martín", "Fraile Pintado", "Yuto"],
        "PALPALA": ["Palpalá"],
        "RINCONADA": [],
        "SAN ANTONIO": [],
        "SAN PEDRO": ["San Pedro", "La Mendieta"],
        "SANTA BARBARA": ["Palmasola"],
        "SANTA CATALINA": [],
        "SUSQUES": ["Susques"],
        "TILCARA": ["Tilcara"],
        "TUMBAYA": ["Tumbaya"],
        "VALLE GRANDE": [],
        "YAVI": ["La Quiaca"],
    }
    dept_names = sorted(dept_towns)
    geo_path = Path(__file__).with_name("departamentos_jujuy.geojson")
    if "dept_choice" not in st.session_state:
        st.session_state.dept_choice = "Todos"
    if "last_map_click" not in st.session_state:
        st.session_state.last_map_click = None

    selected_department = st.session_state.dept_choice
    if geo_path.exists():
        with open(geo_path, encoding="utf-8") as geo_file:
            boundaries = json.load(geo_file)
        m = folium.Map(
            location=[-23.25, -65.7], zoom_start=8, tiles=None,
            zoom_control=False, scrollWheelZoom=False,
            dragging=False, doubleClickZoom=False
        )
        folium.GeoJson(
            boundaries,
            name="Departamentos",
            style_function=lambda feature: {
                "fillColor": "#F59E0B" if feature["properties"]["departamento"] == selected_department
                             else feature["properties"]["color"],
                "color": "#9A3412" if feature["properties"]["departamento"] == selected_department
                         else "#475569",
                "weight": 4 if feature["properties"]["departamento"] == selected_department else 1.6,
                "fillOpacity": 1 if feature["properties"]["departamento"] == selected_department else 0.88
            },
            highlight_function=lambda feature: {
                "fillColor": "#F59E0B", "color": "#9A3412",
                "weight": 3, "fillOpacity": 1
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["departamento"], aliases=["Departamento:"], sticky=False
            ),
        ).add_to(m)
        # Etiquetas visibles, ubicadas sobre cada departamento.
        # Los nombres largos se dividen en dos renglones para que no se superpongan.
        label_names = {
            "DOCTOR MANUEL BELGRANO": "Dr. Manuel<br>Belgrano",
            "SANTA CATALINA": "Santa<br>Catalina",
            "SANTA BARBARA": "Santa<br>Bárbara",
            "VALLE GRANDE": "Valle<br>Grande",
            "SAN ANTONIO": "San<br>Antonio",
            "SAN PEDRO": "San Pedro",
            "EL CARMEN": "El Carmen",
        }
        for feature in boundaries["features"]:
            name = feature["properties"]["departamento"]
            ring = feature["geometry"]["coordinates"][0]
            lons = [p[0] for p in ring]
            lats = [p[1] for p in ring]
            lat, lon = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
            label = label_names.get(name, name.title())
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    icon_size=(115, 32), icon_anchor=(57, 16),
                    html=(
                        '<div style="width:115px;text-align:center;'
                        'font:600 10px/1.1 Arial,sans-serif;color:#253047;'
                        'text-shadow:1px 1px 2px white,-1px -1px 2px white;'
                        'pointer-events:none;">' + label + '</div>'
                    )
                ),
            ).add_to(m)
        m.fit_bounds([[-24.65, -67.3], [-21.7, -64.0]])
        event = st_folium(
            m, height=620, use_container_width=True,
            returned_objects=["last_object_clicked_tooltip"],
            key="mapa_departamentos"
        )
        clicked = (event or {}).get("last_object_clicked_tooltip")
        if clicked and clicked != st.session_state.last_map_click:
            st.session_state.last_map_click = clicked
            matched = next((name for name in dept_names if name in str(clicked).upper()), None)
            if matched and matched != selected_department:
                st.session_state.dept_choice = matched
                st.rerun()
    else:
        st.error("No se encontró el archivo del mapa departamental.")
    selected_department = st.selectbox(
        "Departamento seleccionado (también podés hacer clic en el mapa)",
        ["Todos"] + dept_names, key="dept_choice"
    )
    if selected_department == "Todos":
        st.info("Hacé clic en un departamento coloreado o elegilo en la lista.")
        selected_town = st.selectbox("Localidad", ["Todas"] + towns, key="map_town_all")
        filtered = df if selected_town == "Todas" else df[df[town] == selected_town]
    else:
        available = [loc for loc in dept_towns[selected_department] if loc in towns]
        st.markdown(f"### 📍 {selected_department.title()}")
        if available:
            selected_town = st.selectbox(f"Localidades de {selected_department.title()}", ["Todas las localidades del departamento"] + available, key=f"map_town_{selected_department}")
            filtered = df[df[town].isin(available)] if selected_town == "Todas las localidades del departamento" else df[df[town] == selected_town]
            st.caption(f"{len(filtered)} registros históricos en esta selección. Elegí una localidad para ver sus instituciones y carreras.")
        else:
            filtered = df.iloc[0:0]
            st.info("Este departamento no tiene localidades con ofertas cargadas en la base preliminar; eso no significa que no existan carreras.")
    if filtered.empty:
        st.info("Todavía no hay ofertas cargadas para esta selección en la base preliminar.")
    else:
        st.markdown("### 🎓 Carreras por localidad")
        st.caption("Las inscripciones, los requisitos y las sedes pueden variar. Consultá la información oficial de cada institución.")
        kind_order = ["Profesorados", "Tecnicaturas", "Ingenierías", "Licenciaturas", "Otras formaciones"]
        for locality, locality_group in filtered.groupby(town, sort=True):
            st.markdown(f"#### 📍 {locality}")
            locality_group = locality_group.copy()
            locality_group["_tipo_grupo"] = locality_group.apply(career_kind, axis=1)
            for kind in kind_order:
                grouped = locality_group[locality_group["_tipo_grupo"] == kind]
                if grouped.empty:
                    continue
                st.markdown(f"**{kind} ({len(grouped)})**")
                for _, item in grouped.sort_values(career).iterrows():
                    with st.container(border=True):
                        st.markdown(f"**🎓 {item[career]}**")
                        st.caption(f"📚 Tipo de formación: {kind[:-1] if kind != 'Otras formaciones' else 'Otra formación'}")
                        st.caption(f"🏫 {item['Institución']}")
                        if str(item.get("Facultad", "")).strip():
                            st.caption(f"🏛️ {item['Facultad']}")
                        sede = str(item.get("Sede de cursado confirmada", "")).strip()
                        if not sede:
                            sede = str(item.get("Lugar donde se dicta", "")).strip()
                        if sede and "dirección a confirmar" not in sede and "dirección sin confirmar" not in sede:
                            st.caption(f"📍 Sede: {sede}")
                        st.caption(f"Área: {item['Área principal preliminar']}")
        with st.expander("Ver tabla completa de registros"):
            results(filtered)
with tab_search:
    q=st.text_input("Buscá una carrera o palabra clave")
    loc=st.selectbox("Filtrar localidad",["Todas"]+towns,key="searchloc")
    subset=df if loc=="Todas" else df[df[town]==loc]
    if q:
        subset=subset[subset.apply(lambda row:q.casefold() in " ".join(map(str,row.values)).casefold(),axis=1)]
    results(subset)
with tab_test:
    st.subheader("🧭 Descubrí tus intereses")
    st.write("Respondé según lo que te gustaría hacer. No hay respuestas correctas.")
    st.info("Actividad exploratoria, no es un test vocacional validado.")
    areas = {
        "Tecnología e informática": ["Crear una aplicación que resuelva un problema cotidiano.", "Investigar por qué un dispositivo no funciona.", "Encontrar patrones en un conjunto de datos."],
        "Salud y bienestar": ["Aprender cómo funciona el cuerpo humano.", "Participar en actividades de prevención y cuidado.", "Escuchar y acompañar a alguien que necesita ayuda."],
        "Educación": ["Explicar un tema de distintas maneras.", "Preparar una actividad para que otras personas aprendan.", "Ayudar a alguien a superar una dificultad de aprendizaje."],
        "Sociedad y humanidades": ["Investigar una historia de tu comunidad.", "Debatir soluciones para un problema social.", "Comprender cómo cambian las costumbres de una sociedad."],
        "Arte y comunicación": ["Crear un video para contar una historia.", "Diseñar imágenes para comunicar una idea.", "Inventar una producción musical, visual o escrita."],
        "Ambiente y producción": ["Investigar cómo proteger un ecosistema.", "Conocer cómo se producen los alimentos.", "Proponer soluciones para reducir residuos."],
        "Administración y economía": ["Organizar los recursos de un proyecto.", "Planificar un pequeño emprendimiento.", "Comparar presupuestos para tomar decisiones."],
        "Turismo y servicios": ["Diseñar un recorrido para conocer Jujuy.", "Organizar una actividad para recibir visitantes.", "Dar a conocer las tradiciones de una localidad."]
    }
    questions = [(area, i, question) for area, items in areas.items() for i, question in enumerate(items)]
    questions = sorted(questions, key=lambda item: (item[1] * 11 + list(areas).index(item[0]) * 5) % 24)
    options = ["Mucho", "Bastante", "Poco", "Nada", "No estoy seguro/a"]
    with st.form("intereses_nuevo"):
        answers = {}
        for number, (area, index, question) in enumerate(questions, 1):
            answers[(area, index)] = st.radio(
                f"{number}. ¿Qué tanto te gustaría...? {question}",
                options, index=None, key=f"interes_{number}"
            )
        sent = st.form_submit_button("✨ ¡Descubrir mi perfil vocacional!", type="primary", use_container_width=True)
    if sent:
        if any(answer is None for answer in answers.values()):
            st.warning("Respondé todas las preguntas para ver tus resultados.")
        else:
            values = {"Mucho": 4, "Bastante": 3, "Poco": 2, "Nada": 1}
            scores = {}
            uncertainty = {}
            for area, items in areas.items():
                selected = [answers[(area, i)] for i in range(len(items))]
                valid = [values[x] for x in selected if x in values]
                scores[area] = round(sum(valid) / len(valid), 2) if valid else None
                uncertainty[area] = selected.count("No estoy seguro/a")
            ranked = sorted((area for area in areas if scores[area] is not None), key=lambda area: scores[area], reverse=True)
            st.subheader("🌟 Tu perfil exploratorio")
            if ranked:
                st.success("Áreas de mayor interés expresado: " + ", ".join(ranked[:3]))
                st.markdown("### ✨ Tus 3 áreas de mayor interés")
                descriptions = {
                    "Tecnología e informática": "Te atrae crear soluciones digitales, explorar datos y resolver desafíos tecnológicos.",
                    "Salud y bienestar": "Te interesa conocer el cuerpo humano, cuidar y acompañar a otras personas.",
                    "Educación": "Te gusta compartir conocimientos y acompañar procesos de aprendizaje.",
                    "Sociedad y humanidades": "Te interesa comprender la historia, la cultura y los problemas de la sociedad.",
                    "Arte y comunicación": "Disfrutás crear, expresar ideas y comunicar de distintas maneras.",
                    "Ambiente y producción": "Te interesa cuidar la naturaleza y explorar formas de producción sustentable.",
                    "Administración y economía": "Te gusta organizar proyectos, recursos y emprendimientos.",
                    "Turismo y servicios": "Te interesa compartir el patrimonio de Jujuy y organizar experiencias para visitantes."
                }
                backgrounds = ["#F0E8FF", "#E5F5F4", "#FFF1DB"]
                accents = ["#6D35B5", "#087C79", "#A66312"]
                top_three = ranked[:3]
                for index, area in enumerate(top_three):
                    number = index + 1
                    tied_with_previous = index > 0 and scores[area] == scores[top_three[index - 1]]
                    label = f"{number}° lugar" if not tied_with_previous else f"{number}° área destacada · mismo interés que la anterior"
                    st.markdown(
                        f"""<div style="background:{backgrounds[index]};border-left:6px solid {accents[index]};border-radius:14px;padding:20px 24px;margin:12px 0;">
                        <div style="color:{accents[index]};font-size:22px;font-weight:800;">{label}</div>
                        <div style="color:#20242c;font-size:23px;font-weight:750;margin:5px 0 9px;">{area}</div>
                        <div style="color:#414852;font-size:16px;line-height:1.5;">{descriptions[area]}</div>
                        </div>""",
                        unsafe_allow_html=True
                    )
                st.caption("Se muestran solo tres áreas. Si hay puntajes iguales, el orden entre esas áreas no indica mayor interés. Este resultado es orientativo y no mide capacidades.")
                st.markdown("### Carreras para seguir explorando")
                for area in ranked[:3]:
                    st.markdown(f"**{area}**")
                    matches = df[df["Área principal preliminar"].astype(str).str.lower().str.contains(area.split(" ")[0].lower(), regex=False)]
                    if matches.empty:
                        st.caption("Explorá las carreras en la pestaña Carreras; no hay coincidencias directas en la clasificación preliminar.")
                    else:
                        display_cols = [career, town, "Institución"]
                        if "Observación" in matches.columns:
                            display_cols.append("Observación")
                        st.dataframe(matches[display_cols].drop_duplicates(), hide_index=True, use_container_width=True)
            else:
                st.info("Elegiste 'No estoy seguro/a' en todas las preguntas. Podés explorar actividades antes de decidir.")
            total_uncertain = sum(uncertainty.values())
            if total_uncertain:
                st.write(f"Marcaste 'No estoy seguro/a' en {total_uncertain} actividades. Es una oportunidad para conocerlas mejor.")
            st.caption("Los registros de carreras son históricos y deben verificarse con cada institución. Este resultado no determina qué estudiar.")

st.divider()
st.caption("Mi Futuro Jujuy · Prototipo educativo · Información en revisión")
