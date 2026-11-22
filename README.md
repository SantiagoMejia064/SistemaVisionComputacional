# Colombia en Movimiento

Interfaz cultural local para reconocer posturas asociadas a Cumbia, Currulao, Bambuco y Joropo.

## Ejecución local

Desde la raíz del proyecto, con Python 3.13 (entorno comprobado):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m backend.yolo.api
```

Abrir **http://127.0.0.1:5000**. Flask sirve interfaz y API.
Si Python no está en PATH, usar su ruta completa para crear el entorno.
También se admite Live Server en localhost, con la API en el puerto 5000.
Las versiones fijadas corresponden al entorno comprobado. CUDA depende de la instalación de PyTorch.

## Modelos locales

- `yolo11n-pose.pt` en la raíz.
- `models/cnn/cnn_filtro_pose.pth`: MobileNetV2 binaria.
- `models/yolo/pose_classifier.pth`: MLP 34 → 64 → 32 → 4.

Los checkpoints entrenados están ignorados por Git.
[Datos y modelos del equipo](https://drive.google.com/drive/folders/1OiU35X_bGq5RkKuuXAHBH0aeCmfa8w46?usp=sharing).
El servidor indica la ruta si falta un modelo. No descarga pesos automáticamente.

## Flujo integrado

1. El navegador abre cámara sin audio e inicia una sesión.
2. Envía un JPEG. Espera la respuesta y 700 ms antes de la siguiente captura.
3. YOLO Pose procesa el fotograma completo una vez.
4. Se exige una sola persona y se recorta su caja con margen del 10 %.
5. La CNN evalúa el recorte RGB: P(pose) ≥ 0,70.
6. Se exige confianza ≥ 0,50 en hombros, codos, muñecas, caderas, rodillas y tobillos.
7. El MLP recibe 17 puntos X/Y normalizados respecto del fotograma original: confianza ≥ 0,85.
8. Cinco clases consecutivas iguales confirman la danza.
9. Se actualizan ficha cultural, fotografía, video, región y confianza; se cierra la cámara.

YOLO va antes de la CNN porque el entrenamiento existente usa recortes de personas.
La CNN distingue pose/no pose; YOLO obtiene puntos y el MLP clasifica la danza.
El filtro lee etiquetas, tamaño y normalización del checkpoint.
No se reentrenaron pesos ni se cambió la normalización del MLP.
Los umbrales están en `backend/yolo/clasificador.py` y requieren calibración con personas reales.

Cada ejecución usa una sesión independiente. El cliente cancela solicitudes y descarta respuestas antiguas
al detener o cambiar cámara. El servidor reinicia la racha ante rechazos o pausas de más de 10 s;
las sesiones caducan después de 120 s sin actividad. La inferencia compartida usa un bloqueo.
No se guardan imágenes de visitantes.

## Organización

| Ruta | Responsabilidad |
| --- | --- |
| `frontend/` | Interfaz, captura, ficha cultural y recursos multimedia |
| `backend/yolo/api.py` | HTTP, servicio de archivos y confirmación por sesión |
| `backend/yolo/clasificador.py` | Pipeline compartido YOLO → recorte/CNN → MLP |
| `backend/yolo/filtro_pose.py` | Carga e inferencia de la CNN |
| `backend/yolo/test_camara.py` | Prueba manual del mismo pipeline |
| `backend/cnn/CNN.PERSONA.ipynb` | Entrenamiento original CNN para Colab |
| `backend/tests/` | Pruebas del contrato y modelos |
| `models/` | Pesos entrenados locales |
| `data/`, `notebooks/` | Directorios reservados |
| `docs/images/` | Capturas de la interfaz |

La evaluación por ángulos está pendiente y se identifica así en la interfaz.
Las poses son consignas de interacción; no validan la autenticidad de una danza tradicional.

## API

- `GET /`: interfaz.
- `GET /api/health`: disponibilidad y confirmaciones requeridas.
- `POST /api/reset`: crea una sesión; devuelve `ok` y `sesion`.
- `POST /api/predict`: multipart con `frame` y `sesion`.

La predicción devuelve `estado`, `clase`, `confianza` del MLP, `confianza_pose` de la CNN,
`personas`, `puntos_visibles`, `keypoints` (triples X/Y/confianza), `consecutivas`,
`requeridas`, `confirmada` y `danza`. Las probabilidades van de 0 a 1.
La probabilidad CNN es null si no se evaluó; danza es null hasta confirmar.

Estados: `sin_persona`, `multiples_personas`, `no_pose`, `puntos_insuficientes`,
`sin_clasificacion`, `analizando`, `confirmada`.
Errores JSON: 400 (entrada inválida), 409 (sesión caducada), 413 (más de 8 MiB),
500 (fallo de inferencia). Se rechazan imágenes de más de 16 megapíxeles.

## Validación

```powershell
python -m unittest discover -s backend/tests -v
node --test frontend/js/deteccion.test.cjs
python -m backend.yolo.test_camara
```

La prueba manual requiere cámara disponible; Q cierra la ventana.
Usa los mismos modelos y umbrales, y muestra la racha de confirmación.

Las pruebas automáticas comprueban modelos reales sin persona, salida binaria CNN, errores,
confirmación, cambio de clase, aislamiento y caducidad de sesiones y descarte de respuestas antiguas.
Las clases positivas se simulan en las pruebas del contrato; esto no mide precisión de las danzas.
Validar las cuatro poses y negativos con visitantes, distancias e iluminación diferentes antes de reportar métricas.

## Equipo y créditos

**Universidad Autónoma de Occidente**

**Asignatura** Procesamiento Digital de Imágenes

**Docente** Nicolás Llanos Neuta

| Integrante | Rol principal | Responsabilidades |
| --- | --- | --- |
| Santiago Mejía Suárez | Responsable técnico | Arquitectura, integración frontend y backend, coordinación técnica y seguimiento de visión computacional |
| Jean Carlo Caicedo Chantre | Responsable funcional | Requisitos, alcance, escenarios de uso y correspondencia con necesidades |
| Jhoan Esteban Burgos | Responsable de interacción | Experiencia de usuario, navegación, prototipado, retroalimentación y coherencia visual |
| Karol Lizeth Grain Mosquera | Validadora | Planificación y ejecución de pruebas, revisión de criterios de aceptación y oportunidades de mejora |

Los roles describen responsabilidades organizativas del equipo. No asignan autoría exclusiva de archivos ni certifican tareas individuales realizadas.

<a id="referencias"></a>
## Referencias y atribuciones

### Ingeniería, modelos y herramientas

- [Repositorio del proyecto](https://github.com/SantiagoMejia064/SistemaVisionComputacional) y [prototipo en Figma](https://www.figma.com/design/E15852kz3GEqF0mtmDZLiC/Untitled?node-id=0-1).
- [Flask](https://flask.palletsprojects.com/en/stable/), [Flask-CORS](https://flask-cors.readthedocs.io/en/latest/) y [Python](https://docs.python.org/3/).
- [PyTorch](https://pytorch.org/get-started/locally/), [OpenCV](https://docs.opencv.org/4.x/) y [NumPy](https://numpy.org/doc/stable/).
- [Ultralytics en GitHub](https://github.com/ultralytics/ultralytics), [YOLO11](https://docs.ultralytics.com/models/yolo11/) y [estimación de poses](https://docs.ultralytics.com/tasks/pose/).
- [Media Capture and Streams](https://www.w3.org/TR/mediacapture-streams/) para acceso a dispositivos de cámara.
- [Bootstrap](https://getbootstrap.com/docs/5.3/) y [Live Server](https://github.com/ritwickdey/vscode-live-server).

### Fuentes culturales y cartografía

- [Cumbia tradicional del Caribe colombiano](https://patrimonio.mincultura.gov.co/salvaguardiapci/Lista-Representativa/Paginas/Cumbia-tradicional-del-Caribe-Colombiano.aspx).
- [Músicas de marimba y cantos tradicionales](https://mng.mincultura.gov.co/areas/patrimonio/patrimonio-cultural-en-Colombia/Paginas/Lista-Representativa-del-Patrimonio-Cultural-Inmaterial.aspx) y [Danzas guapireñas](https://colombiaaprende.edu.co/sites/default/files/files_public/plan-lectura-2021/territorios-narrados-parte-1/Danzas_guapirenas.pdf).
- [Danzas de la región Andina](https://contenidos.mineducacion.gov.co/ntg/men/archivos/Referentes_Calidad/Modelos_Flexibles/Secundaria_Activa/Guias_del_estudiante/Educacion_Artistica/ART__Danza.pdf) y [traje típico del sanjuanero huilense](https://www.huila.gov.co/publicaciones/719/traje-tispico-69064/).
- [Pobladores del Orinoco](https://enciclopedia.banrepcultural.org/Pobladores_del_Orinoco) y [vestuario del joropo en Casanare](https://feriasdellibro.mincultura.gov.co/contenidos_digitales/tradiciones-del-vestuario-asociadas-al-baile-del-joropo-en-casanare-siglos-xix-y-xx/).
- [GeoJSON de Colombia](https://github.com/johan/world.geo.json/blob/master/countries/COL.geo.json), base geográfica del mapa. Las cuatro zonas culturales internas son esquemáticas.

### Licencias de recursos y dependencias

| Recurso | Licencia o condición de consulta |
| --- | --- |
| Bootstrap | MIT. Se conserva [su licencia local](frontend/css/bootstrap-LICENSE.txt). |
| Outfit | SIL Open Font License 1.1. [Licencia local](frontend/assets/fonts/OFL-Outfit.txt). |
| Plus Jakarta Sans | SIL Open Font License 1.1. [Licencia local](frontend/assets/fonts/OFL-Jakarta.txt). |
| Ultralytics | El repositorio publica AGPL-3.0 y ofrece licencia Enterprise. Revisar las condiciones aplicables al código y los pesos utilizados. [Licencia](https://github.com/ultralytics/ultralytics/blob/main/LICENSE), [opciones de licencia](https://www.ultralytics.com/license). |
| Flask y Flask-CORS | Consultar licencias de las versiones instaladas. [Flask](https://github.com/pallets/flask/blob/main/LICENSE.txt), [Flask-CORS](https://github.com/corydolphin/flask-cors/blob/main/LICENSE). |
| PyTorch, NumPy y OpenCV | Consultar atribuciones y licencias en las distribuciones instaladas. [PyTorch](https://github.com/pytorch/pytorch/blob/main/LICENSE), [NumPy](https://github.com/numpy/numpy/blob/main/LICENSE.txt), [OpenCV](https://github.com/opencv/opencv/blob/4.x/LICENSE). |
| Datos y checkpoint del equipo | Disponibles en Drive. No se identificó una licencia de redistribución dentro de los archivos del repositorio inspeccionado. |
| Cartografía y fuentes culturales | Se conservan enlaces de atribución. Comprobar las condiciones de reutilización al publicar recursos derivados. |

Las capturas de `docs/images/` muestran la interfaz del proyecto y no incluyen fotografías de visitantes. No existe un archivo de licencia global del proyecto en esta revisión, por lo que este README no declara una.
