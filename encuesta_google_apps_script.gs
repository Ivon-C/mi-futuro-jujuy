// Apps Script para guardar la encuesta de Mi Futuro Jujuy en Google Sheets.
// Copiar este contenido en el proyecto de Apps Script vinculado a la hoja de respuestas.
const SPREADSHEET_ID = "15PW7f5AzGUNshPwdRxvGiVMbxEeh9d3u1Jnx190cCfs";
const SHEET_NAME = "Respuestas";
const CAMPOS_AREAS = [
  "Área sugerida 1", "Puntaje área 1",
  "Área sugerida 2", "Puntaje área 2",
  "Área sugerida 3", "Puntaje área 3",
  "Ajuste percibido de las áreas"
];

function doPost(e) {
  try {
    const data = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    const edad = Number(data.edad);
    const encontrada = String(data.carrera_encontrada || "").trim();
    const faltante = String(data.carrera_faltante || "").trim();
    const mejora = String(data.mejoras || "").trim();
    const ajuste = String(data.ajuste_areas || "").trim();
    const areas = [1, 2, 3].map(i => String(data["area_" + i] || "").trim());
    const puntajes = [1, 2, 3].map(i => data["puntaje_" + i] === "" || data["puntaje_" + i] == null ? "" : Number(data["puntaje_" + i]));
    const envioId = String(data.submission_id || "").trim();
    if (envioId && !/^[a-f0-9]{32}$/i.test(envioId)) {
      throw new Error("El identificador del envío no es válido.");
    }
    if (!Number.isInteger(edad) || edad < 10 || edad > 99) {
      throw new Error("La edad debe ser un número entero entre 10 y 99.");
    }
    if (encontrada !== "Sí" && encontrada !== "No") {
      throw new Error("Indicá si encontraste la carrera.");
    }
    if (encontrada === "No" && !faltante) {
      throw new Error("Indicá qué carrera buscabas.");
    }
    const opcionesAjuste = ["Sí, me representan", "En parte", "No me representan", "No estoy seguro/a"];
    if (areas.some(Boolean) && !opcionesAjuste.includes(ajuste)) {
      throw new Error("Indicá si las áreas sugeridas se relacionan con tus intereses.");
    }
    if (!areas.some(Boolean) && ajuste) {
      throw new Error("No se esperaba una evaluación de áreas sin resultado sugerido.");
    }
    for (let i = 0; i < 3; i++) {
      if (Boolean(areas[i]) !== (puntajes[i] !== "")) {
        throw new Error("El área y su puntaje deben enviarse juntos.");
      }
      if (puntajes[i] !== "" && (!Number.isFinite(puntajes[i]) || puntajes[i] < 1 || puntajes[i] > 4)) {
        throw new Error("El puntaje de cada área debe estar entre 1 y 4.");
      }
      if (areas[i] && areas[i].length > 120) {
        throw new Error("El nombre del área no es válido.");
      }
    }

    const libro = SpreadsheetApp.openById(SPREADSHEET_ID);
    const hoja = libro.getSheetByName(SHEET_NAME);
    if (!hoja) throw new Error("No se encontró la pestaña Respuestas.");
    const encabezadosActuales = hoja.getRange(1, 6, 1, CAMPOS_AREAS.length).getValues()[0];
    CAMPOS_AREAS.forEach((titulo, i) => {
      if (!encabezadosActuales[i]) hoja.getRange(1, 6 + i).setValue(titulo);
    });

    const bloqueo = LockService.getScriptLock();
    bloqueo.waitLock(10000);
    let duplicado = false;
    try {
      const propiedades = PropertiesService.getScriptProperties();
      const claveEnvio = envioId ? "encuesta_envio_" + envioId : "";
      if (claveEnvio && propiedades.getProperty(claveEnvio)) {
        duplicado = true;
      } else {
        const fecha = Utilities.formatDate(new Date(), "America/Argentina/Jujuy", "yyyy-MM-dd HH:mm:ss");
        hoja.appendRow([
          fecha, edad, encontrada, encontrada === "No" ? faltante : "", mejora,
          areas[0], puntajes[0], areas[1], puntajes[1], areas[2], puntajes[2], ajuste
        ]);
        if (claveEnvio) propiedades.setProperty(claveEnvio, fecha);
      }
    } finally {
      bloqueo.releaseLock();
    }

    return ContentService.createTextOutput(JSON.stringify({ok: true, duplicate: duplicado}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, error: String(error.message || error)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
