import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path
import json
import io
import uuid
from urllib.request import urlopen

st.set_page_config(page_title="Mi Futuro Jujuy", page_icon="🎓", layout="wide")
st.markdown("""<style>div.st-key-intereses_nuevo button[kind=\"primaryFormSubmit\"] {background:#7138c8;color:white;border:0;font-weight:700;} div.st-key-intereses_nuevo button[kind=\"primaryFormSubmit\"]:hover {background:#5925a7;color:white;}</style>""", unsafe_allow_html=True)
FILE = Path(__file__).with_name("carreras.xlsx")
if not FILE.exists():
    st.error("Falta cargar el archivo carreras.xlsx en el repositorio. Descargá la base preliminar y subila con Add file > Upload files.")
    st.stop()
@st.cache_data
def load_data():
    return pd.read_excel(FILE, sheet_name="Carreras").fillna("")
df = load_data()
# El IES 6 se actualizó con la oferta oficial anunciada para ingreso 2027.
# No recuperar registros históricos de ese instituto desde el Excel de respaldo.
import re as _re
def _es_ies6(nombre):
    t = str(nombre).casefold()
    return bool(_re.search(r"(?:\bies\b|instituto de educaci[oó]n superior)\s*(?:n[.°ºo]*\s*)?6\b", t))
df = df[~df["Institución"].map(_es_ies6)].copy()
# Google Sheets es la fuente principal. El CSV local es una copia reciente
# del catálogo público: evita fichas viejas si la versión publicada de Sheets
# todavía no se actualizó o si falla temporalmente la descarga.
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTqkZDRlfoNYwLpzqnMi9AeVI-Y2stohIpvKVL2hr_Gy4Gp3Ay_gaOEvTNDDuDgVL1sypWyRw5EUX8M/pub?gid=2132573097&single=true&output=csv"
SHEET_BACKUP = Path(__file__).with_name("carreras_actualizadas.csv")

@st.cache_data(ttl=300, show_spinner=False)
def load_google_sheet():
    campos_basicos = {"Institución", "Localidad", "Carrera", "Tipo de formación"}
    campos_actualizados = {
        "Sitio web institucional", "Teléfono institucional", "Correo institucional",
        "Unidad académica", "Título otorgado", "Ingreso 2027",
    }

    copia = pd.read_csv(SHEET_BACKUP, dtype=str, keep_default_na=False) if SHEET_BACKUP.exists() else None
    fuente = "respaldo actualizado de Google Sheets"
    tabla = copia

    try:
        with urlopen(SHEET_CSV_URL, timeout=12) as respuesta:
            contenido_csv = respuesta.read().decode("utf-8-sig")
        publicada = pd.read_csv(io.StringIO(contenido_csv), dtype=str, keep_default_na=False)
        publicada = publicada[publicada["Carrera"].astype(str).str.strip().ne("")].copy()
        # Un enlace público de Sheets puede estar publicado con una versión
        # antigua: nunca usarla si perdió campos nuevos o casi todas las carreras.
        minimo = max(1, int(len(copia) * 0.90)) if copia is not None else 1
        if (campos_basicos.issubset(publicada.columns)
                and (copia is None or campos_actualizados.issubset(publicada.columns))
                and len(publicada) >= minimo):
            tabla = publicada
            fuente = "Google Sheets"
    except Exception:
        pass  # Seguir con la copia completa y vigente, nunca con el Excel antiguo.

    if tabla is None or not campos_basicos.issubset(tabla.columns):
        raise ValueError("La base de carreras actualizada no está disponible.")
    tabla = tabla[tabla["Carrera"].astype(str).str.strip().ne("")].copy()
    tabla = tabla.rename(columns={
        "Carrera": "Carrera / título",
        "Área preliminar": "Área principal preliminar",
        "Sede/dirección": "Sede de cursado confirmada",
    })
    return tabla, fuente

try:
    google_df, fuente_carreras = load_google_sheet()
    # Reemplazar en el respaldo las instituciones presentes en Sheets.
    # Así las bajas y correcciones en Drive no vuelven a aparecer desde Excel.
    # Equiparar "IES 10" con "INSTITUTO DE EDUCACIÓN SUPERIOR N° 10" del respaldo.
    def clave_institucion(valor):
        import re
        import unicodedata
        txt = "".join(letra for letra in unicodedata.normalize("NFKD", str(valor).casefold())
                      if not unicodedata.combining(letra))
        numero = re.search(r"(?:\bies\b|instituto de educacion superior)\s*(?:n[.°ºo]*\s*)?(\d+)\b", txt)
        return "ies " + numero.group(1) if numero else txt.strip()
    institutos_google = set(google_df["Institución"].map(clave_institucion))
    # Conservar las tecnicaturas y las demás carreras históricas de los IES
    # estatales incorporados ahora (3, 4 y 5). La ausencia de una tecnicatura
    # de la planilla NO significa que el instituto haya dejado de dictarla.
    # Para los IES ya depurados (1, 2, 6, 9, 10 y 11) se mantienen las
    # decisiones previas para no reintroducir registros descartados.
    conservar_respaldo_de = {"ies 3", "ies 4", "ies 5"}
    def clave_textual(valor):
        import unicodedata
        import re
        txt = "".join(ch for ch in unicodedata.normalize("NFKD", str(valor).casefold())
                      if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9]+", " ", txt).strip()

    claves_google = {
        (clave_institucion(fila.get("Institución", "")),
         clave_textual(fila.get("Localidad", "")),
         clave_textual(fila.get("Carrera / título", "")))
        for _, fila in google_df.iterrows()
    }

    def conservar_registro_historico(fila):
        institucion = clave_institucion(fila.get("Institución", ""))
        if institucion not in institutos_google:
            return True
        if institucion not in conservar_respaldo_de:
            return False
        clave = (institucion,
                 clave_textual(fila.get("Localidad", "")),
                 clave_textual(fila.get("Carrera / título", "")))
        return clave not in claves_google

    df = df[df.apply(conservar_registro_historico, axis=1)].copy()
    df["_registro_actualizado"] = False
    google_df["_registro_actualizado"] = True
    df = pd.concat([df, google_df], ignore_index=True)
    st.caption(f"📄 Oferta de gestión estatal · fuente: {fuente_carreras}. La plataforma consulta actualizaciones aproximadamente cada 5 minutos.")
except Exception:
    st.caption("📄 Mostrando la copia de respaldo. Para activar la sincronización, publicá la pestaña Carreras como CSV en Google Sheets.")


# Conservar las tecnicaturas históricas de los IES, aun cuando la ficha
# mencione un cierre de preinscripción para una cohorte anterior.
# Cierre de ingreso NO equivale a supresión de la carrera del catálogo.
cerrada_para_ingreso = df.astype(str).apply(
    lambda col: col.str.contains(
        "inscripciones no habilitadas|inscripciones cerradas|no admite ingresantes",
        case=False, regex=True)
).any(axis=1)
es_ies = df["Institución"].astype(str).str.contains(
    r"(?:\bies\b|instituto de educaci[oó]n superior)\s*(?:n[.°ºo]*\s*)?\d+",
    case=False, regex=True)
es_tecnica = df["Carrera / título"].astype(str).str.contains(
    "tecnicatura|técnic", case=False, regex=True
) | df["Tipo de formación"].astype(str).str.contains(
    "tecnicatura", case=False, regex=True
)
df = df[~cerrada_para_ingreso | (es_ies & es_tecnica)].copy()
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
# Esta plataforma presenta exclusivamente carreras de gestión ESTATAL.
# Algunos institutos numerados son de gestión privada (IES 7 Populorum
# Progressio e IES 8 Sagrado Corazón FASTA); tener número de IES no implica
# pertenecer a la oferta pública provincial. Se aplica el filtro también
# a carreras del respaldo histórico, aunque Google Sheets no esté disponible.
def institucion_de_gestion_estatal(nombre):
    import re
    import unicodedata
    texto = "".join(ch for ch in unicodedata.normalize("NFKD", str(nombre).casefold())
                    if not unicodedata.combining(ch))
    if any(part in texto for part in ("populorum", "fasta", "sagrado corazon")):
        return False
    ies = re.search(r"(?:\bies\b|instituto de educacion superior)\s*(?:n[.°ºo]*\s*)?(\d+)\b", texto)
    if ies:
        return int(ies.group(1)) in {1, 2, 3, 4, 5, 6, 9, 10, 11}
    return any(s in texto for s in (
        "unju", "universidad nacional de jujuy",
        "utn", "universidad tecnologica nacional",
        "universidad nacional de salta", "unsa",
        "instituto superior de artes", "escuela superior de musica",
        "escuela superior de danza", "escuela provincial de teatro",
        "escuela provincial de artes",
    ))

df = df[df["Institución"].map(institucion_de_gestion_estatal)].copy()

# Evitar repeticiones de la misma carrera, institución y localidad.
# Si están tanto en el Excel anterior como en la base vigente, DEBE ganar
# la ficha de Google Sheets: contiene duración, contacto y sede confirmada.
if "_registro_actualizado" in df.columns:
    df["_registro_actualizado"] = df["_registro_actualizado"].fillna(False).astype(bool)
    df = df.sort_values("_registro_actualizado", ascending=False, kind="stable")
