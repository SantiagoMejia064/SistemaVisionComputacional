// ============================================================
// FICHA CULTURAL
// ============================================================

const fichas = document.querySelectorAll("[data-ficha]");

function seleccionarDanza(danza) {
    fichas.forEach((ficha) => {
        ficha.hidden = ficha.dataset.ficha !== danza;
    });

    const ficha = document.querySelector("[data-ficha]:not([hidden])");
    const nombre = ficha.querySelector("h3").textContent;

    document.querySelector("#region-cultural").textContent = ficha.dataset.region;
    document.querySelector("#foto-cultural").textContent = `Fotografía de ${nombre} pendiente`;
    document.querySelector("#video-cultural").textContent = `Video de ${nombre}`;
    document.querySelector("#danza-seleccionada").textContent = `Ficha cultural de ${nombre}`;
}

document.querySelectorAll("input[name='danza']").forEach((tarjeta) => {
    tarjeta.addEventListener("change", () => seleccionarDanza(tarjeta.value));
});

seleccionarDanza(
    document.querySelector("input[name='danza']:checked").value
);


// ============================================================
// ESTADOS DEL VISOR
// ============================================================

const estados = {
    espera: [
        "En espera",
        "Ponte de pie frente al visor",
        "La silueta es una guía visual para el encuadre."
    ],

    preparacion: [
        "Preparación",
        "Encuadra el cuerpo completo",
        "Activa la cámara y usa la guía para encuadrarte."
    ],

    analisis: [
        "Análisis",
        "Analizando postura",
        "Mantén el cuerpo completo visible mientras se analiza tu pose."
    ],

    resultado: [
        "Resultado",
        "Danza reconocida",
        "Consulta el panel de resultados."
    ]
};


// ============================================================
// ELEMENTOS
// ============================================================

const controles = document.querySelectorAll("#controles-camara [data-camara]");
const guia = document.querySelector("#guia");
const escenario = document.querySelector("#escenario");
const aviso = document.querySelector("#aviso-camara");
const visor = document.querySelector("#visor-camara");
const video = document.querySelector("#video-camara");

const dispositivos = document.querySelector("#dispositivo-camara");
const activar = document.querySelector("#activar-camara");
const detener = document.querySelector("#detener-camara");

const accionPortada = document.querySelector("#accion-camara-portada");
const estadoDispositivo = document.querySelector("#estado-dispositivo");
const ayudaDispositivo = document.querySelector("#ayuda-dispositivo");
const errorDispositivo = document.querySelector("#error-dispositivo");

const media = navigator.mediaDevices;

let solicitudCamara = 0;


// ============================================================
// CÁMARA
// ============================================================

function liberarVideo() {
    video.srcObject?.getTracks().forEach((pista) => pista.stop());

    video.srcObject = null;
    video.hidden = true;

    visor.classList.remove("visor-en-vivo");
}


function apagarCamara() {
    detenerDeteccion();

    solicitudCamara++;

    liberarVideo();

    dispositivos.disabled = false;
    activar.disabled = false;
    activar.hidden = false;

    accionPortada.textContent = "Activar cámara";

    detener.hidden = true;
    errorDispositivo.hidden = true;

    estadoDispositivo.textContent = "Cámara apagada";
    estadoDispositivo.classList.replace("verde", "naranja");
}


async function listarCamaras() {
    const flujo = video.srcObject;
    const seleccion = dispositivos.value;

    const lista = await media.enumerateDevices();

    if (video.srcObject !== flujo) return;

    const camaras = lista.filter(
        (dispositivo) =>
            dispositivo.kind === "videoinput" &&
            dispositivo.deviceId
    );

    dispositivos.replaceChildren(
        new Option("Cámara predeterminada", "")
    );

    camaras.forEach((camara, i) => {
        dispositivos.add(
            new Option(
                camara.label || `Cámara ${i + 1}`,
                camara.deviceId
            )
        );
    });

    const activa =
        flujo.getVideoTracks()[0].getSettings().deviceId ||
        seleccion;

    dispositivos.value =
        camaras.some((camara) => camara.deviceId === activa)
            ? activa
            : "";

    ayudaDispositivo.textContent =
        "Elige la cámara que quieres usar en el visor.";
}


function mostrarErrorDispositivo(mensaje) {
    errorDispositivo.textContent = mensaje;
    errorDispositivo.hidden = false;
}


// ============================================================
// ENCENDER CÁMARA
// ============================================================

