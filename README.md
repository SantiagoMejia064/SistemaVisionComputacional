# Colombia en Movimiento

Instalación interactiva universitaria para explorar Cumbia, Currulao, Bambuco y Joropo. El mapa, el repertorio, la ficha cultural, la cámara y los resultados comparten una sola página.

## Abrir en localhost

Desde la raíz del repositorio, con Python 3 instalado:

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory frontend
```

Abre [http://localhost:8000](http://localhost:8000). Este comando sirve los archivos estáticos. Bootstrap, las tipografías y los SVG se cargan desde el repositorio.

Pulsa **Activar cámara** y concede el permiso en el navegador. El selector **Cámara del dispositivo** mostrará las opciones disponibles después de concederlo. Cambia la selección para ver otra cámara o pulsa **Apagar cámara** para liberar el dispositivo. La vista en vivo usa solo video y permanece en el navegador.

## Organización

| Carpeta | Contenido |
| --- | --- |
| `frontend/` | Página única, estilos, interacciones y recursos visuales. |
| `backend/cnn/` | Futuro código Python para clasificar la danza. |
| `backend/yolo/` | Futuro código Python para obtener los puntos corporales. |
| `backend/angulos/` | Futuro cálculo de ángulos y evaluación de la postura. |
| `notebooks/` | Desarrollo y evaluación, separados en CNN, YOLO y ángulos. |
| `models/` | Archivos locales de los modelos entrenados de CNN y YOLO. |
| `data/` | Imágenes, anotaciones y referencias del proyecto. |

## Integración pendiente

La vista en vivo permite preparar el encuadre. El análisis y los avisos del prototipo siguen en modo de demostración. Los paneles `resultado-cnn`, `resultado-yolo` y `resultado-angulos` muestran los campos pendientes de integración.

La CNN y YOLO Pose podrán recibir la misma imagen temporal. Python usará los puntos de YOLO para calcular los ángulos y aplicar los criterios de postura que se definan y validen. Los resultados aparecerán en la misma página. La comunicación entre Python y el navegador se definirá cuando estén listos los modelos.

El sistema funcionará en localhost. Las capturas y los resultados serán temporales en memoria durante la ejecución. Los pesos entrenados podrán guardarse como archivos locales. El proyecto prescinde de servicios en la nube, bases de datos y almacenamiento de fotografías, videos, resultados o historiales de visitantes.

## Referencias

- [GeoJSON de Colombia](https://github.com/johan/world.geo.json/blob/master/countries/COL.geo.json), base de la silueta del mapa. Sus divisiones culturales son esquemáticas.
- [Cumbia tradicional del Caribe](https://patrimonio.mincultura.gov.co/salvaguardiapci/Lista-Representativa/Paginas/Cumbia-tradicional-del-Caribe-Colombiano.aspx).
- [Músicas de marimba y cantos tradicionales](https://mng.mincultura.gov.co/areas/patrimonio/patrimonio-cultural-en-Colombia/Paginas/Lista-Representativa-del-Patrimonio-Cultural-Inmaterial.aspx) y [Danzas guapireñas](https://colombiaaprende.edu.co/sites/default/files/files_public/plan-lectura-2021/territorios-narrados-parte-1/Danzas_guapirenas.pdf).
- [Danzas de la región Andina](https://contenidos.mineducacion.gov.co/ntg/men/archivos/Referentes_Calidad/Modelos_Flexibles/Secundaria_Activa/Guias_del_estudiante/Educacion_Artistica/ART__Danza.pdf) y [traje típico del sanjuanero huilense](https://www.huila.gov.co/publicaciones/719/traje-tispico-69064/).
- [Pobladores del Orinoco](https://enciclopedia.banrepcultural.org/Pobladores_del_Orinoco) y [vestuario del joropo en Casanare](https://feriasdellibro.mincultura.gov.co/contenidos_digitales/tradiciones-del-vestuario-asociadas-al-baile-del-joropo-en-casanare-siglos-xix-y-xx/).