df["_clave_carrera"] = df["Carrera / título"].astype(str).str.strip().str.casefold()
df["_clave_localidad"] = df["Localidad"].astype(str).str.strip().str.casefold()
# Unificar variantes del nombre institucional (UNJu, UNJu - Facultad de...).
# Conservar carreras iguales en localidades diferentes.
def _clave_institucion_canonica(valor):
    import unicodedata
    t = "".join(x for x in unicodedata.normalize("NFKD", str(valor).casefold())
                if not unicodedata.combining(x))
    if "unju" in t or "universidad nacional de jujuy" in t:
        return "universidad nacional de jujuy"
    t = _re.sub(r"\s*\(extension aulica\)", "", t)
    return " ".join(t.split())
df["_clave_institucion"] = df["Institución"].map(_clave_institucion_canonica)
df = df.drop_duplicates(subset=["_clave_carrera", "_clave_localidad", "_clave_institucion"])
df = df.drop(columns=["_clave_carrera", "_clave_localidad", "_clave_institucion", "_registro_actualizado"], errors="ignore")
import re
import unicodedata

def normalize(value):
    value = unicodedata.normalize("NFKD", str(value).casefold())
    return "".join(char for char in value if not unicodedata.combining(char))

def visible_value(value):
    """No mostrar valores ausentes ni datos declarados pendientes de confirmar."""
    if value is None:
        return ""
    if not isinstance(value, str) and pd.isna(value):
        return ""
    text = str(value).strip()
    clean = normalize(text)
    if clean in {
        "", "nan", "none", "null", "nat", "n/a", "na", "sin dato",
        "sin datos", "no disponible", "no informado", "no informada",
        "por clasificar", "sin clasificar", "en revision", "a verificar",
        "-", "consultar",
        "no informados", "no informadas", "a confirmar", "por confirmar",
        "sin confirmar", "pendiente de confirmar",
        "pendiente de confirmacion", "pendiente de verificacion",
        "no especificado", "no especificada", "consultar duracion",
        "duracion no informada", "sin informacion",
    }:
        return ""
    if any(fragment in clean for fragment in (
        "pendiente de confirm", "pendiente de verific", "direccion sin confirmar",
        "direccion a confirmar", "domicilio a confirmar", "domicilio sin confirmar",
        "sede a confirmar", "sede sin confirmar", "direccion no confirmada",
        "direccion no informada", "consultar domicilio", "consultar direccion",
    )):
        return ""
    return text


def contacto_institucional_visible(row):
    """Datos de contacto confirmados: sin campos vacíos, URLs inválidas ni marcadores."""
    from urllib.parse import urlsplit
    sitio = visible_value(row.get("Sitio web institucional", ""))
    if sitio:
        try:
            enlace = urlsplit(sitio)
            if enlace.scheme not in ("https", "http") or not enlace.netloc or any(x in sitio for x in (" ", "<", ">", "(", ")")):
                sitio = ""
        except ValueError:
            sitio = ""
    telefono = visible_value(row.get("Teléfono institucional", ""))
    correo = visible_value(row.get("Correo institucional", ""))
    if correo and not re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", correo):
        correo = ""
    return sitio, telefono, correo


def enlace_oficial_carrera(row):
    """Enlace oficial de la carrera si consta en la base y es una URL válida."""
    from urllib.parse import urlsplit
    enlace = visible_value(row.get("Enlace oficial", ""))
    if not enlace:
        return ""
    try:
        url = urlsplit(enlace)
        if url.scheme not in ("http", "https") or not url.netloc:
            return ""
        if any(c in enlace for c in (" ", "<", ">", "(", ")")):
            return ""
    except ValueError:
        return ""
    return enlace


def mostrar_informacion_y_contacto(row):
    """Un solo apartado en todas las fichas; nunca muestra etiquetas vacías."""
    pagina = enlace_oficial_carrera(row)
    sitio, telefono, correo = contacto_institucional_visible(row)
    # Priorizar la página específica de la carrera; si no existe, mostrar
    # el sitio institucional. Nunca duplicar enlaces.
    enlace = pagina or sitio
    detalles = []
    if enlace:
        detalles.append(f"🔗 [Página web oficial]({enlace})")
    if telefono:
        detalles.append(f"📞 **Teléfono:** {telefono}")
    if correo:
        detalles.append(f"✉️ **Correo:** [{correo}](mailto:{correo})")
    if not detalles:
        return
    st.markdown("**🌐 Información y contacto**")
    st.markdown("  \n".join(detalles))


def ingreso_2027_visible(row):
    """Ingreso 2027: mostrar solo datos oficiales aportados en la base."""
    from urllib.parse import urlsplit
    resumen = visible_value(row.get("Ingreso 2027", ""))
    enlace = visible_value(row.get("Enlace de ingreso 2027", ""))
    if enlace:
        try:
            url = urlsplit(enlace)
            if url.scheme not in ("http", "https") or not url.netloc or any(c in enlace for c in (" ", "<", ">")):
                enlace = ""
        except ValueError:
            enlace = ""
    return resumen, enlace


def mostrar_ingreso_2027(row):
    resumen, enlace = ingreso_2027_visible(row)
    if not (resumen or enlace):
        return
    with st.expander("📅 Ingreso 2027"):
        if resumen:
            st.write(resumen)
        if enlace:
            st.markdown(f"🔗 [Ver información oficial de ingreso 2027]({enlace})")


def alcance_sede_visible(row):
    """Aviso importante: algunas sedes ofrecen solo el primer año."""
    obs = normalize(row.get("Observación", ""))
    dur = normalize(row.get("Duración", ""))
    if re.search(r"\bsolo\s*(?:1|primer)\b", obs + " " + dur):
        return "En esta sede se cursa solo el primer año; consultá dónde continuar."
    return ""


# La información pendiente permanece en Sheets; nunca se presenta como dato seguro.
public_fields = [
    "Institución", "Localidad", "Carrera / título", "Tipo de formación",
    "Área principal preliminar", "Duración", "Modalidad", "Facultad",
    "Sede de cursado confirmada", "Lugar donde se dicta",
    "Sitio web institucional", "Teléfono institucional", "Correo institucional",
    "Título otorgado", "Unidad académica", "Ingreso 2027", "Enlace de ingreso 2027",
    "Enlace oficial",
]
for field in public_fields:
    if field in df.columns:
        df[field] = df[field].map(visible_value)
df = df[df["Carrera / título"].ne("")].copy()

town = "Localidad"
career = "Carrera / título"
towns = sorted(localidad for localidad in df[town].unique() if localidad)
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
        frame = frame.copy()
        frame["Duración"] = frame.apply(duracion_visible, axis=1)
        frame["Modalidad"] = frame.apply(modalidad_visible, axis=1)
        frame["Página web"] = frame.apply(
            lambda row: enlace_oficial_carrera(row) or contacto_institucional_visible(row)[0],
            axis=1,
        )
        display_cols = ["Institución", town, career, "Tipo de formación", "Duración", "Modalidad", "Área principal preliminar", "Página web"]
        display_cols = [column for column in display_cols if column in frame.columns]
        for column in display_cols:
            frame[column] = frame[column].map(visible_value)
        display_cols = [column for column in display_cols if frame[column].ne("").any()]
        if display_cols:
            st.dataframe(
                frame[display_cols], hide_index=True, use_container_width=True,
                column_config={
                    "Página web": st.column_config.LinkColumn("🌐 Página web", display_text="Abrir")
                } if "Página web" in display_cols else {},
            )
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

# Mantener la dirección real que viene de Google Sheets. Sobrescribirla solo
# si existe una corrección específica y confirmada para el IES N.º 10.
if "Sede de cursado confirmada" not in df.columns:
    df["Sede de cursado confirmada"] = ""
sede_confirmada_ies10 = df.apply(sede_ies10, axis=1)
reemplazar_sede = sede_confirmada_ies10.ne("")
df.loc[reemplazar_sede, "Sede de cursado confirmada"] = sede_confirmada_ies10[reemplazar_sede]

# Aplicar correcciones históricas del IES 10 solo al respaldo cuando Drive no está disponible.
if "google_df" not in locals():
    # Mantener únicamente las tecnicaturas del IES N.º 10 confirmadas por la docente.
    # La oferta de profesorados del instituto se conserva sin cambios.
    tecnicaturas_ies10_vigentes = {
        ("yuto", "tecnicatura superior en higiene y seguridad"),
        ("libertador general san martin", "tecnicatura superior en cocina regional y cultura alimentaria"),
        ("fraile pintado", "tecnicatura superior en niñez, adolescencia y familia"),
    }
    def es_tecnicatura_ies10_anterior(row):
        inst = normalize(row.get("Institución", ""))
        titulo = normalize(row.get("Carrera / título", ""))
        localidad = normalize(row.get("Localidad", ""))
        ies10 = ("ies 10" in inst or "instituto de educacion superior" in inst and
                 any(s in inst for s in ("n° 10", "n.º 10", "nº 10", "n°10", "nº10")))
        es_tecnicatura = ("tecnicatura" in titulo or "tecnico superior" in titulo or
                           "tecnica superior" in titulo or
                           "tecnicatura" in normalize(row.get("Tipo de formación", "")))
        return ies10 and es_tecnicatura and (localidad, titulo) not in tecnicaturas_ies10_vigentes

    df = df[~df.apply(es_tecnicatura_ies10_anterior, axis=1)].copy()


    # Actualización de oferta del IES N.º 10 informada el 21/10/2026.
    # Se aplica a los datos cargados, sin atribuir aperturas de inscripción no verificadas.
    oferta_ies10_actualizada = [
        ("Yuto", "Tecnicatura Superior en Higiene y Seguridad", "Fundación Te Ayudamos Hermanos"),
        ("Libertador General San Martín", "Tecnicatura Superior en Cocina Regional y Cultura Alimentaria", "Escuela Normal"),
        ("Libertador General San Martín", "Enfermería", "Escuela Provincial de Comercio N.º 4"),
        ("Fraile Pintado", "Tecnicatura Superior en Niñez, Adolescencia y Familia", "Escuela N.º 123 Manuel Belgrano"),
    ]
    for localidad_nueva, titulo_nuevo, sede_nueva in oferta_ies10_actualizada:
        coincidencia = (
            (df["Localidad"].astype(str).str.strip().str.casefold() == localidad_nueva.casefold()) &
            (df["Carrera / título"].astype(str).str.strip().str.casefold() == titulo_nuevo.casefold()) &
            (df["Institución"].astype(str).str.contains(r"IES\s*(?:N[.º°]*\s*)?10|Instituto de Educación Superior.*10", case=False, regex=True, na=False))
        )
        if coincidencia.any():
            df.loc[coincidencia, "Sede de cursado confirmada"] = sede_nueva
        else:
            nueva_oferta = {
                "Institución": "IES N.º 10",
                "Localidad": localidad_nueva,
                "Carrera / título": titulo_nuevo,
                "Tipo de formación": "Tecnicatura Superior" if titulo_nuevo.startswith("Tecnicatura") else "",
                "Área principal preliminar": "Salud y bienestar" if "Enfermería" in titulo_nuevo else "",
                "Observación": "Oferta informada para esta sede. Consultar requisitos y período de inscripción con el IES N.º 10.",
                "Sede de cursado confirmada": sede_nueva,
            }
            df = pd.concat([df, pd.DataFrame([nueva_oferta])], ignore_index=True)



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

