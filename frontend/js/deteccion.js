const videoDeteccion =
    document.querySelector("#video-camara");

const cnnDanza =
    document.querySelector("#cnn-danza");

const cnnRegion =
    document.querySelector("#cnn-region");

const cnnConfianza =
    document.querySelector("#cnn-confianza");

const estadoResultados =
    document.querySelector("#estado-resultados");


// ============================================================
// VARIABLES
// ============================================================

let intervaloDeteccion = null;
let procesandoFrame = false;


// ============================================================
// REGIONES
// ============================================================

const regiones = {
    cumbia: "Caribe",
    currulao: "Pacífica",
    bambuco: "Andina",
    joropo: "Orinoquía"
};


// ============================================================
// ENVIAR FRAME
// ============================================================

async function enviarFrame() {

    if (procesandoFrame) return;

    if (
        !videoDeteccion.videoWidth
        || !videoDeteccion.videoHeight
    ) {
        return;
    }


    procesandoFrame = true;


    const canvas =
        document.createElement("canvas");


    canvas.width =
        videoDeteccion.videoWidth;

    canvas.height =
        videoDeteccion.videoHeight;


    const contexto =
        canvas.getContext("2d");


    contexto.drawImage(
        videoDeteccion,
        0,
        0,
        canvas.width,
        canvas.height
    );


    canvas.toBlob(

        async (blob) => {

            if (!blob) {
                procesandoFrame = false;
                return;
            }


            const datos =
                new FormData();


            datos.append(
                "frame",
                blob,
                "frame.jpg"
            );


            try {

                const respuesta =
                    await fetch(
                        "http://127.0.0.1:5000/api/predict",
                        {
                            method: "POST",
                            body: datos
                        }
                    );


                const resultado =
                    await respuesta.json();


                console.log(
                    "Predicción:",
                    resultado
                );


                mostrarResultado(
                    resultado
                );


            } catch (error) {

                console.error(
                    "Error con el backend:",
                    error
                );


                estadoResultados.textContent =
                    "Backend no disponible";


            } finally {

                procesandoFrame = false;
            }

        },

        "image/jpeg",

        0.8
    );
}


// ============================================================
// MOSTRAR RESULTADO
// ============================================================

function mostrarResultado(resultado) {

    if (!resultado.confirmada) {
        estadoResultados.textContent =
            "Analizando postura";

        return;
    }

    const danza = resultado.danza;

    cnnDanza.textContent =
        danza.toUpperCase();

    cnnRegion.textContent =
        regiones[danza] || "—";

    cnnConfianza.textContent =
        `${Math.round(resultado.confianza * 100)}%`;

    estadoResultados.textContent =
        "Danza reconocida";

    // Detener análisis
    detenerDeteccion();

    // Apagar físicamente la cámara
    videoDeteccion.srcObject
        ?.getTracks()
        .forEach((pista) => pista.stop());

    videoDeteccion.srcObject = null;

    // Ir al resultado
    document
        .getElementById("resultados")
        .scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
}


// ============================================================
// INICIAR
// ============================================================

async function iniciarDeteccion() {

    if (intervaloDeteccion) return;

    // Limpiar las 5 predicciones anteriores
    await fetch(
        "http://127.0.0.1:5000/api/reset",
        {
            method: "POST"
        }
    );

    intervaloDeteccion = setInterval(
        enviarFrame,
        4000
    );
}


// ============================================================
// DETENER
// ============================================================

function detenerDeteccion() {

    if (intervaloDeteccion) {

        clearInterval(
            intervaloDeteccion
        );


        intervaloDeteccion =
            null;
    }


    procesandoFrame =
        false;
}

function reiniciarResultados() {
    cnnDanza.textContent = "Esperando detección";
    cnnRegion.textContent = "—";
    cnnConfianza.textContent = "—";
    estadoResultados.textContent = "Analizando postura";
}