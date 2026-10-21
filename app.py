import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path

st.set_page_config(page_title="Mi Futuro Jujuy", page_icon="🎓", layout="wide")
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
tab_map,tab_search,tab_test,tab_chat=st.tabs(["🗺️ Mapa","🔎 Carreras","🧭 Intereses","💬 Asistente"])
with tab_map:
    chosen=st.selectbox("Elegí una localidad",["Todas"]+towns)
    st.caption("Los puntos marcan centros urbanos aproximados, no direcciones de instituciones.")
    m=folium.Map(location=[-23.9,-65.3],zoom_start=7)
    for loc, count in df[town].value_counts().items():
        if loc in coords:
            folium.CircleMarker(coords[loc],radius=7,tooltip=f"{loc}: {count} registros",popup=loc,color="#087f8c",fill=True).add_to(m)
    map_event = st_folium(
        m, height=520, use_container_width=True,
        returned_objects=["last_object_clicked_tooltip"], key="jujuy_map"
    )
    clicked = (map_event or {}).get("last_object_clicked_tooltip")
    clicked_town = next((loc for loc in towns if clicked and clicked.startswith(loc + ": ")), None)
    active_town = chosen if chosen != "Todas" else clicked_town
    if active_town:
        st.success(f"📍 {active_town}: {len(df[df[town] == active_town])} carreras registradas en la base preliminar.")
        st.caption("Para volver a ver todas las localidades, elegí otra localidad en el selector o hacé clic en otro marcador.")
    else:
        st.info("Hacé clic en uno de los círculos del mapa para ver las carreras de esa localidad.")
    results(df if not active_town else df[df[town] == active_town])
with tab_search:
    q=st.text_input("Buscá una carrera o palabra clave")
    loc=st.selectbox("Filtrar localidad",["Todas"]+towns,key="searchloc")
    subset=df if loc=="Todas" else df[df[town]==loc]
    if q:
        subset=subset[subset.apply(lambda row:q.casefold() in " ".join(map(str,row.values)).casefold(),axis=1)]
    results(subset)
with tab_test:
    st.subheader("Cuestionario exploratorio de intereses")
    st.info("Ejercicio orientativo, no es un test vocacional validado.")
    areas={
        "Tecnología e informática":["Me gusta resolver problemas con computadoras","Me interesaría crear aplicaciones"],
        "Salud":["Me interesa cuidar la salud de las personas","Me gusta aprender sobre el cuerpo humano"],
        "Educación":["Disfruto explicar temas a otros","Me gustaría acompañar aprendizajes"],
        "Sociales":["Me interesa la historia y la sociedad","Me gusta investigar problemas sociales"],
        "Arte y diseño":["Disfruto crear producciones artísticas","Me interesa diseñar objetos o imágenes"],
        "Agro y ambiente":["Me importa cuidar el ambiente","Me interesa la producción sustentable"]
    }
    with st.form("intereses"):
        answers={}
        for area, questions in areas.items():
            st.markdown("**"+area+"**")
            for i,q in enumerate(questions):
                answers[(area,i)]=st.radio(q,["Nada","Poco","Bastante","Mucho"],horizontal=True,index=None,key=area+str(i))
        sent=st.form_submit_button("Ver resultados")
    if sent:
        if None in answers.values():
            st.error("Respondé todas las afirmaciones.")
        else:
            points={"Nada":0,"Poco":1,"Bastante":2,"Mucho":3}
            scores={area:sum(points[answers[(area,i)]] for i in range(2)) for area in areas}
            top=sorted(scores,key=scores.get,reverse=True)[:3]
            st.success("Áreas de mayor interés: "+", ".join(top))
            st.bar_chart(pd.Series(scores))
            st.caption("Los resultados son una invitación a explorar, no una indicación de qué carrera elegir.")
with tab_chat:
    st.subheader("Asistente de carreras")
    st.caption("Primera versión: búsqueda conversacional por palabras, sin IA generativa.")
    query=st.chat_input("Ej.: matemática, historia, informática")
    if query:
        with st.chat_message("user"):st.write(query)
        found=df[df.apply(lambda row:any(word.casefold() in " ".join(map(str,row.values)).casefold() for word in query.split() if len(word)>4),axis=1)]
        with st.chat_message("assistant"):
            if found.empty:st.write("No encontré coincidencias. Probá con el nombre de una carrera.")
            else:
                for _,r in found.head(8).iterrows():
                    st.write(f"• {r[career]} — {r['Institución']} ({r[town]})")
                st.caption("Información histórica: verificar oferta vigente.")
st.divider()
st.caption("Mi Futuro Jujuy · Prototipo educativo · Información en revisión")