def duracion_visible(row):
    """Usa la duración registrada y completa las reglas conocidas de los IES provinciales."""
    registrada = visible_value(row.get("Duración", ""))
    if registrada:
        if "solo" in normalize(registrada) and re.search(r"\b(?:primer|1)\b", normalize(registrada)):
            return ""  # Alcance de una sede, no duración total.
        return registrada
    if normalize(row.get("Carrera / título", "")) == "profesorado tecnico":
        return ""  # La duración aún no está verificada.
    institucion = normalize(row.get("Institución", ""))
    match = __import__("re").search(r"(?:\bies\b|instituto de educacion superior)\s*(?:n[.°ºo]*\s*)?(\d+)\b", institucion)
    if not match:
        return ""
    numero = match.group(1)
    titulo = normalize(row.get("Carrera / título", ""))
    tipo = normalize(row.get("Tipo de formación", ""))
    if "tecnicatura" in titulo or "tecnicatura" in tipo:
        return "3 años"
    if "profesorado" in titulo or "profesorado" in tipo:
        if numero == "10" and "ciencias de la educacion" in titulo:
            return "5 años"
        if numero == "5" and "educacion superior" in titulo:
            return "5 años"
        return "4 años"
    return ""



def modalidad_visible(row):
    """Distingue la modalidad de cursado de la carrera de las instancias de ingreso."""
    registrada = visible_value(row.get("Modalidad", ""))
    if registrada:
        return registrada
    titulo = normalize(row.get("Carrera / título", ""))
    localidad = normalize(row.get("Localidad", ""))
    institucion = normalize(row.get("Institución", ""))
    if titulo == "licenciatura en ciencia politica":
        # La estudiante confirmó que cursa con clases virtuales y algunos exámenes presenciales.
        return "Virtual · algunos exámenes presenciales"
    if titulo == "tecnicatura universitaria en transformacion de la produccion agropecuaria":
        if localidad == "abra pampa":
            return "Modalidad especial: 75 % virtual y 25 % presencial intensiva al final del cuatrimestre"
        return "Presencial con alternancia: una semana en sede y otra virtual sincrónica"
    if titulo == "licenciatura en desarrollo rural":
        return "Modalidad especial: 75 % virtual y 25 % presencial intensiva (una semana al final de cada cuatrimestre)"
    # La FCA-UNJu publica alternancia en varias sedes del interior.
    # El cursado combina actividades presenciales con encuentros virtuales.
    carreras_alternancia_fca = {
        "tecnicatura universitaria en produccion de animales de granja",
        "tecnicatura universitaria en mecanizacion agricola",
        "tecnicatura universitaria forestal",
        "licenciatura en gestion ambiental"
    }
    if ("agrarias" in institucion or "fca" in institucion) and titulo in carreras_alternancia_fca:
        return "Presencial con alternancia (actividades presenciales y virtuales)"
    return ""  # Si no hay modalidad registrada, no inventar la categoría.


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
        for indice_mensaje, item in enumerate(st.session_state.assistant_history):
            with st.chat_message(item["role"]):
                st.markdown(item["content"])
                if item["role"] == "assistant" and indice_mensaje == len(st.session_state.assistant_history) - 1:
                    contenido = item["content"]
                    if "Iniciar el test ahora" in contenido:
                        if st.button("🧭 Iniciar el test ahora →", key="cifac_test_en_respuesta", type="primary", use_container_width=True):
                            st.session_state.mf_nav_pendiente = "📊 Mis intereses"
                            st.rerun()
                    if "Ir al mapa ahora" in contenido:
                        if st.button("🗺️ Ir al mapa ahora →", key="cifac_mapa_en_respuesta", type="primary", use_container_width=True):
                            st.session_state.mf_nav_pendiente = "📍 Mapa"
                            st.rerun()
        if "cifac_step" not in st.session_state:
            st.session_state.cifac_step = "inicio"
        step = st.session_state.cifac_step
        if step == "inicio" and not st.session_state.assistant_history:
            st.caption("Elegí una opción para empezar:")
            suggestions = ["No sé qué estudiar, ¿me ayudás?", "Quiero buscar carreras por localidad", "Me interesa la tecnología, ¿qué opciones tengo?"]
        elif step == "orientacion":
            st.caption("¿Cómo querés continuar?")
            suggestions = ["Hacer el test de intereses", "Explorar carreras en el mapa"]
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
        else:
            st.caption("Podés seguir preguntando o iniciar otra búsqueda:")
            suggestions = ["Buscar carreras por localidad", "Hacer el test de intereses", "Explorar carreras en el mapa"]
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
            wants_test = any(term in normalized_message for term in ["descubrir mis intereses", "hacer el test de intereses", "explorar mis intereses"])
            wants_map = any(term in normalized_message for term in ["explorar carreras en el mapa", "ir al mapa", "quiero ir al mapa", "abrir el mapa", "ver el mapa", "mostrame el mapa"])
            if wants_test:
                response = "🧭 ¡Excelente! Tocá **Iniciar el test ahora** para ir directamente al cuestionario."
                st.session_state.cifac_step = "continuar"
            elif wants_map:
                response = "🗺️ ¡Vamos al mapa! Tocá el botón **Ir al mapa ahora** que aparece debajo de esta respuesta para abrirlo directamente."
                st.session_state.cifac_step = "continuar"
            elif wants_guidance:
                response = "💜 No necesitás decidir ahora. Podés hacer el **test de intereses** para explorar áreas que te llaman la atención, o abrir el **Mapa** para conocer carreras por localidad. ¿Por dónde preferís empezar?"
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
                                      f"🏫 {item['Institución']}"])
                        aviso = alcance_sede_visible(item)
                        if aviso:
                            lines.append(f"ℹ️ {aviso}")
                        pagina = enlace_oficial_carrera(item)
                        sitio, _, _ = contacto_institucional_visible(item)
                        enlace = pagina or sitio
                        if enlace:
                            lines.append(f"🌐 [Página web oficial]({enlace})")
                        _, ingreso_link = ingreso_2027_visible(item)
                        if ingreso_link:
                            lines.append(f"📅 [Ingreso 2027]({ingreso_link})")
                        lines.append("")
                    lines.append("*Registros históricos: verificá la oferta actual, sede y gratuidad con la institución.*")
                    response = "\n".join(lines)
                    st.session_state.cifac_step = "continuar"
            elif any(term in normalized_message for term in ["me gusta", "me gustan", "disfruto", "prefiero hacer", "no me gusta"]) and not match_localities(message):
                response = "💜 Gracias por contarme tus intereses. Para no sugerirte carreras solo por unas pocas palabras, te recomiendo abrir **Intereses** y hacer el test, o explorar las opciones en **Mapa**. También puedo buscar una carrera o localidad concreta."
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
                        pagina = enlace_oficial_carrera(item)
                        sitio, _, _ = contacto_institucional_visible(item)
                        url = pagina or sitio
                        etiqueta = "Información oficial" if pagina else "Sitio institucional"
                        enlace = f" · [🔗 {etiqueta}]({url})" if url else ""
                        response += f"- **{item[career]}** — {item['Institución']} ({item[town]}){enlace}\n"
                    if len(found) > 8:
                        response += f"\nHay {len(found) - 8} opciones adicionales. Podés precisar tu consulta.\n"
                    response += "\n*Información histórica sin verificar: confirmá carreras, sedes y gratuidad con cada institución.*"
                if st.session_state.cifac_step not in ("tipo", "localidad"):
                    st.session_state.cifac_step = "continuar"
            st.session_state.assistant_history.append({"role": "assistant", "content": response})
            st.rerun()
        # Accesos directos: el asistente navega, no solo explica dónde hacer clic.
        if st.session_state.assistant_history:
            ultimo_usuario = next((item["content"] for item in reversed(st.session_state.assistant_history) if item["role"] == "user"), "")
            ultimo_normalizado = normalize(ultimo_usuario)
            acceso_mapa = any(term in ultimo_normalizado for term in ["mapa", "ir al mapa"])
            acceso_test = any(term in ultimo_normalizado for term in ["test de intereses", "descubrir mis intereses", "explorar mis intereses"])
            if acceso_mapa or st.session_state.cifac_step == "orientacion":
                if st.button("🗺️ Ir al mapa ahora →", key="cifac_ir_mapa", use_container_width=True):
                    st.session_state.mf_nav_pendiente = "📍 Mapa"
                    st.rerun()
            if acceso_test or st.session_state.cifac_step == "orientacion":
                if st.button("🧭 Iniciar el test ahora →", key="cifac_ir_test", use_container_width=True):
                    st.session_state.mf_nav_pendiente = "📊 Mis intereses"
                    st.rerun()
        if st.button("🗑️ Borrar conversación", key="clear_cifac_chat"):
            st.session_state.assistant_history = []
            st.session_state.cifac_step = "inicio"
            st.rerun()
        st.caption("Buscador conversacional, no IA generativa ni orientación vocacional profesional.")

