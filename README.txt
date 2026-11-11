FACE ATTENDANCE SYSTEM - ALL-IN-ONE STARTER

1. Extract the ZIP.
2. Open the extracted folder in VS Code.
3. Open Terminal > New Terminal.
4. Run: py -m pip install flask opencv-python
5. Run: py app.py
6. Open: http://127.0.0.1:5000

Demo login:
Username: admin
Password: 1234

Included pages:
Login, Dashboard, Students, Register Student, Face Scan camera preview,
Attendance Reports with CSV download, and Activity Log.

Camera:
CAMERA_INDEX = 1 is set by default. If DroidCam does not appear, change it to 0
in app.py and restart the server.

Important:
- The sample student records are fictional and added automatically at first run.
- Demo credentials are hard-coded; this is not secure production authentication.
- Students page permits manual status updates for demonstration.
- Camera preview alone does not implement face recognition, blink/liveness checking,
  or automatic verified attendance.
- Keep app.py and attendance.db in the same folder. Back up any existing database.
