"""Prueba manual del pipeline real. Ejecutar como módulo; Q para salir."""
import cv2
if __package__:
    from .clasificador import analizar_imagen
else:
    from clasificador import analizar_imagen


def main():
    cap = cv2.VideoCapture(0)
    try:
        if not cap.isOpened():
            raise RuntimeError("No se pudo abrir la cámara")
        clase_anterior, consecutivas = None, 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            resultado = analizar_imagen(frame)
            clase = resultado["clase"]
            consecutivas = (consecutivas + 1 if clase == clase_anterior else 1) if clase else 0
            clase_anterior = clase
            texto = f"{clase or resultado['estado']} {resultado['confianza']:.0%} ({min(consecutivas, 3)}/3)"
            if consecutivas >= 3:
                texto += " CONFIRMADA"
            for x, y, confianza in resultado["keypoints"]:
                if confianza >= 0.5:
                    cv2.circle(frame, (int(x * frame.shape[1]), int(y * frame.shape[0])), 4, (0, 255, 0), -1)
            cv2.putText(frame, texto, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Pipeline de danzas - Q para salir", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