# Pestañas diferenciadas por color: mapa, carreras e intereses.
st.markdown("""
<style>
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    border-radius: 12px 12px 0 0 !important;
    margin-right: 6px !important;
    font-weight: 700 !important;
    padding: 10px 17px !important;
    border-bottom: 3px solid transparent !important;
    transition: background-color .15s ease, color .15s ease;
}
div[data-testid="stTabs"] button[data-baseweb="tab"]:nth-child(1) {
    background: #E5F4ED !important; color: #237A56 !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"]:nth-child(2) {
    background: #E8EEFF !important; color: #3457B1 !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"]:nth-child(3) {
    background: #F2E7FF !important; color: #7941B3 !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"]:nth-child(1)[aria-selected="true"] {
    background: #237A56 !important; color: white !important; border-bottom-color: #17543C !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"]:nth-child(2)[aria-selected="true"] {
    background: #3457B1 !important; color: white !important; border-bottom-color: #243F83 !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"]:nth-child(3)[aria-selected="true"] {
    background: #7941B3 !important; color: white !important; border-bottom-color: #562B84 !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background: transparent !important;
}
@media (max-width: 600px) {
    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        padding: 9px 11px !important; margin-right: 3px !important;
        font-size: 13px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Navegación principal y portada
st.markdown("""
<style>
.block-container {padding-top:1.2rem;max-width:1480px}
[data-testid="stHeader"] {background:rgba(255,255,255,.92)}
div[data-testid="stSegmentedControl"] {justify-content:flex-end}
.mf-brand {font-size:2rem;font-weight:850;color:#0b2c55;letter-spacing:-1px}
.mf-brand em {color:#087d99;font-weight:650}
.mf-eyebrow {color:#173c68;letter-spacing:3px;font-weight:750;font-size:.83rem;margin-top:1.2rem}
.mf-hero-title {font-size:clamp(2.3rem,4.6vw,4.8rem);font-weight:850;line-height:1.06;color:#092a56;letter-spacing:-2px;margin:16px 0 20px}
.mf-hero-title em {font-style:italic;color:#087fa4}
.mf-intro {font-size:1.18rem;color:#345071;max-width:560px;line-height:1.55}
.mf-art {border-radius:30px;background:linear-gradient(145deg,#f3fbff,#fff 48%,#fff7e9);padding:25px;text-align:center;min-height:310px;position:relative}
.mf-map {display:inline-block;width:70%;height:285px;background:linear-gradient(165deg,#2388ba 0 19%,#e8c398 20% 35%,#b45638 36% 52%,#4a9c78 53% 67%,#f4e2b8 68% 80%,#c06e3d 81%);clip-path:polygon(33% 0,43% 6%,55% 4%,61% 16%,55% 30%,67% 39%,71% 50%,93% 55%,97% 71%,87% 85%,76% 86%,64% 100%,49% 90%,43% 74%,27% 66%,19% 54%,25% 40%,21% 27%,28% 15%);filter:drop-shadow(0 4px 4px #163f69)}
.mf-art-title {color:#0d385e;font-weight:800;font-size:1.1rem;margin-top:5px}
.mf-art-caption {color:#35617a;font-size:.92rem;margin-top:7px}
.mf-card {min-height:255px;border-radius:22px;padding:22px 22px 12px;margin-bottom:4px}
.mf-card h3 {font-size:1.55rem;margin:12px 0;color:#0b2d54;font-weight:800}
.mf-card p {color:#274766;font-size:1rem;line-height:1.45}
.mf-icon {font-size:2.45rem;display:flex;align-items:center;justify-content:center;width:86px;height:86px;margin:5px auto 16px;border-radius:50%;background:#ffffff80;box-shadow:0 2px 10px #102f4a10}
.mf-card h3,.mf-card p{text-align:center}
div[class*="st-key-ir_01"] button{background:#007d80!important;border-color:#007d80!important;color:white!important}
div[class*="st-key-ir_02"] button{background:#0867df!important;border-color:#0867df!important;color:white!important}
div[class*="st-key-ir_03"] button{background:#ffbb12!important;border-color:#ffbb12!important;color:#102f54!important}
div[class*="st-key-ir_04"] button{background:#e82d70!important;border-color:#e82d70!important;color:white!important}
div[class*="st-key-ir_01"] button,div[class*="st-key-ir_02"] button,div[class*="st-key-ir_03"] button,div[class*="st-key-ir_04"] button{border-radius:30px!important;font-weight:750!important}
.mf-footer {border-top:1px solid #d9e4eb;padding-top:22px;margin-top:25px;color:#34516d;text-align:center}.mf-hero-title em {text-decoration:underline;text-decoration-color:#ffbd13;text-decoration-thickness:5px;text-underline-offset:9px}div[data-testid="stImage"] img {border-radius:20px}
@media(max-width:700px){.mf-hero-title{letter-spacing:-1px}.mf-art{min-height:240px}.mf-map{height:190px}}
</style>
""",unsafe_allow_html=True)
st.markdown('<div class="mf-brand">🏔️ Mi Futuro <em>Jujuy</em> <span style="font-size:.67rem;letter-spacing:2px;font-weight:600;color:#173c68"> EXPLORÁ · CONOCÉ · ELEGÍ</span></div>',unsafe_allow_html=True)
opciones_nav=["🏠 Inicio","🧭 Explorá","📊 Mis intereses","🎓 Buscá carreras","📍 Mapa"]
if "mf_nav" not in st.session_state:
    st.session_state.mf_nav="🏠 Inicio"
# Cambiar la navegación solo antes de instanciar el widget: evita
# StreamlitWidgetAlreadyInstantiatedError al usar los botones de acceso.
if "mf_nav_pendiente" in st.session_state:
    st.session_state.mf_nav = st.session_state.pop("mf_nav_pendiente")
seleccion_nav=st.segmented_control("Secciones",opciones_nav,key="mf_nav",label_visibility="collapsed")
if seleccion_nav is None:
    seleccion_nav="🏠 Inicio"

if seleccion_nav=="🏠 Inicio":
    izquierda,derecha=st.columns([1,1.1],gap="large",vertical_alignment="center")
    with izquierda:
        st.markdown('<div class="mf-eyebrow">ORIENTACIÓN EDUCATIVA EN JUJUY</div><div class="mf-hero-title">Tu futuro comienza<br>con un <em>clic.</em></div><p class="mf-intro">Descubrí carreras, explorá tus intereses y conocé todo lo que Jujuy tiene para ofrecerte.</p>',unsafe_allow_html=True)
    with derecha:
        # La imagen se carga como recurso local para mantener los botones y textos accesibles.
        portada_imagen = Path(__file__).with_name("jujuy_portada.webp")
        if portada_imagen.exists():
            st.image(str(portada_imagen), use_container_width=True)
        else:
            st.markdown('<div class="mf-art"><div class="mf-map"></div></div>', unsafe_allow_html=True)
    st.write("")
    tarjetas=[
        ("01","🧭","Explorá","Descubrí los distintos campos de formación, actividades y perfiles profesionales.","Explorar áreas","🧭 Explorá","#e8f9f5","#007b80"),
        ("02","📊","Mis intereses","Respondé un cuestionario y descubrí cuáles son tus áreas de mayor interés.","Iniciar test","📊 Mis intereses","#e6f2ff","#0961d5"),
        ("03","🎓","Buscá carreras","Explorá carreras, instituciones y sedes disponibles en Jujuy. Usá filtros según tus intereses.","Buscar carreras","🎓 Buscá carreras","#fff6df","#b17b00"),
        ("04","📍","Mapa de instituciones","Ubicá las instituciones de educación superior de Jujuy y conocé sus sedes.","Ver mapa","📍 Mapa","#fff0f4","#bf2f62")
    ]
    cols=st.columns(4,gap="medium")
    for col,(numero,icono,titulo,descripcion,boton,destino,fondo,color) in zip(cols,tarjetas):
        with col:
            st.markdown(f'<div class="mf-card" style="background:{fondo}"><span style="display:inline-flex;align-items:center;justify-content:center;width:43px;height:43px;border-radius:50%;background:{color};color:white;font-size:1.22rem;font-weight:850;letter-spacing:.5px;box-shadow:0 3px 8px #18334c1a">{numero}</span><div class="mf-icon">{icono}</div><h3>{titulo}</h3><p>{descripcion}</p></div>',unsafe_allow_html=True)
            if st.button(boton+" →",key="ir_"+numero,use_container_width=True,type="primary"):
                st.session_state.mf_nav_pendiente = destino
                st.rerun()
    st.markdown('<div class="mf-footer">🎓 Oferta educativa de Jujuy &nbsp; · &nbsp; 🛡️ Información orientativa &nbsp; · &nbsp; 💙 Tu futuro importa</div>',unsafe_allow_html=True)

if seleccion_nav=="🧭 Explorá":
    st.header("🧭 Explorá áreas de estudio")
    st.write("Conocé los distintos campos de formación y descubrí cuáles despiertan tu curiosidad.")
    campos={
        "💻 Tecnología e informática":"Programación, ingeniería informática, software, sistemas, ciencia de datos e inteligencia artificial.",
        "🏗️ Ingeniería, industria y construcción":"Diseño de estructuras, procesos industriales, materiales y soluciones técnicas.",
        "📐 Ciencias exactas":"Matemática, física, química, modelos y resolución de problemas científicos.",
        "🌿 Ciencias naturales y ambiente":"Biología, geología, ecosistemas, biodiversidad y cuidado ambiental.",
        "🌾 Producción agropecuaria y alimentaria":"Agricultura, ganadería, actividad forestal, producción y calidad de alimentos.",
        "🩺 Salud y bienestar":"Cuidado de la salud, prevención y acompañamiento a las personas.",
        "📚 Educación y enseñanza":"Formación docente, enseñanza, aprendizaje, inclusión y profesorados de diferentes disciplinas.",
        "🗣️ Lenguas, literatura y escritura":"Inglés, francés, portugués, letras, lectura, escritura y edición.",
        "🏛️ Filosofía, historia y antropología":"Pensamiento filosófico, procesos históricos, culturas y formas de vida.",
        "⚖️ Derecho, política y sociedad":"Leyes, Estado, políticas públicas, trabajo social y acompañamiento a niños, adolescentes y familias.",
        "📢 Comunicación y medios":"Periodismo, comunicación social, medios digitales y producción de contenidos.",
        "🎨 Arte, diseño y creatividad":"Artes visuales, música, teatro, danza y diseño creativo.",
        "📊 Economía, administración y gestión":"Organización, gestión, finanzas, economía y emprendimientos.",
        "🧳 Turismo, gastronomía y patrimonio":"Turismo, patrimonio cultural, cocina regional y experiencias para visitantes."
    }
    lista_campos = list(campos.items())
    for inicio in range(0, len(lista_campos), 3):
        columnas = st.columns(3, gap="small")
        for columna, (nombre, descripcion) in zip(columnas, lista_campos[inicio:inicio + 3]):
            with columna:
                with st.expander(nombre):
                    st.write(descripcion)
    if st.button("Descubrir mis intereses →",type="primary",key="explora_a_intereses"):
        st.session_state.mf_nav_pendiente = "📊 Mis intereses"
        st.rerun()

if seleccion_nav=="📍 Mapa":
    st.subheader("🗺️ Mapa interactivo de Jujuy por departamento")
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
    @st.cache_data(ttl=86400, show_spinner=False)
    def load_official_jujuy_boundaries():
        """Usa geometrías departamentales de Georef; nunca altera límites a mano."""
        from urllib.request import Request, urlopen
        from urllib.parse import urlencode
        import unicodedata

        params = urlencode({
            "provincia": "jujuy", "max": 16,
            "formato": "geojson", "campos": "nombre,geometria"
        })
        # Compatibilidad con las dos rutas publicadas del servicio Georef.
        urls = [
            "https://apis.datos.gob.ar/georef/api/v2.0/departamentos?" + params,
            "https://apis.datos.gob.ar/georef/api/departamentos?" + params,
        ]
        data = None
        last_error = None
        for url in urls:
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0 MiFuturoJujuy/1.0"})
                with urlopen(req, timeout=8) as response:
                    candidate = json.load(response)
                if candidate.get("type") == "FeatureCollection":
                    data = candidate
                    break
            except Exception as exc:
                last_error = exc
        if data is None:
            raise RuntimeError("No se pudo descargar el GeoJSON oficial") from last_error
        if data.get("type") != "FeatureCollection":
            raise ValueError("Georef no devolvió una colección GeoJSON")
        colors = {
            "YAVI": "#F4A261", "RINCONADA": "#7BC8A4",
            "COCHINOCA": "#B7A4EA", "SANTA CATALINA": "#F7D774"
        }
        def key(value):
            value = unicodedata.normalize("NFKD", str(value).upper())
            return "".join(ch for ch in value if not unicodedata.combining(ch))
        expected = set(dept_towns)
        for feature in data["features"]:
            props = feature.get("properties") or {}
            name = key(props.get("nombre", props.get("departamento", "")))
            if name == "DR MANUEL BELGRANO":
                name = "DOCTOR MANUEL BELGRANO"
            if name not in expected:
                raise ValueError("Departamento no reconocido: " + name)
            props["departamento"] = name
            props["color"] = colors.get(name, "#A9D8E6")
            feature["properties"] = props
            if feature.get("geometry", {}).get("type") not in ("Polygon", "MultiPolygon"):
                raise ValueError("Geometría no válida para " + name)
        if len(data["features"]) != 16 or {f["properties"]["departamento"] for f in data["features"]} != expected:
            raise ValueError("La respuesta oficial no incluye los 16 departamentos")
        return data

    geo_path = Path(__file__).with_name("departamentos_jujuy.geojson")
    if "dept_choice" not in st.session_state:
        st.session_state.dept_choice = "Todos"
    if "last_map_click" not in st.session_state:
        st.session_state.last_map_click = None

    selected_department = st.session_state.dept_choice
    if geo_path.exists():
        try:
            boundaries = load_official_jujuy_boundaries()
        except Exception:
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
                         else "#344054",
                "weight": 4 if feature["properties"]["departamento"] == selected_department else 2.2,
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
            geometry = feature["geometry"]
            if geometry["type"] == "MultiPolygon":
                ring = max((polygon[0] for polygon in geometry["coordinates"]), key=len)
            else:
                ring = geometry["coordinates"][0]
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
                interactive=False,
            ).add_to(m)
        m.fit_bounds([[-24.65, -67.3], [-21.7, -64.0]])
        event = st_folium(
            m, height=620, use_container_width=True,
            returned_objects=["last_active_drawing", "last_object_clicked_tooltip"],
            key="mapa_departamentos"
        )
        # Priorizar la propiedad del polígono realmente pulsado: funciona
        # también en departamentos pequeños como El Carmen, Palpalá y San Antonio.
        drawing = (event or {}).get("last_active_drawing") or {}
        props = drawing.get("properties") or {}
        matched = str(props.get("departamento", "")).upper().strip()
        clicked = (event or {}).get("last_object_clicked_tooltip")
        if matched not in dept_names and clicked:
            import unicodedata
            raw = unicodedata.normalize("NFKD", str(clicked).upper())
            raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
            matched = next((name for name in sorted(dept_names, key=len, reverse=True)
                            if name in raw), "")
        if matched in dept_names and matched != selected_department:
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
        st.caption("Los profesorados se mantienen como opciones de formación; la apertura de nuevos ingresos debe confirmarse con cada IES. Las tecnicaturas pueden cambiar según la cohorte: aunque sigan en el catálogo, verificá su continuidad, sede y convocatoria.")
        kind_order = ["Profesorados", "Tecnicaturas", "Ingenierías", "Licenciaturas", "Otras formaciones"]
        for locality, locality_group in filtered.groupby(town, sort=True):
            st.markdown(f"#### 📍 {locality}")
            locality_group = locality_group.copy()
            locality_group["_tipo_grupo"] = locality_group.apply(career_kind, axis=1)
            for kind in kind_order:
                grouped = locality_group[locality_group["_tipo_grupo"] == kind]
                if grouped.empty:
                    continue
                titulo_grupo = "Más carreras" if kind == "Otras formaciones" else kind
                st.markdown(f"**{titulo_grupo} ({len(grouped)})**")
                for _, item in grouped.sort_values(career).iterrows():
                    with st.container(border=True):
                        st.markdown(f"**🎓 {item[career]}**")
                        tipo_formacion = visible_value(item.get("Tipo de formación", ""))
                        if tipo_formacion:
                            st.caption(f"📚 Tipo de formación: {tipo_formacion}")
                        duracion = duracion_visible(item)
                        if duracion:
                            st.caption(f"⏳ Duración: {duracion}")
                        titulo_otorgado = visible_value(item.get("Título otorgado", ""))
                        if titulo_otorgado:
                            st.caption(f"🎓 Título: {titulo_otorgado}")
                        modalidad = modalidad_visible(item)
                        if modalidad:
                            st.caption(f"🧑‍🏫 Modalidad de cursado: {modalidad}")
                        aviso = alcance_sede_visible(item)
                        if aviso:
                            st.caption(f"ℹ️ {aviso}")
                        institucion = visible_value(item.get("Institución", ""))
                        if institucion:
                            st.caption(f"🏫 {institucion}")
                        facultad = visible_value(item.get("Unidad académica", "")) or visible_value(item.get("Facultad", ""))
                        if facultad:
                            st.caption(f"🏛️ {facultad}")
                        sede = visible_value(item.get("Sede de cursado confirmada", ""))
                        if not sede:
                            sede = visible_value(item.get("Lugar donde se dicta", ""))
                        if sede:
                            st.caption(f"📍 Sede: {sede}")
                        mostrar_informacion_y_contacto(item)
                        mostrar_ingreso_2027(item)
                        area = visible_value(item.get("Área principal preliminar", ""))
                        if area:
                            st.caption(f"Área: {area}")
        with st.expander("Ver tabla completa de registros"):
            results(filtered)
if seleccion_nav=="🎓 Buscá carreras":
    st.markdown("### 🔎 Encontrá tu carrera")
    st.caption("Buscá por nombre, institución o área de interés y descubrí dónde estudiar en Jujuy.")
    col_busqueda, col_localidad = st.columns([2, 1], gap="medium")
    with col_busqueda:
        q = st.text_input("¿Qué te gustaría estudiar?", placeholder="Ej.: Matemática, Enfermería, Programación…", key="busqueda_carrera")
    with col_localidad:
        loc = st.selectbox("📍 Localidad", ["Todas las localidades"] + towns, key="searchloc")
    tipos = sorted(t for t in df["Tipo de formación"].unique() if visible_value(t))
    tipo = st.selectbox("🎓 Tipo de formación", ["Todas las formaciones"] + tipos, key="searchtipo")
    subset = df.copy()
    if loc != "Todas las localidades":
        subset = subset[subset[town] == loc]
    if tipo != "Todas las formaciones":
        subset = subset[subset["Tipo de formación"] == tipo]
    if q.strip():
        consulta = normalize(q.strip())
        subset = subset[subset.apply(lambda row: consulta in normalize(" ".join(map(str, row.values))), axis=1)]
    st.markdown(f"**{len(subset)} opciones encontradas**")
    st.caption("Catálogo orientativo: los profesorados pueden continuar aunque no haya ingreso abierto. Para tecnicaturas, confirmá la continuidad de la próxima cohorte, la sede y la inscripción.")
    if subset.empty:
        st.info("No encontramos coincidencias. Probá otra palabra o seleccioná «Todas las localidades».")
    else:
        for _, carrera_row in subset.iterrows():
            nombre = visible_value(carrera_row.get(career, ""))
            institucion = visible_value(carrera_row.get("Institución", ""))
            localidad = visible_value(carrera_row.get(town, ""))
            formacion = visible_value(carrera_row.get("Tipo de formación", ""))
            area = visible_value(carrera_row.get("Área principal preliminar", ""))
            sede = visible_value(carrera_row.get("Sede de cursado confirmada", ""))
            if not sede:
                sede = visible_value(carrera_row.get("Lugar donde se dicta", ""))
            aviso = alcance_sede_visible(carrera_row)
            with st.container(border=True):
                if nombre:
                    st.markdown(f"#### 🎓 {nombre}")
                duracion = duracion_visible(carrera_row)
                if duracion:
                    st.write(f"⏳ **Duración:** {duracion}")
                titulo_otorgado = visible_value(carrera_row.get("Título otorgado", ""))
                if titulo_otorgado:
                    st.write(f"🎓 **Título:** {titulo_otorgado}")
                modalidad = modalidad_visible(carrera_row)
                if modalidad:
                    st.write(f"🧑‍🏫 **Modalidad de cursado:** {modalidad}")
                if formacion or area:
                    complemento = f"{formacion} · {area}" if formacion and area else formacion or area
                    st.caption(f"📘 {complemento}")
                if institucion:
                    st.write(f"🏫 **Institución:** {institucion}")
                unidad = visible_value(carrera_row.get("Unidad académica", "")) or visible_value(carrera_row.get("Facultad", ""))
                if unidad:
                    st.write(f"🏛️ **Unidad académica:** {unidad}")
                if localidad:
                    st.write(f"📍 **Localidad:** {localidad}")
                if sede:
                    st.write(f"🏢 **Sede de cursado:** {sede}")
                mostrar_informacion_y_contacto(carrera_row)
                mostrar_ingreso_2027(carrera_row)
                if aviso:
                    st.caption(f"ℹ️ {aviso}")
if seleccion_nav=="📊 Mis intereses":
    st.subheader("🧭 Descubrí tus intereses")
    st.write("Explorá actividades vinculadas con distintas áreas de estudio y trabajo. No necesitás saber hacerlas: respondé según lo que te gustaría conocer o realizar.")
    st.caption("Cuestionario educativo exploratorio. No es una prueba psicométrica validada ni determina qué carrera debés elegir.")

    areas = {
        "Tecnología e informática": [
            "Crear aplicaciones, páginas web o programas para resolver problemas.",
            "Configurar equipos o redes y resolver problemas técnicos.",
            "Usar datos o inteligencia artificial para encontrar soluciones."
        ],
        "Ingeniería, industria y construcción": [
            "Diseñar edificios, estructuras o máquinas.",
            "Mejorar procesos de fabricación para aprovechar mejor los materiales y la energía.",
            "Planificar el mantenimiento de máquinas y equipos industriales."
        ],
        "Ciencias exactas": [
            "Resolver problemas matemáticos mediante cálculos y razonamiento lógico.",
            "Investigar fenómenos físicos, como el movimiento, la materia o la energía.",
            "Analizar datos y usar modelos matemáticos para explicar situaciones."
        ],
        "Ciencias naturales y ambiente": [
            "Investigar cómo se relacionan los seres vivos con los ecosistemas donde habitan.",
            "Analizar problemas ambientales y proponer formas de cuidar los recursos naturales.",
            "Tomar muestras de agua, suelo o aire para estudiar sus características."
        ],
        "Producción agropecuaria y alimentaria": [
            "Participar en el cultivo de plantas y la producción de alimentos.",
            "Mejorar la crianza de animales o el aprovechamiento del suelo y los bosques.",
            "Controlar la calidad y participar en la elaboración de productos alimenticios."
        ],
        "Salud y bienestar": [
            "Identificar riesgos en los espacios de trabajo y proponer medidas para prevenir accidentes y cuidar la salud.",
            "Comprender cómo funciona el cuerpo humano.",
            "Acompañar a otras personas en el cuidado de su salud."
        ],
        "Educación y enseñanza": [
            "Explicar un tema para ayudar a otra persona a comprenderlo.",
            "Diseñar actividades o materiales para enseñar.",
            "Buscar distintas maneras de acompañar el aprendizaje de cada estudiante."
        ],
        "Lenguas, literatura y escritura": [
            "Aprender otros idiomas y conocer las culturas de quienes los hablan.",
            "Leer, interpretar o escribir cuentos, poemas y otros textos.",
            "Investigar cómo se forman las lenguas y cómo cambian con el tiempo."
        ],
        "Filosofía, historia y antropología": [
            "Debatir preguntas sobre la libertad, la justicia o el sentido de la vida.",
            "Investigar hechos del pasado y comprender sus consecuencias en la actualidad.",
            "Conocer cómo viven, piensan y se organizan distintas comunidades."
        ],
        "Derecho, política y sociedad": [
            "Analizar leyes y comprender cómo se aplican en distintas situaciones.",
            "Estudiar cómo funciona el Estado y cómo se toman las decisiones políticas.",
            "Participar en proyectos que busquen resolver problemas de una comunidad."
        ],
        "Comunicación y medios": [
            "Investigar hechos de actualidad y comunicar información al público.",
            "Producir contenidos para radio, redes sociales o medios digitales.",
            "Diseñar campañas para difundir ideas o promover temas de interés social."
        ],
        "Arte, diseño y creatividad": [
            "Crear dibujos, imágenes o diseños para comunicar una idea.",
            "Participar en proyectos de música, teatro, danza o artes visuales.",
            "Usar herramientas digitales para crear propuestas visuales, sonoras o interactivas."
        ],
        "Economía, administración y gestión": [
            "Organizar el presupuesto y los recursos de un emprendimiento.",
            "Analizar cómo se producen y distribuyen los bienes y servicios.",
            "Planificar y coordinar las actividades de una organización."
        ],
        "Turismo, gastronomía y patrimonio": [
            "Diseñar recorridos para dar a conocer lugares de Jujuy.",
            "Preparar comidas tradicionales y conocer la historia de sus ingredientes.",
            "Organizar actividades culturales y recibir a visitantes."
        ]
    }
    def _normalizar_interes(texto):
        return "".join(letra for letra in unicodedata.normalize("NFKD", str(texto).casefold()) if not unicodedata.combining(letra))

    def _afinidades_carrera(nombre):
        n = _normalizar_interes(nombre)
        etiquetas = set()
        def agregar(area, *palabras):
            if any(p in n for p in palabras):
                etiquetas.add(area)
        agregar("Tecnología e informática", "informatica", "software", "programacion", "programador", "sistemas", "datos", "inteligencia artificial", "videojuegos", "soporte de infraestructura", "infraestructura de tecnologia de la informacion")
        agregar("Ingeniería, industria y construcción", "ingenieria quimica", "ingenieria industrial", "ingenieria de minas", "perforacion", "arquitectura", "construccion", "higiene y seguridad", "mantenimiento industrial", "energias renovables")
        agregar("Ciencias exactas", "matematica", "fisica", "quimica", "geolog")
        agregar("Ciencias naturales y ambiente", "biolog", "ambient", "forestal", "agronom", "geolog", "ecolog", "desarrollo rural")
        agregar("Producción agropecuaria y alimentaria", "agro", "alimento", "bromatolog", "granja", "forestal", "agricola", "cocina regional", "desarrollo rural")
        agregar("Salud y bienestar", "medicina", "enfermer", "salud", "seguridad e higiene")
        agregar("Educación y enseñanza", "profesorado", "educacion", "docencia", "formacion docente")
        agregar("Lenguas, literatura y escritura", "ingles", "frances", "portugues", "letras", "literatura", "editorial", "lengua")
        agregar("Filosofía, historia y antropología", "filosofia", "historia", "antropolog")
        agregar("Derecho, política y sociedad", "abogac", "derecho", "politic", "trabajo social", "ninez", "adolescencia", "familia")
        agregar("Comunicación y medios", "comunicacion", "periodismo", "medios", "editorial")
        agregar("Arte, diseño y creatividad", "arte", "artistic", "diseno", "musica", "teatro", "danza", "videojuegos")
        agregar("Economía, administración y gestión", "administracion", "contador", "economia", "gestion empresarial")
        agregar("Turismo, gastronomía y patrimonio", "turismo", "gastronom", "cocina", "cultura alimentaria")
        if "ingenieria informatica" in n:
            etiquetas.add("Ingeniería, industria y construcción")
        if "economia politica" in n:
            etiquetas.add("Derecho, política y sociedad")
        if "tecnologia de los alimentos" in n or "tecnologias de los alimentos" in n:
            etiquetas.add("Ingeniería, industria y construcción")
        return etiquetas

    questions = [(area, i, pregunta) for i in range(3) for area, preguntas in areas.items() for pregunta in [preguntas[i]]]
    opciones = ["1 — Nada", "2 — Poco", "3 — Bastante", "4 — Mucho", "No estoy seguro/a"]
    puntajes = {"1 — Nada": 1, "2 — Poco": 2, "3 — Bastante": 3, "4 — Mucho": 4, "No estoy seguro/a": 0}
    version = "intereses_v5_4niveles_tarjetas"
    if st.session_state.get("intereses_version") != version:
        st.session_state.intereses_version = version
        st.session_state.intereses_paso = 0
        st.session_state.intereses_respuestas = {}
        st.session_state.intereses_finalizado = False
    if st.session_state.intereses_finalizado:
        if st.button("↻ Volver a realizar la exploración", key="reiniciar_intereses"):
            st.session_state.intereses_paso = 0
            st.session_state.intereses_respuestas = {}
            st.session_state.intereses_finalizado = False
            st.session_state.pop("intereses_area_carreras", None)
            st.session_state.encuesta_mi_futuro_enviada = False
            st.session_state.encuesta_enviando = False
            st.session_state.encuesta_payload = None
            st.session_state.encuesta_error = ""
            st.session_state.pop("encuesta_submission_id", None)
            for k in ("encuesta_edad", "encuesta_carrera_encontrada", "encuesta_carrera_faltante", "encuesta_mejoras"):
                st.session_state.pop(k, None)
            for k in list(st.session_state.keys()):
                if k.startswith(("intereses_opcion_v2_", "intereses_opcion_v3_", "intereses_opcion_v4_", "intereses_opcion_v5_")):
                    del st.session_state[k]
            st.rerun()
    else:
        st.info("Leé cada actividad e indicá cuánto te interesaría realizarla. No hay respuestas correctas o incorrectas. «No estoy seguro/a» no se incluye en el puntaje.")
        paso = st.session_state.intereses_paso
        area_actual, indice_actual, actividad = questions[paso]
        st.markdown(f"**Pregunta {paso + 1} de {len(questions)}**")
        st.progress((paso + 1) / len(questions))
        st.markdown(f"### {actividad}")
        st.caption("¿Cuánto te interesaría realizar esta actividad?")
        clave = f"intereses_opcion_v5_{paso}"
        if clave not in st.session_state and paso in st.session_state.intereses_respuestas:
            st.session_state[clave] = st.session_state.intereses_respuestas[paso]
        st.markdown("""
        <style>
        .st-key-intereses_respuesta_visual [data-testid="column"] {
            border: 1px solid #d9e4e1;
            border-radius: 16px;
            padding: .55rem .45rem .35rem;
            background: #ffffff;
            transition: background .16s ease, border-color .16s ease, box-shadow .16s ease;
        }
        .st-key-intereses_respuesta_visual [data-testid="column"]:hover {
            border-color: #13877d;
            background: #f3faf8;
        }
        .st-key-intereses_respuesta_visual [data-testid="column"]:has(button[kind="primary"]) {
            background: linear-gradient(145deg, #126d65, #159286);
            border-color: #126d65;
            box-shadow: 0 7px 18px rgba(18, 109, 101, .24);
        }
        .st-key-intereses_respuesta_visual .numero-respuesta {
            min-height: 2.4rem;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #183b38;
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1;
        }
        .st-key-intereses_respuesta_visual [data-testid="column"]:has(button[kind="primary"]) .numero-respuesta {
            color: #ffffff;
        }
        .st-key-intereses_respuesta_visual [data-testid="stButton"] > button {
            min-height: 3rem;
            border-radius: 11px;
            font-weight: 700;
            white-space: normal;
            line-height: 1.2;
            border-color: transparent;
            background: transparent;
            color: #183b38;
            padding: .4rem .25rem;
        }
        .st-key-intereses_respuesta_visual [data-testid="column"]:has(button[kind="primary"]) [data-testid="stButton"] > button {
            color: #ffffff !important;
            background: transparent !important;
            border-color: transparent !important;
        }
        .st-key-intereses_respuesta_visual [data-testid="column"]:has(button[kind="primary"]) [data-testid="stButton"] > button:hover {
            color: #ffffff !important;
            background: rgba(255, 255, 255, .12) !important;
        }
        @media (max-width: 700px) {
            .st-key-intereses_respuesta_visual [data-testid="column"] {
                padding: .35rem .25rem .25rem;
            }
            .st-key-intereses_respuesta_visual [data-testid="stButton"] > button {
                font-size: .85rem;
            }
        }
        </style>
        """, unsafe_allow_html=True)
        with st.container(key="intereses_respuesta_visual"):
            columnas_respuestas = st.columns(len(opciones), gap="small")
            for indice_opcion, opcion in enumerate(opciones):
                with columnas_respuestas[indice_opcion]:
                    seleccionada = st.session_state.get(clave) == opcion
                    if " — " in opcion:
                        numero, etiqueta = opcion.split(" — ", 1)
                    else:
                        numero, etiqueta = "", opcion
                    st.markdown(
                        f'<div class="numero-respuesta">{numero or "&nbsp;"}</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        etiqueta,
                        key=f"intereses_respuesta_card_{paso}_{indice_opcion}",
                        type="primary" if seleccionada else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state[clave] = opcion
                        st.session_state.intereses_respuestas[paso] = opcion
                        st.rerun()
            seleccion = st.session_state.get(clave)
        if seleccion is not None:
            st.session_state.intereses_respuestas[paso] = seleccion
        col_anterior, col_siguiente = st.columns(2)
        with col_anterior:
            if st.button("← Anterior", disabled=paso == 0, use_container_width=True, key="intereses_anterior"):
                st.session_state.intereses_paso -= 1
                st.rerun()
        with col_siguiente:
            texto = "Ver mis resultados ✓" if paso == len(questions) - 1 else "Siguiente →"
            if st.button(texto, type="primary", use_container_width=True, key="intereses_siguiente"):
                if seleccion is None:
                    st.warning("Seleccioná una opción para continuar.")
                elif paso < len(questions) - 1:
                    st.session_state.intereses_paso += 1
                    st.rerun()
                else:
                    st.session_state.intereses_finalizado = True
                    st.rerun()
    if st.session_state.intereses_finalizado:
        respuestas = {(area, i): st.session_state.intereses_respuestas.get(paso) for paso, (area, i, _) in enumerate(questions)}
        if any(x is None for x in respuestas.values()):
            st.warning("Respondé todas las preguntas para ver tus resultados.")
        else:
            resultados = {}
            for area, preguntas in areas.items():
                elegidas = [respuestas[(area, i)] for i in range(len(preguntas))]
                validas = [puntajes[x] for x in elegidas if x in puntajes and puntajes[x] > 0]
                resultados[area] = sum(validas) / len(validas) if validas else None
            orden = sorted((a for a in areas if resultados[a] is not None), key=lambda a: resultados[a], reverse=True)
            st.subheader("🌟 Tu perfil exploratorio")
            if orden:
                destacadas = orden[:3]
                st.write("Estas son las áreas en las que expresaste mayor interés. Un empate no significa que una sea más importante que otra.")
                fondos = ["#F0E8FF", "#E5F5F4", "#FFF1DB"]
                acentos = ["#6D35B5", "#087C79", "#A66312"]
                iconos_areas = {
                    "Tecnología e informática": "💻",
                    "Ingeniería, industria y construcción": "🏗️",
                    "Ciencias exactas": "🧮",
                    "Ciencias naturales y ambiente": "🌿",
                    "Producción agropecuaria y alimentaria": "🌾",
                    "Salud y bienestar": "🩺",
                    "Educación y enseñanza": "📚",
                    "Lenguas, literatura y escritura": "📖",
                    "Filosofía, historia y antropología": "🏺",
                    "Derecho, política y sociedad": "⚖️",
                    "Comunicación y medios": "🎙️",
                    "Arte, diseño y creatividad": "🎨",
                    "Economía, administración y gestión": "📊",
                    "Turismo, gastronomía y patrimonio": "🧭",
                }
                columnas_podio = st.columns(len(destacadas))
                for pos, (columna_podio, area) in enumerate(zip(columnas_podio, destacadas), 1):
                    empate = pos > 1 and resultados[area] == resultados[destacadas[pos - 2]]
                    titulo = f"{pos}° área destacada · mismo interés que la anterior" if empate else f"{pos}° lugar"
                    with columna_podio:
                        st.markdown(
                            f"""<div style="min-height:205px;background:linear-gradient(145deg,{fondos[pos-1]},#ffffff);border:1px solid {acentos[pos-1]}33;border-top:5px solid {acentos[pos-1]};border-radius:18px;padding:20px 18px;margin:8px 0;box-shadow:0 8px 22px rgba(29,45,75,.08);">
                            <div style="font-size:34px;line-height:1.1;">{iconos_areas.get(area, "✨")}</div>
                            <div style="color:{acentos[pos-1]};font-size:16px;font-weight:800;margin-top:10px;">{titulo}</div>
                            <div style="color:#20242c;font-size:20px;font-weight:750;margin:6px 0 10px;">{area}</div>
                            <div style="color:#414852;font-size:14px;">Interés promedio: {resultados[area]:.1f} de 4</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        if st.button("🎓 Ver carreras", key=f"ver_carreras_resultado_{pos}", use_container_width=True):
                            st.session_state["intereses_area_carreras"] = area

                area_carreras_seleccionada = st.session_state.get("intereses_area_carreras")
                if area_carreras_seleccionada in destacadas:
                    st.markdown(f"### 🎓 Carreras vinculadas con {area_carreras_seleccionada}")
                    st.caption("Explorá las carreras relacionadas con esta área. Una carrera puede vincularse con más de un campo. Verificá la oferta, las sedes y los requisitos de ingreso.")
                    coinciden = df[df[career].fillna("").astype(str).map(
                        lambda nombre: area_carreras_seleccionada in _afinidades_carrera(nombre)
                    )]
                    if coinciden.empty:
                        st.info("Todavía no hay carreras asociadas a esta área en los registros disponibles.")
                    else:
                        columnas = [career, town, "Institución"]
                        coinciden = coinciden[columnas].drop_duplicates()
                        st.dataframe(coinciden, hide_index=True, use_container_width=True)
                    st.caption("Algunos profesorados universitarios requieren estudios previos; no todas las carreras son de ingreso directo desde la secundaria.")
                    if st.button("↑ Volver al podio", key="cerrar_carreras_resultado"):
                        st.session_state.pop("intereses_area_carreras", None)
                        st.rerun()
                st.caption("También podés abrir el botón de cada área para consultar sus carreras.")
            else:
                st.info("Aún no hay respuestas suficientes para destacar áreas. Podés explorar las carreras disponibles y volver a intentarlo cuando tengas más información.")
            st.caption("Este resultado es orientativo, no mide capacidades ni determina qué estudiar.")

            st.markdown("""
            <style>
            .st-key-encuesta_visual {
                background: linear-gradient(135deg, #f3eaff 0%, #e6f7f5 58%, #fff5df 100%);
                border: 1px solid #d9c7f4;
                border-radius: 22px;
                padding: 1.25rem 1.4rem;
                box-shadow: 0 10px 28px rgba(57, 48, 103, 0.09);
            }
            .st-key-encuesta_visual [data-testid="stWidgetLabel"] p {
                color: #17345f;
                font-weight: 650;
            }
            .st-key-encuesta_visual button[kind="primary"] {
                background: linear-gradient(90deg, #7138c8, #078b87);
                color: white;
                border: 0;
                border-radius: 12px;
                font-weight: 750;
                min-height: 3rem;
            }
            .st-key-encuesta_visual button[kind="primary"]:hover {
                background: linear-gradient(90deg, #5925a7, #066b68);
                color: white;
            }
            @media (max-width: 640px) {
                .st-key-encuesta_visual { padding: .75rem; }
            }
            </style>
            """, unsafe_allow_html=True)
            with st.container(key="encuesta_visual", border=True):
                st.markdown("""
                <div style="display:flex;align-items:center;justify-content:space-between;gap:20px;padding:8px 4px 14px;">
                    <div>
                        <span style="display:inline-block;background:#ffffffb8;color:#6531ad;border-radius:999px;padding:6px 12px;font-size:12px;font-weight:800;letter-spacing:.08em;">TU EXPERIENCIA CUENTA</span>
                        <h2 style="color:#17345f;margin:12px 0 6px;font-size:30px;">Ayudanos a mejorar Mi Futuro Jujuy</h2>
                        <p style="color:#40516c;margin:0;font-size:16px;">Tu opinión ayuda a que más jóvenes encuentren información útil para pensar su futuro.</p>
                    </div>
                    <div aria-hidden="true" style="flex:0 0 112px;width:112px;height:112px;border-radius:32px;background:linear-gradient(145deg,#7138c8,#08a39a);display:flex;align-items:center;justify-content:center;font-size:56px;box-shadow:0 12px 24px rgba(71,49,139,.2);">💬</div>
                </div>
                """, unsafe_allow_html=True)
                st.caption("Completá estas preguntas breves al terminar la exploración.")
                if st.session_state.get("encuesta_mi_futuro_enviada"):
                    st.success("¡Gracias! Tu respuesta quedó registrada.")
                else:
                    edad = st.number_input(
                        "¿Qué edad tenés?",
                        min_value=10,
                        max_value=99,
                        value=None,
                        step=1,
                        help="Escribí solo tu edad en números. No se admiten letras.",
                        key="encuesta_edad",
                    )
                    carrera_encontrada = st.radio(
                        "¿Encontraste en la app la carrera que te interesa?",
                        ["Sí", "No"],
                        index=None,
                        horizontal=True,
                        key="encuesta_carrera_encontrada",
                    )
                    carrera_faltante = ""
                    if carrera_encontrada == "No":
                        carrera_faltante = st.text_input(
                            "¿Qué carrera buscabas y no encontraste?",
                            key="encuesta_carrera_faltante",
                        ).strip()
                    mejoras = st.text_area(
                        "¿Qué mejorarías o agregarías en la app?",
                        key="encuesta_mejoras",
                        help="Esta respuesta es opcional.",
                        height=110,
                    )
                    def preparar_envio_encuesta():
                        edad_actual = st.session_state.get("encuesta_edad")
                        encontrada_actual = st.session_state.get("encuesta_carrera_encontrada")
                        faltante_actual = str(st.session_state.get("encuesta_carrera_faltante", "")).strip()
                        if edad_actual is None:
                            st.session_state.encuesta_error = "Ingresá tu edad usando solo números."
                            return
                        if encontrada_actual is None:
                            st.session_state.encuesta_error = "Indicá si encontraste la carrera que te interesa."
                            return
                        if encontrada_actual == "No" and not faltante_actual:
                            st.session_state.encuesta_error = "Contanos qué carrera buscabas y no encontraste."
                            return
                        st.session_state.encuesta_error = ""
                        st.session_state.encuesta_payload = {
                            "edad": int(edad_actual),
                            "carrera_encontrada": encontrada_actual,
                            "carrera_faltante": faltante_actual if encontrada_actual == "No" else "",
                            "mejoras": str(st.session_state.get("encuesta_mejoras", "")).strip(),
                        }
                        st.session_state.setdefault("encuesta_submission_id", uuid.uuid4().hex)
                        st.session_state.encuesta_enviando = True

                    if st.session_state.get("encuesta_error"):
                        st.warning(st.session_state.encuesta_error)
                    st.button(
                        "Enviando…" if st.session_state.get("encuesta_enviando") else "Enviar mi opinión",
                        type="primary",
                        key="enviar_encuesta_mi_futuro",
                        use_container_width=True,
                        disabled=st.session_state.get("encuesta_enviando", False),
                        on_click=preparar_envio_encuesta,
                    )

                    if st.session_state.get("encuesta_enviando"):
                        st.info("Enviando tu respuesta… Esperá a que aparezca la confirmación.")
                        try:
                            survey_webhook_url = str(st.secrets.get("survey_webhook_url", "")).strip()
                        except Exception:
                            survey_webhook_url = ""
                        if not survey_webhook_url:
                            st.session_state.encuesta_enviando = False
                            st.session_state.encuesta_payload = None
                            st.error("La encuesta está lista, pero falta conectar el envío a la hoja de respuestas.")
                        else:
                            try:
                                from urllib.request import Request
                                payload = dict(st.session_state.encuesta_payload)
                                payload["submission_id"] = st.session_state.encuesta_submission_id
                                cuerpo = json.dumps(payload).encode("utf-8")
                                solicitud = Request(
                                    survey_webhook_url,
                                    data=cuerpo,
                                    headers={"Content-Type": "application/json"},
                                    method="POST",
                                )
                                with st.spinner("Guardando tu respuesta…"):
                                    with urlopen(solicitud, timeout=30) as respuesta_webhook:
                                        resultado_webhook = json.loads(respuesta_webhook.read().decode("utf-8"))
                                if resultado_webhook.get("ok"):
                                    st.session_state.encuesta_mi_futuro_enviada = True
                                    st.session_state.encuesta_enviando = False
                                    st.session_state.encuesta_payload = None
                                    st.session_state.encuesta_error = ""
                                    st.rerun()
                                else:
                                    st.session_state.encuesta_enviando = False
                                    st.session_state.encuesta_payload = None
                                    st.error("No se pudo guardar la respuesta. Revisá los datos e intentá nuevamente.")
                            except Exception:
                                st.session_state.encuesta_enviando = False
                                st.session_state.encuesta_payload = None
                                st.error("No se pudo confirmar el envío. Podés volver a intentar; el mismo envío no se duplicará.")

st.divider()
st.caption("Mi Futuro Jujuy · Prototipo educativo · Información en revisión")