async function encenderCamara() {
    if (activar.disabled) return;

    if (!media?.getUserMedia) {
        mostrarErrorDispositivo(
            "Abre el sitio en localhost desde un navegador compatible para usar la cámara."
        );
        return;
    }

    const solicitud = ++solicitudCamara;
    const id = dispositivos.value;

    liberarVideo();

    activar.disabled = true;
    dispositivos.disabled = true;
    detener.hidden = true;
    errorDispositivo.hidden = true;

    estadoDispositivo.textContent = "Abriendo cámara…";
    estadoDispositivo.classList.replace("verde", "naranja");

    try {
        const flujo = await media.getUserMedia({
            video: id
                ? { deviceId: { exact: id } }
                : true,

            audio: false
        });

        if (solicitud !== solicitudCamara) {
            flujo.getTracks().forEach((pista) => pista.stop());
            return;
        }

        video.srcObject = flujo;
        video.hidden = false;

        visor.classList.add("visor-en-vivo");

        estadoDispositivo.textContent = "Cámara en vivo";
        estadoDispositivo.classList.replace("naranja", "verde");

        activar.hidden = true;
        accionPortada.textContent = "Ver cámara";

        detener.hidden = false;
        dispositivos.disabled = false;

        if (visor.classList.contains("visor-espera")) {
            cambiarCamara("preparacion");
        }

        // Limpiar resultado anterior
        reiniciarResultados();

        // Comenzar reconocimiento
        iniciarDeteccion();

        flujo.getVideoTracks()[0].addEventListener("ended", () => {
            if (video.srcObject !== flujo) return;

            apagarCamara();

            mostrarErrorDispositivo(
                "La cámara dejó de estar disponible."
            );
        });

        actualizarListaCamaras();

    } catch (error) {
        if (solicitud !== solicitudCamara) return;

        apagarCamara();

        const mensajes = {
            NotAllowedError:
                "Permite el acceso a la cámara y vuelve a intentarlo.",

            NotFoundError:
                "No se encontró la cámara.",

            OverconstrainedError:
                "La cámara seleccionada ya no está disponible.",

            NotReadableError:
                "Otra aplicación puede estar usando la cámara."
        };

        mostrarErrorDispositivo(
            mensajes[error.name] ||
            "No se pudo activar la cámara."
        );

    } finally {
        if (solicitud === solicitudCamara) {
            activar.disabled = false;
        }
    }
}


function actualizarListaCamaras() {
    if (!video.srcObject) return;

    listarCamaras().catch(() => {
        if (video.srcObject) {
            ayudaDispositivo.textContent =
                "No se pudo actualizar la lista de cámaras.";
        }
    });
}


// ============================================================
// BOTONES DE CÁMARA
// ============================================================

document.querySelectorAll("[data-activar-camara]").forEach((boton) => {
    boton.addEventListener("click", () => {
        if (!video.srcObject) {
            encenderCamara();
        }
    });
});


dispositivos.addEventListener("change", () => {
    if (video.srcObject) {
        encenderCamara();
    }
});


detener.addEventListener("click", () => {
    apagarCamara();
    activar.focus();
});


media?.addEventListener(
    "devicechange",
    actualizarListaCamaras
);


window.addEventListener(
    "pagehide",
    apagarCamara
);


// ============================================================
// AVISOS
// ============================================================

function cerrarAviso() {
    aviso.hidden = true;
    escenario.value = "";
}


// ============================================================
// CAMBIAR ESTADO DEL VISOR
// ============================================================

function cambiarCamara(estado) {
    const [rotulo, titulo, mensaje] = estados[estado];

    document.querySelector("#estado-camara").textContent = rotulo;
    document.querySelector("#titulo-visor").textContent = titulo;
    document.querySelector("#mensaje-visor").textContent = mensaje;

    visor.classList.toggle(
        "visor-espera",
        estado === "espera"
    );

    if (estado === "espera") {
        apagarCamara();
    }

    document.querySelector("#pipeline-pdi").hidden =
        estado !== "analisis";

    guia.open =
        estado === "preparacion";

    const siguiente = {
        espera: "preparacion",
        preparacion: "analisis",
        analisis: "resultado"
    }[estado];

    controles.forEach((control) => {
        control.hidden =
            control.dataset.camara !== siguiente &&
            (
                control.dataset.camara !== "espera" ||
                estado === "espera"
            );
    });

    cerrarAviso();
}


// ============================================================
// ESCENARIOS DE DEMOSTRACIÓN
// ============================================================

escenario.addEventListener("change", () => {
    if (!escenario.value) {
        cerrarAviso();
        return;
    }

    const opcion = escenario.selectedOptions[0];

    aviso.hidden = false;

    document.querySelector("#titulo-aviso").textContent =
        `${opcion.text} · Demostración`;

    document.querySelector("#mensaje-aviso").textContent =
        opcion.dataset.mensaje;
});


document.querySelector("#cerrar-aviso")
    .addEventListener("click", () => {
        cerrarAviso();
        escenario.focus();
    });


// ============================================================
// NAVEGACIÓN
// ============================================================

document.querySelectorAll("[data-camara], [data-ir]")
    .forEach((boton) => {

        boton.addEventListener("click", () => {

            if (boton.dataset.camara) {
                cambiarCamara(
                    boton.dataset.camara
                );
            }

            if (boton.dataset.ir) {
                const panel =
                    document.getElementById(
                        boton.dataset.ir
                    );

                panel.focus({
                    preventScroll: true
                });

                panel.scrollIntoView({
                    block: "start"
                });

            } else if (boton.hidden) {
                document
                    .querySelector(
                        "#controles-camara button:not([hidden])"
                    )
                    ?.focus({
                        preventScroll: true
                    });
            }
        });
    });