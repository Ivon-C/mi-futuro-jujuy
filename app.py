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
st.warning("Prototipo: datos históricos sin verificar para 2026/2027. Confirmar carreras, sedes y gratuidad en las instituciones.")
FILE = Path(__file__).with_name("carreras.xlsx")
if not FILE.exists():
    st.error("Falta cargar el archivo carreras.xlsx en el repositorio. Descargá la base preliminar y subila con Add file > Upload files.")
    st.stop()
@st.cache_data
def load_data():
    return pd.read_excel(FILE, sheet_name="Carreras").fillna("")
df = load_data()
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
        st.dataframe(frame[["Institución",town,career,"Tipo de formación","Área principal preliminar"]], hide_index=True, use_container_width=True)
import re
import unicodedata

st.subheader("💬 Tu asistente de carreras")
st.write("Preguntame qué podés estudiar en una localidad de Jujuy o contame qué tema te interesa.")
st.caption("Consulto la base histórica de Mi Futuro Jujuy. No soy una IA generativa y no reemplazo a un orientador vocacional.")

def normalize(value):
    value = unicodedata.normalize("NFKD", str(value).casefold())
    return "".join(char for char in value if not unicodedata.combining(char))

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

def find_careers(message):
    q = normalize(message)
    selected_localities = [loc for loc in towns if normalize(loc) in q]
    subset = df[df[town].isin(selected_localities)] if selected_localities else df
    detected = []
    for name, keywords in topics.items():
        if any(word in q for word in keywords):
            detected.extend(keywords)
    words = [word for word in re.findall(r"[a-z]+", q) if len(word) >= 4 and word not in ignore]
    if selected_localities:
        for loc in selected_localities:
            words = [word for word in words if word not in normalize(loc).split()]
    searchable = subset[career].astype(str).map(normalize) + " " + subset["Área principal preliminar"].astype(str).map(normalize)
    if detected:
        found = subset[searchable.map(lambda value: any(word in value for word in detected))]
    elif words:
        found = subset[searchable.map(lambda value: any(word in value for word in words))]
    else:
        found = subset
    return found.drop_duplicates(subset=[career, town, "Institución"]), selected_localities


st.markdown("""<style>
[data-testid="stSidebar"] {display:none;}
.st-key-cifac_launcher {position:fixed;bottom:20px;right:22px;z-index:999999;width:auto!important;}
.st-key-cifac_launcher button[data-testid="stPopoverButton"] {background:#7138c8!important;color:white!important;border-radius:28px!important;border:2px solid white!important;box-shadow:0 5px 22px #0003!important;font-weight:700!important;padding:12px 22px!important;}
@media(max-width:600px){.st-key-cifac_launcher{bottom:12px;right:12px;}}
</style>""", unsafe_allow_html=True)
with st.container(key="cifac_launcher"):
    with st.popover("🤖 CIFAC · ¿Te ayudo?", use_container_width=False):
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
        st.caption("Preguntas para empezar:")
        suggestions = ["No sé qué estudiar, ¿me ayudás?", "Quiero buscar carreras por localidad", "Me interesa la tecnología, ¿qué opciones tengo?"]
        picked = None
        for index, example in enumerate(suggestions):
            if st.button(example, key=f"cifac_example_{index}", use_container_width=True):
                picked = example
        with st.form("cifac_chat_form", clear_on_submit=True):
            question = st.text_input("Tu pregunta", placeholder="Escribí tu consulta...", label_visibility="visible")
            submitted = st.form_submit_button("➤ Enviar", type="primary", use_container_width=True)
        message = picked or (question.strip() if submitted else None)
        if message:
            st.session_state.assistant_history.append({"role": "user", "content": message})
            normalized_message = normalize(message)
            wants_guidance = any(term in normalized_message for term in ["no se que estudiar", "no se que elegir", "no se que carrera", "estoy indeciso", "estoy indecisa"])
            wants_locality = "buscar carreras por localidad" in normalized_message
            if not wants_guidance and not wants_locality:
                found, selected_localities = find_careers(message)
            if wants_guidance:
                response = "¡Claro! 💜 No necesitás decidir ahora. Podés comenzar con el **test de intereses** en la pestaña 🧭 Intereses, o contarme qué actividades te gustan para explorar carreras relacionadas. ¿Qué preferís?"
            elif wants_locality:
                response = "¡Vamos a buscar! 📍 ¿En qué localidad de Jujuy te gustaría estudiar? Por ejemplo: Yuto, Fraile Pintado, Perico o San Salvador de Jujuy."
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
            st.session_state.assistant_history.append({"role": "assistant", "content": response})
            st.rerun()
        if st.button("🗑️ Borrar conversación", key="clear_cifac_chat"):
            st.session_state.assistant_history = []
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
        st.caption("Oferta histórica preliminar: confirmar vigencia, gratuidad y sede con cada institución.")
        for locality, locality_group in filtered.groupby(town, sort=True):
            st.markdown(f"#### 📍 {locality}")
            for _, item in locality_group.sort_values(career).iterrows():
                with st.container(border=True):
                    st.markdown(f"**🎓 {item[career]}**")
                    st.caption(f"🏫 {item['Institución']}")
                    st.caption(f"{item['Tipo de formación']} · {item['Área principal preliminar']}")
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
                        st.dataframe(matches[[career, town, "Institución"]].drop_duplicates().head(6), hide_index=True, use_container_width=True)
            else:
                st.info("Elegiste 'No estoy seguro/a' en todas las preguntas. Podés explorar actividades antes de decidir.")
            total_uncertain = sum(uncertainty.values())
            if total_uncertain:
                st.write(f"Marcaste 'No estoy seguro/a' en {total_uncertain} actividades. Es una oportunidad para conocerlas mejor.")
            st.caption("Los registros de carreras son históricos y deben verificarse con cada institución. Este resultado no determina qué estudiar.")

st.divider()
st.caption("Mi Futuro Jujuy · Prototipo educativo · Información en revisión")
