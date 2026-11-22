// Pruebas de carreras as?ncronas sin cámara ni dependencias externas.
const {test} = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const source = fs.readFileSync(__dirname + "/deteccion.js", "utf8");

function entorno() {
    const elementos = new Map();
    const elemento = selector => {
        if (!elementos.has(selector)) elementos.set(selector, {
            textContent:"", hidden:false, srcObject:{}, readyState:2,
            videoWidth:640, videoHeight:480, replaceChildren(){},
            setAttribute(){}, append(){}, scrollIntoView(){}
        });
        return elementos.get(selector);
    };
    const peticiones = [];
    const contexto = vm.createContext({
        location:{port:"5000"}, AbortController, FormData, Blob,
        setTimeout, clearTimeout,
        document:{
            querySelector:elemento, getElementById:elemento,
            createElement:() => ({
                getContext:() => ({drawImage(){}}),
                toBlob:callback => callback(new Blob(["frame"]))
            }),
            createElementNS:() => ({setAttribute(){}})
        },
        fetch:(url, opciones) => new Promise(resolve => peticiones.push({url, opciones, resolve})),
        cambiarCamara(){}, seleccionarDanza(){}, mostrarErrorDispositivo(){},
        apagarCamara:() => vm.runInContext("detenerDeteccion()", contexto)
    });
    vm.runInContext(source, contexto);
    return {contexto, peticiones, elementos};
}
const resolver = (peticion, resultado) => peticion.resolve({ok:true, json:async()=>resultado});
const turno = () => new Promise(resolve => setImmediate(resolve));

test("apagar durante reset no inicia capturas", async () => {
    const e = entorno();
    const inicio = vm.runInContext("iniciarDeteccion()", e.contexto);
    vm.runInContext("detenerDeteccion()", e.contexto);
    resolver(e.peticiones[0], {sesion:"anterior"});
    await inicio;
    assert.equal(e.peticiones.length, 1);
});

test("ignora una predicción de una ejecución anterior", async () => {
    const e = entorno();
    const inicio = vm.runInContext("iniciarDeteccion()", e.contexto);
    resolver(e.peticiones[0], {sesion:"anterior"});
    await turno();
    assert.equal(e.peticiones.length, 2);
    vm.runInContext("detenerDeteccion()", e.contexto);
    resolver(e.peticiones[1], {confirmada:true, danza:"cumbia"});
    await inicio;
    assert.equal(e.elementos.get("#cnn-danza").textContent, "");
});

test("una nueva ejecución conserva su propia sesión", async () => {
    const e = entorno();
    const anterior = vm.runInContext("iniciarDeteccion()", e.contexto);
    const nueva = vm.runInContext("iniciarDeteccion()", e.contexto);
    resolver(e.peticiones[0], {sesion:"anterior"});
    resolver(e.peticiones[1], {sesion:"nueva"});
    await turno();
    assert.equal(e.peticiones[2].opciones.body.get("sesion"), "nueva");
    vm.runInContext("detenerDeteccion()", e.contexto);
    resolver(e.peticiones[2], {});
    await Promise.all([anterior, nueva]);
});
