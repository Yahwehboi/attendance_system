import cv2
from pyzbar.pyzbar import decode
from modules.attendance import mark_attendance_for_course, mark_attendance
import time

def start_scanner(status_callback=None, course_id=None):
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        msg = "❌ Camera not found."
        print(msg)
        if status_callback:
            status_callback(msg)
        return

    msg = "📷 Scanner started. Show QR code. Press Q to quit."
    print(msg)
    if status_callback:
        status_callback(msg)

    last_scan_time = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        for obj in decode(frame):
            student_id = obj.data.decode("utf-8")
            now = time.time()

            if student_id not in last_scan_time or \
               now - last_scan_time[student_id] > 3:

                last_scan_time[student_id] = now

                if course_id:
                    success, message = mark_attendance_for_course(
                        student_id, course_id)
                else:
                    success, message = mark_attendance(student_id)

                print(message)
                if status_callback:
                    status_callback(message)

                color = (0, 255, 0) if success else (0, 0, 255)
                points = obj.polygon
                if len(points) == 4:
                    pts = [(p.x, p.y) for p in points]
                    for i in range(4):
                        cv2.line(frame, pts[i], pts[(i+1) % 4], color, 3)

                x, y = obj.rect.left, obj.rect.top
                cv2.putText(frame, student_id, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.putText(frame, "Press Q to stop",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 0), 2)
        cv2.imshow("QR Attendance Scanner", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    msg = "📷 Scanner stopped."
    print(msg)
    if status_callback:
        status_callback(msg)