from tkinter import *
from tkinter import ttk
import PIL.Image, PIL.ImageTk
from datetime import datetime
import os
from dotenv import load_dotenv
from assets.firebase import Firebase
import face_recognition
import pickle
import cv2
import face_recognition
import numpy as np
import pendulum
import time
import sys
import pyttsx3
import threading

from pathlib import Path
sys.path.insert(0, str(Path(f"{os.getcwd()}\\app")).replace("\\", "/"))


db = Firebase()

class HomeView(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)

        self.controller = controller

class RecordView(Frame,):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)

        self.controller = controller
        self.currentdir  = os.getcwd()
        
        self.null_datetime = "0000-00-00 00:00:00"
        self.today = self.datetime().split(" ")[0]
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

        # Create a canvas that can fit the above video source size
        self.canvas = Label(self, width=self.screen_width, height=self.screen_height)
        self.canvas.pack()

        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.face_id = []
        self.target_face = []
        self.process_this_frame = True
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.video_capture = None

        try:
            with open(os.getenv("DATASET"), "rb") as f:
                self.data = pickle.load(f)
                self.known_face_id = self.data["id"]
                self.known_face_encodings = self.data["encodings"]
                self.known_face_names = self.data["names"]
                print(f"Total student dataset: {len(self.known_face_names)}")
        except (FileNotFoundError, EOFError):
            print("Error: the file does not exist or is empty.")
            self.data = []
        
    
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
        latetime = self.today + " 07:01:00"

        reference_time = pendulum.parse(timenow)
        compare_time = pendulum.parse (latetime)
        
        
        if not has_time_in:
            db.ref = db.reference("gate_presence")
            
            if reference_time < compare_time:
                db.push({
                    "student_id": id,
                    "time_in": timenow,
                    "time_out": self.null_datetime,
                    "reason": "",
                    "status": 1
                })

            else:
                db.push({
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
        db.ref = db.reference("gate_presence")
        snap = db.select_from("gate_presence", [
            ["student_id", target]
        ])
        
        # Intersection method
        records = [each for each in snap if self.today in each.get("time_in")]
        return len(records) > 0
        
    def has_time_out(self, target):
        db.ref = db.reference("gate_presence")
        snap = db.select_from("gate_presence", [
            ["student_id", target]
        ])
        
        # Intersection method
        self.records = [each for each in snap if self.null_datetime not in each.get("time_out") and self.today in each.get("time_in")]
        
        return len(self.records) > 0
    
    def start_video_capture(self):
        print("Start video capture...")

        try:
            # Start the video capture
            self.video_capture = cv2.VideoCapture(0)

            # Schedule the first call to show_frame
            self.after(0, self.gen_frames)
        except Exception:
            print(Exception)
    
    def stop_video_capture(self):
        if self.video_capture != None:
            self.video_capture.release()
    
    def gen_frames(self):
        success, frame = self.video_capture.read()
        if success:

            if time.time() - self.start_time > 2:
                self.start_time = time.time()
                print("Detecting...")
                self.face_locations = face_recognition.face_locations(frame)
                self.face_encodings = face_recognition.face_encodings(frame, self.face_locations)
                self.face_names = []
                self.face_id = []
                self.thread2 = threading.Thread(target=self.process_frame, args=(self.face_encodings,))
                self.thread2.start()
                
                        
            with self.lock:
                if len(self.face_names) != 0:
                    for name, id in zip(self.face_names, self.face_id):
                        if name != "Unknown":
                            self.target_face.append(id)
                            print(f"Detected face: {name}, Face id: {id}")
                            print(len(self.target_face))
                        if self.target_face.count(id) > 5:
                            print(self.target_face)
                            self.insertIntoPresence(int(id))
                            self.say(f"{name} face appear more than 5 times in list")
                            self.target_face.clear()

            self.thread3 = threading.Thread(target=self.display_frame, args=(frame,))
            self.thread3.start()
    
    def process_frame(self, face_encodings):
        for face_encoding in face_encodings:
            self.matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.9)
            self.name = "Unknown"
            self.face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            self.best_match_index = np.argmin(self.face_distances)

            if self.matches[self.best_match_index]:
                with self.lock:
                    self.name = self.known_face_names[self.best_match_index]
                    self.id = self.known_face_id[self.best_match_index]
                    self.face_names.append(self.name)
                    self.face_id.append(self.id)
    
    def display_frame(self, frame):
        # Convert the frame to RGB color
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Resize the frame
        frame = cv2.resize(frame, (self.screen_width, self.screen_height))
        # Convert the frame to a PhotoImage object
        frame = PIL.ImageTk.PhotoImage(PIL.Image.fromarray(frame))
        # Display the frame on the canvas
        self.canvas.config(image=frame)
        self.canvas.image = frame
        # Schedule the next call to show_frame
        self.after(30, self.gen_frames)
    

class EncodeView(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)

        # Initialize variables
        self.controller = controller
        self.images = {}
        self.known_id = []
        self.known_name = []
        self.image_face_encoding = []
        self.tasknum = 0
        self.enc = FALSE
        self.width = int(self.winfo_screenwidth())
        self.height = int(self.winfo_screenheight())

        # Getting all images from imageset directory
        self.image_path = os.getenv("IMAGE_PATH")
        self.image_reference = os.listdir(self.image_path)

        if(".gitignore" in self.image_reference):
            self.image_reference.remove(".gitignore")
        
        self.id = [os.path.splitext(string)[0] for string in self.image_reference]

        self.top_frame = Frame(self, width=self.width, height=self.height * 0.2, bg="white")
        self.label_encode = Label(self, text="Encode Image", width= self.width, background="white", anchor=W, padx=self.width * 0.04, font=("", 16, "bold")).pack()
        
        self.max_task = len(self.image_reference)
        self.percent = 0.0
        Label(self, text=f"Total image in directory: {len(self.image_reference)}", width= self.width, background="white", anchor=W, padx=self.width * 0.04).pack()
        self.dataset_count = Label(self, text=f"Total dataset in directory: 0", width= self.width, background="white", anchor=W, padx=self.width * 0.04)
        self.dataset_count.pack()
        Label(self, text="", width= self.width, background="white", anchor=W, padx=self.width * 0.04, pady=4).pack()
        self.open_bin()
        
       
        self.open_bin()
        
        
        self.loadinglabel = Label(self, text = None)
        self.loadingbar = ttk.Progressbar(self, orient = HORIZONTAL, length = self.width * 0.96,  mode = 'determinate')
        self.loadingbar["maximum"] = self.max_task

        self.percentage = Label(self, text = None)

        self.start_encode = Button(self, text="Start Encode", command= lambda: self.start_encoding(), width= self.width, background="blue", fg="white", anchor=E, padx=self.width * 0.04)
        self.start_encode.pack()
        self.stop_encode = Button(self, text="Stop Encode", command= lambda: self.stop_encoding(), width= self.width, background="gray", fg="white", anchor=E, padx=self.width * 0.04)
    
    def open_bin(self):
         # Load existing dataset
        try:
            with open(os.getenv("DATASET"), "rb") as f:
                self.existing_data = pickle.load(f)
            self.known_id = self.existing_data["id"]
            self.known_name = self.existing_data["names"]
            self.image_face_encoding = self.existing_data["encodings"]
            self.dataset_count.config(text=f"Total dataset in directory: {len(self.known_id)}")
            self.update_idletasks()
        except:
            self.dataset_count.config(text=f"Total dataset in directory: 0")
    
    def start_encoding(self):
        self.start_encode.pack_forget()
        self.stop_encode.pack()
        self.thread = threading.Thread(target=self.encode)
        self.thread.start()
    
    def stop_encoding(self):
        self.stop_encode.pack_forget()
        self.start_encode.pack()
        self.enc = FALSE
        self.loadinglabel.pack_forget()
        self.loadingbar.pack_forget()
        self.percentage.pack_forget()
        

    def encode(self):
        self.enc = TRUE

        if self.enc == TRUE:
            self.loadinglabel.pack()
            self.loadingbar.pack()
            percentage = (self.tasknum / self.max_task) * 100
            self.percentage.config(text = f"{round(percentage, 1)}%")
            self.percentage.pack()
            self.loadinglabel.config(text = "Preparing encoding...")
            self.update_idletasks()

            
            self.thread = threading.Thread(target=self.create_dataset)
            self.thread.start()
            
    # Skipping already existing dataset
    def create_dataset(self):

        for reference_id in self.id:
            if self.enc == False:
                continue

            if reference_id in self.known_id:
                self.loadinglabel.config(text = f"{reference_id} has already been encoded, skipping...")
                self.tasknum += 1
                self.loadingbar['value'] = self.tasknum
                percentage = (self.tasknum / self.max_task) * 100
                self.percentage.config(text = f"{round(percentage, 1)}%")
                self.update_idletasks()
                continue
            
            # Converting image
            try:
                self.loadinglabel.config(text = f"Converting {reference_id}...")
                self.update_idletasks()
                self.images[reference_id] = cv2.imread(os.path.join(self.image_path, f"{reference_id}.jpg"))
                rgb = cv2.cvtColor(self.images[reference_id], cv2.COLOR_BGR2RGB)
                self.loadinglabel.config(text = f"{reference_id} Has been converted.")
                self.update_idletasks()
            except Exception as e:
                self.loadinglabel.config(text = f"Error reading or converting {reference_id} image, Error: {e}")
                self.update_idletasks()
                continue
            
            # Detecting face in image
            self.loadinglabel.config(text = f"Detecting face in {reference_id}...")
            self.update_idletasks()
            boxes = face_recognition.face_locations(rgb, model='hog')
            self.loadinglabel.config(text = f"Face has been detected in {reference_id} image.")
            self.update_idletasks()
            # Encoding image
            self.loadinglabel.config(text = f"Encoding {reference_id}...")
            self.update_idletasks()
            encodings = face_recognition.face_encodings(rgb, boxes)
            self.loadinglabel.config(text = f"{reference_id} has been encoded.")
            self.update_idletasks()
            # Searching person in database
            try:
                person = db.select_from("users", [["id", int(reference_id)]])[0]
                name = person.get("name").title()
                self.loadinglabel.config(text = f"{reference_id} has found.")
            except Exception as e:
                self.loadinglabel.config(text = f"Error while uploading to Firebase. Related issue with {reference_id}. Error: {e}")
            for encoding in encodings:
                self.image_face_encoding.append(encoding)
                self.known_id.append(reference_id)
                self.known_name.append(name)
                self.tasknum += 1
                self.loadingbar["value"] = self.tasknum
                percentage = (self.tasknum / self.max_task) * 100
                self.percentage.config(text = f"{round(percentage, 1)}%")
                self.update_idletasks()
            self.loadinglabel.config(text = f"Successfully encoded {reference_id}.")
            self.update_idletasks()
        
            self.loadinglabel.config(text = f"Saving datasets...")
            self.update_idletasks()

            data = {"id": self.known_id, "names": self.known_name, "encodings": self.image_face_encoding}
            with open(os.getenv("DATASET"), "wb") as f:
                pickle.dump(data, f)

            self.loadinglabel.config(text = "dataset has been saved.")
            self.update_idletasks()
            self.open_bin()
    
        self.tasknum = 0
        self.loadinglabel.config(text = "Completed encoding.")
        time.sleep(3)
        self.loadinglabel.pack_forget()
        self.loadingbar.pack_forget()
        self.percentage.pack_forget()
        self.stop_encoding()

class DatasetView(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)

        self.controller = controller

        self.width = int(self.winfo_screenwidth())
        self.height = int(self.winfo_screenheight())

        self.dataset = ttk.Treeview(self, height=self.height)
        self.dataset['columns'] = ('num', 'nis', 'name')

        self.dataset.column("#0", width=0,  stretch=NO)
        self.dataset.column("num",anchor=CENTER, width=round(self.width * 0.1))
        self.dataset.column("nis",anchor=CENTER, width=round(self.width * 0.2))
        self.dataset.column("name",anchor=W, width=round(self.width * 0.7))

        self.dataset.heading("#0",text="",anchor=CENTER)
        self.dataset.heading("num",text="Num.",anchor=CENTER)
        self.dataset.heading("nis",text="NIS",anchor=CENTER)
        self.dataset.heading("name",text="Name",anchor=CENTER)
        
        try:
            with open(os.getenv("DATASET"), "rb") as f:
                self.data = pickle.load(f)
        except (FileNotFoundError, EOFError):
            print("Error: the file does not exist or is empty.")
            self.data = []
        
        if len(self.data) > 1:
            for i, nis, name in zip(range(len(self.data["id"])), self.data["id"], self.data["names"]):
                self.dataset.insert(parent='', index='end', iid=i, values=(f"{i + 1}", f"{nis}", f"{name}"))

            self.dataset.pack()
        else:
            Label(self, text="Dataset is empty!").pack()
        