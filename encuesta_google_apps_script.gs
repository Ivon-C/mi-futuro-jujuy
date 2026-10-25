// Apps Script para guardar la encuesta de Mi Futuro Jujuy en Google Sheets.
// Copiar este contenido en un proyecto de Apps Script vinculado a la hoja de respuestas.
const SPREADSHEET_ID = "15PW7f5AzGUNshPwdRxvGiVMbxEeh9d3u1Jnx190cCfs";
const SHEET_NAME = "Respuestas";

function doPost(e) {
  try {
    const data = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    const edad = Number(data.edad);
    const encontrada = String(data.carrera_encontrada || "").trim();
    const faltante = String(data.carrera_faltante || "").trim();
    const mejora = String(data.mejoras || "").trim();
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

    const libro = SpreadsheetApp.openById(SPREADSHEET_ID);
    const hoja = libro.getSheetByName(SHEET_NAME);
    if (!hoja) throw new Error("No se encontró la pestaña Respuestas.");

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
        hoja.appendRow([fecha, edad, encontrada, encontrada === "No" ? faltante : "", mejora]);
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
