// Flask sirve la interfaz; también se admite Live Server en localhost.
const API_BASE = location.port === "5000" ? "" : "http://127.0.0.1:5000";
const PAUSA_ENTRE_CAPTURAS_MS = 400;
const videoDeteccion = document.querySelector("#video-camara");
const cnnDanza = document.querySelector("#cnn-danza");
const cnnRegion = document.querySelector("#cnn-region");
const cnnConfianza = document.querySelector("#cnn-confianza");
const estadoResultados = document.querySelector("#estado-resultados");
const regiones = { cumbia: "Caribe", currulao: "Pacífica", bambuco: "Andina", joropo: "Orinoquía" };
let ejecucionDeteccion = null;

async function solicitar(ruta, opciones, ejecucion) {
    const controlador = new AbortController();
    ejecucion.controlador = controlador;
    const limite = setTimeout(() => controlador.abort(), 30000);
    try {
        const respuesta = await fetch(API_BASE + ruta, { ...opciones, signal: controlador.signal });
        const resultado = await respuesta.json();
        if (!respuesta.ok) throw new Error(resultado.error || "Error del servidor");
        return resultado;
    } finally {
        clearTimeout(limite);
        if (ejecucion.controlador === controlador) ejecucion.controlador = null;
    }
}

async function iniciarDeteccion() {
    detenerDeteccion();
    const ejecucion = { sesion: null, controlador: null, temporizador: null };
    ejecucionDeteccion = ejecucion;
    try {
        const resultado = await solicitar("/api/reset", { method: "POST" }, ejecucion);
        if (ejecucionDeteccion !== ejecucion) return;
        ejecucion.sesion = resultado.sesion;
        cambiarCamara("analisis");
        await enviarFrame(ejecucion);
    } catch (error) {
        informarError(error, ejecucion);
    }
}

function informarError(error, ejecucion) {
    if (ejecucionDeteccion !== ejecucion) return;
    const mensaje = error.name === "AbortError"
        ? "El servidor tardó demasiado; reinicia la cámara."
        : error.message === "Failed to fetch"
            ? "Backend no disponible. Inicia el servidor y vuelve a activar la cámara."
            : error.message;
    apagarCamara();
    estadoResultados.textContent = mensaje;
    mostrarErrorDispositivo(mensaje);
}

async function enviarFrame(ejecucion) {
    if (ejecucionDeteccion !== ejecucion) return;
    try {
        if (!videoDeteccion.srcObject) return;
        if (videoDeteccion.readyState >= 2 && videoDeteccion.videoWidth) {
            const canvas = document.createElement("canvas");
            // Mantener la relación de aspecto para las coordenadas del MLP.
            const escala = Math.min(1, 1280 / videoDeteccion.videoWidth);
            canvas.width = Math.round(videoDeteccion.videoWidth * escala);
            canvas.height = Math.round(videoDeteccion.videoHeight * escala);
            canvas.getContext("2d").drawImage(videoDeteccion, 0, 0, canvas.width, canvas.height);
            const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
            if (ejecucionDeteccion !== ejecucion) return;
            if (!blob) throw new Error("No se pudo capturar la imagen.");
            const datos = new FormData();
            datos.append("frame", blob, "frame.jpg");
            datos.append("sesion", ejecucion.sesion);
            const resultado = await solicitar("/api/predict", { method: "POST", body: datos }, ejecucion);
            if (ejecucionDeteccion !== ejecucion) return;
            mostrarResultado(resultado);
        }
        if (ejecucionDeteccion === ejecucion) {
            ejecucion.temporizador = setTimeout(() => enviarFrame(ejecucion), PAUSA_ENTRE_CAPTURAS_MS);
        }
    } catch (error) {
        informarError(error, ejecucion);
    }
}

function actualizarEsqueleto(puntos) {
    const svg = document.querySelector("#yolo-esqueleto");
    svg.replaceChildren();
    svg.setAttribute("viewBox", "0 0 400 400");
    const nodo = (tipo, atributos) => {
        const elemento = document.createElementNS("http://www.w3.org/2000/svg", tipo);
        Object.entries(atributos).forEach(([nombre, valor]) => elemento.setAttribute(nombre, valor));
        svg.append(elemento);
    };
    const visible = (i) => puntos[i] && puntos[i][2] >= 0.5;
    const enlaces = [[5,6],[5,7],[7,9],[6,8],[8,10],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16]];
    enlaces.forEach(([a,b]) => {
        if (visible(a) && visible(b)) nodo("line", {
            x1: puntos[a][0]*400, y1: puntos[a][1]*400,
            x2: puntos[b][0]*400, y2: puntos[b][1]*400,
            stroke: "#45d5b0", "stroke-width": 3
        });
    });
    puntos.forEach(([x,y,c]) => {
        if (c >= 0.5) nodo("circle", { cx:x*400, cy:y*400, r:4, fill:"#75cfff" });
    });
    svg.hidden = !puntos.length;
    document.querySelector(".esqueleto-resultado img").hidden = !!puntos.length;
    document.querySelector("#yolo-estado-esqueleto").textContent =
        puntos.length ? "Puntos del último fotograma" : "Sin puntos detectados";
}

function mostrarResultado(resultado) {
    document.querySelector("#yolo-persona").textContent = String(resultado.personas);
    document.querySelector("#yolo-puntos").textContent = resultado.puntos_visibles + " / 17 visibles";
    document.querySelector("#cnn-pose").textContent = resultado.confianza_pose == null
        ? "—" : Math.round(resultado.confianza_pose * 100) + "%";
    actualizarEsqueleto(resultado.keypoints || []);
    const mensajes = {
        sin_persona: "Ponte frente a la cámara",
        multiples_personas: "Debe aparecer una sola persona",
        no_pose: "La CNN no reconoce una pose de danza",
        puntos_insuficientes: "Encuadra el cuerpo completo y deja visibles brazos y piernas",
        sin_clasificacion: "Pose incierta; ajusta la postura",
        analizando: "Mantén la pose: " + resultado.consecutivas + "/" + resultado.requeridas
    };
    estadoResultados.textContent = mensajes[resultado.estado] || "Analizando postura";
    if (!resultado.confirmada) return;
    const danza = resultado.danza;
    if (!Object.hasOwn(regiones, danza)) throw new Error("El servidor devolvió una danza desconocida.");
    cnnDanza.textContent = danza.toUpperCase();
    cnnRegion.textContent = regiones[danza];
    cnnConfianza.textContent = Math.round(resultado.confianza * 100) + "%";
    const tarjeta = document.querySelector('input[name="danza"][value="' + danza + '"]');
    if (tarjeta) tarjeta.checked = true;
    seleccionarDanza(danza);
    pausarCamaraConfirmada();
    cambiarCamara("resultado");
    mostrarContenidoCultural();
    estadoResultados.textContent = "Danza reconocida";
    document.getElementById("resultados").scrollIntoView({ behavior:"smooth", block:"start" });
}

function detenerDeteccion() {
    const anterior = ejecucionDeteccion;
    ejecucionDeteccion = null;
    if (anterior) {
        clearTimeout(anterior.temporizador);
        anterior.controlador?.abort();
    }
}

function reiniciarResultados() {
    cnnDanza.textContent = "Esperando detección";
    cnnRegion.textContent = "—";
    cnnConfianza.textContent = "—";
    document.querySelector("#cnn-pose").textContent = "—";
    document.querySelector("#yolo-persona").textContent = "Pendiente";
    document.querySelector("#yolo-puntos").textContent = "—";
    actualizarEsqueleto([]);
    estadoResultados.textContent = "Conectando con el servidor…";
}
