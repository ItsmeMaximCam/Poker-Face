import cv2
from vision import analyze, draw

cap = cv2.VideoCapture(0)

while True:
    ok, frame = cap.read()
    if not ok:
        print("Couldn't read from webcam")
        break

    frame = cv2.flip(frame, 1)  #mirror so it feels natural

    features, landmarks = analyze(frame)
    draw(frame, features, landmarks)

    cv2.imshow("Webcam :p", frame)
    
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()