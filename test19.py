
import tkinter as tk
from tkinter import messagebox, ttk
import csv
import hashlib
import cv2
import face_recognition
import dlib
import numpy as np
import pyttsx3
import os
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import threading
import time
import winsound

# Text-to-speech setup
engine = pyttsx3.init()
engine.setProperty('rate', 150)

def speak(text):
    engine.say(text)
    engine.runAndWait()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# File paths and setup
admin_image_path = 'Sagu.jpg'
intruder_folder = 'Intruder'
os.makedirs(intruder_folder, exist_ok=True)

register_csv = 'registered_users.csv'
intruder_csv = 'intruders.csv'
attack_log_csv = 'attack_log.csv'

for file, headers in [
    (register_csv, ['Username', 'Password']),
    (intruder_csv, ['Time', 'Intruder_Image']),
    (attack_log_csv, ['Source IP', 'Destination IP', 'Attack Type'])
]:
    if not os.path.exists(file):
        with open(file, 'w', newline='') as f:
            csv.writer(f).writerow(headers)

class NIDSApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NIDS System")
        self.root.geometry("400x300")
        self.root.configure(bg="lightblue")

        tk.Label(self.root, text="Welcome to NIDS", font=("Arial", 16), bg="lightblue").pack(pady=20)
        tk.Button(self.root, text="Register", width=15, bg="lightgreen", command=self.register_form).pack(pady=10)
        tk.Button(self.root, text="Login", width=15, bg="lightyellow", command=self.login_form).pack(pady=10)

        self.root.mainloop()

    def register_form(self):
        self.root.destroy()
        reg = tk.Tk()
        reg.title("Register")
        reg.geometry("400x300")
        reg.configure(bg="lavender")

        tk.Label(reg, text="Username", bg="lavender").pack()
        username_entry = tk.Entry(reg)
        username_entry.pack()

        tk.Label(reg, text="Password", bg="lavender").pack()
        password_entry = tk.Entry(reg, show='*')
        password_entry.pack()

        tk.Label(reg, text="Confirm Password", bg="lavender").pack()
        confirm_entry = tk.Entry(reg, show='*')
        confirm_entry.pack()

        def register_user():
            username = username_entry.get()
            password = password_entry.get()
            confirm = confirm_entry.get()

            if password != confirm:
                messagebox.showerror("Error", "Passwords do not match")
                return

            hashed = hash_password(password)
            with open(register_csv, 'a', newline='') as f:
                csv.writer(f).writerow([username, hashed])

            messagebox.showinfo("Success", "Registration successful")
            reg.destroy()
            self.login_form()

        tk.Button(reg, text="Register", command=register_user, bg="lightgreen").pack(pady=10)

    def login_form(self):
        login = tk.Tk()
        login.title("Login")
        login.geometry("400x250")
        login.configure(bg="lightyellow")

        tk.Label(login, text="Username", bg="lightyellow").pack()
        username_entry = tk.Entry(login)
        username_entry.pack()

        tk.Label(login, text="Password", bg="lightyellow").pack()
        password_entry = tk.Entry(login, show='*')
        password_entry.pack()

        def login_user():
            username = username_entry.get()
            password = hash_password(password_entry.get())
            with open(register_csv, 'r') as f:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    if row == [username, password]:
                        messagebox.showinfo("Success", "Login successful")
                        login.destroy()
                        self.blink_verification()
                        return
            messagebox.showerror("Error", "Invalid credentials")

        tk.Button(login, text="Login", command=login_user, bg="lightgreen").pack(pady=10)

    def blink_verification(self):
        speak("Blink twice to verify")
        known_image = face_recognition.load_image_file(admin_image_path)
        known_encoding = face_recognition.face_encodings(known_image)[0]

        cap = cv2.VideoCapture(0)
        detector = dlib.get_frontal_face_detector()
        predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        blink_count = 0
        EAR_THRESHOLD = 0.25
        CONSEC_FRAMES = 3
        frame_counter = 0

        def eye_aspect_ratio(eye):
            A = np.linalg.norm(eye[1] - eye[5])
            B = np.linalg.norm(eye[2] - eye[4])
            C = np.linalg.norm(eye[0] - eye[3])
            return (A + B) / (2.0 * C)

        while True:
            ret, frame = cap.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector(gray)

            for face in faces:
                shape = predictor(gray, face)
                coords = np.array([[p.x, p.y] for p in shape.parts()])
                left_eye = coords[42:48]
                right_eye = coords[36:42]
                ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0

                if ear < EAR_THRESHOLD:
                    frame_counter += 1
                else:
                    if frame_counter >= CONSEC_FRAMES:
                        blink_count += 1
                        speak(f"Blink {blink_count} detected")
                    frame_counter = 0

            face_encodings = face_recognition.face_encodings(frame)
            if face_encodings:
                match = face_recognition.compare_faces([known_encoding], face_encodings[0])[0]
                if blink_count >= 2 and match:
                    cap.release()
                    cv2.destroyAllWindows()
                    self.dashboard()
                    return
                elif not match:
                    speak("Intruder alert. Access denied")
                    now = datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = os.path.join(intruder_folder, f"intruder_{now}.jpg")
                    cv2.imwrite(filename, frame)
                    with open(intruder_csv, 'a', newline='') as f:
                        csv.writer(f).writerow([datetime.now(), filename])

            cv2.putText(frame, f"Blink Count: {blink_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
            cv2.imshow("Verify Admin", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    def dashboard(self):
        dash = tk.Tk()
        dash.title("NIDS Dashboard")
        dash.geometry("1000x600")

        tk.Button(dash, text="Logout", command=lambda: [dash.destroy(), self.__init__()], bg="lightcoral").pack(anchor='ne', pady=5, padx=5)

        columns = ('Source IP', 'Destination IP', 'Attack Type')
        tree = ttk.Treeview(dash, columns=columns, show='headings')
        for col in columns:
            tree.heading(col, text=col)
        tree.pack(side='left', fill='both', expand=True)

        fig, ax = plt.subplots()
        canvas = FigureCanvasTkAgg(fig, master=dash)
        canvas.get_tk_widget().pack(side='right', fill='both', expand=True)

        last_count = [0]

        def vibration_sound():
            # Loud vibration style sound with rapid beeps
            for _ in range(7):
                winsound.Beep(1500, 100)
                time.sleep(0.05)
                winsound.Beep(1200, 100)
                time.sleep(0.05)

        def update_dashboard():
            attack_counts = {'dos': 0, 'mitm': 0, 'sql injection': 0,  'zero day': 0}
            while True:
                if os.path.exists(attack_log_csv):
                    with open(attack_log_csv, 'r') as f:
                        reader = csv.reader(f)
                        next(reader)
                        rows = list(reader)
                        # Update treeview with current attack entries
                        tree.delete(*tree.get_children())
                        for row in rows:
                            tree.insert('', 'end', values=row)

                        # Count attacks by type (case insensitive)
                        for key in attack_counts:
                            attack_counts[key] = sum(1 for row in rows if row[2].lower() == key)

                        # If new attack detected, play vibration alert
                        if len(rows) > last_count[0]:
                            vibration_sound()
                            last_count[0] = len(rows)

                    # Update bar chart with latest counts
                    ax.clear()
                    ax.bar(attack_counts.keys(), attack_counts.values(), color=['red', 'orange', 'blue', 'green'])
                    ax.set_title("Attack Counts")
                    ax.set_ylabel("Count")
                    canvas.draw()

                time.sleep(3)

        threading.Thread(target=update_dashboard, daemon=True).start()
        dash.mainloop()

if __name__ == "__main__":
    NIDSApp()
