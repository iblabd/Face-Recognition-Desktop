from datetime import datetime
import pendulum
import pyttsx3
import sys
import os
import pickle
import cv2
import time
import face_recognition
import numpy as np
import pendulum

from pathlib import Path
sys.path.insert(0, str(Path(f"{os.getcwd()}\\app")).replace("\\", "/"))
from assets.firebase import Firebase

class Main:
    null_datetime = "0000-00-00 00:00:00"

    def __init__(self): 
        self.app = Firebase()
        self.currentdir  = os.getcwd()
    
    def datetime(self): 
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def say(self, say):
        tts = pyttsx3.init()
        tts.setProperty('voice', 'id-ID')
        tts.say(say)
        return tts.runAndWait()
    
    def insertIntoPresence(self, id):
        # - - - Status - - -
        # 0 -> No changes applied, most likely because had already made a presence
        # 1 -> Created new presence record with time_in today and null datetime for time_out
        # 2 -> Updated presence record with student_id = id on column time_out setted to current datetime
        has_time_in = self.has_time_in(id)
        has_time_out = self.has_time_out(id)

        timenow = self.datetime()
        today = timenow.split(" ")[0]
        latetime = today + " 07:01:00"

        reference_time = pendulum.parse(timenow)
        compare_time = pendulum.parse (latetime)
        
        
        if not has_time_in:
            self.app.ref = self.app.reference("gate_presence")
            
            if reference_time < compare_time:
                self.app.push({
                    "student_id": id,
                    "time_in": timenow,
                    "time_out": self.null_datetime,
                    "reason": "",
                    "status": 1
                })

            else:
                self.app.push({
                    "student_id": id,
                    "time_in": self.datetime(),
                    "time_out": self.null_datetime,
                    "reason": "",
                    "status": 7
                })
            print("Present has been stored to database.")
            return 1
            
        else: 
            message = "You had already made a presence today"
            self.say(message)
            print(message)
            return None
            
    def has_time_in(self, target):
        today = self.datetime().split(" ")[0]
        
        self.app.ref = self.app.reference("gate_presence")
        snap = self.app.select_from("gate_presence", [
            ["student_id", target]
        ])
        
        # Intersection method
        records = [each for each in snap if today in each.get("time_in")]
        return len(records) > 0
        
    def has_time_out(self, target):
        today = self.datetime().split(" ")[0]
        
        self.app.ref = self.app.reference("gate_presence")
        snap = self.app.select_from("gate_presence", [
            ["student_id", target]
        ])
        
        # Intersection method
        records = [each for each in snap if self.null_datetime not in each.get("time_out") and today in each.get("time_in")]
        
        return len(records) > 0
    
    def gen_frames(self):
        video_capture = cv2.VideoCapture(0)
        # video_capture.open(os.getenv("CAMERA_ADDRESS"))
        

        with open(os.getenv("DATASET"), "rb") as f:
            data = pickle.load(f)
            known_face_id = data["id"]
            known_face_encodings = data["encodings"]
            known_face_names = data["names"]
            print(f"Total student dataset: {len(known_face_names)}")

        # target = os.listdir(os.getenv("IMAGE_PATH"))
        # known_face_names = [os.path.splitext(string)[0] for string in target if string != ".gitignore"]
        # print(f"Total student images: {len(known_face_names)}")

        face_locations = []
        face_encodings = []
        face_names = []
        face_id = []
        target_face = []
        process_this_frame = False
        start_time = time.time()

        while True:
            success, frame = video_capture.read()

            if not success:
                break
            else:
                rgb_small_frame = frame

                if process_this_frame:
                    process_this_frame = False
                    print("processing...")
                    face_locations = face_recognition.face_locations(rgb_small_frame)
                    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                    face_names = []
                    face_id = []

                    for face_encoding in face_encodings:
                        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.65)
                        name = "Unknown"

                        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                        best_match_index = np.argmin(face_distances)

                        if matches[best_match_index]:
                            name = known_face_names[best_match_index]
                            id = known_face_id[best_match_index]
                            face_names.append(name)
                            face_id.append(id)
                            
                if len(face_names) != 0:
                    for name, id in zip(face_names, face_id):
                        if name != "Unknown":
                            target_face.append(id)
                            print(f"Detected face: {name}, Face id: {id}")
                            print(len(target_face))

                        if target_face.count(id) > 5:
                            print(target_face)
                            self.insertIntoPresence(int(id))
                            self.say(f"{name} face appear more than 5 times in list")
                            target_face.clear()


                if time.time() - start_time > 3:
                    start_time = time.time()
                    process_this_frame = True

            # Display the resulting image
            cv2.imshow('Video', frame)

            # Hit 'q' on the keyboard to quit!
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
        # Release handle to the webcam
        video_capture.release()
        # cv2.destroyAllWindows()