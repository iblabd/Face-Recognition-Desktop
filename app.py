import os
from tkinter import *
from dotenv import load_dotenv
from assets.controller import DatasetView, EncodeView, RecordView

# Load environment variables
load_dotenv()

class App(Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set window properties
        self.title("Present Time")
        self.state('zoomed')

        # Create menu bar
        self.menubar = Menu(self)

        # Create Home menu
        home_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='Home', menu=home_menu)
        home_menu.add_command(label='View dataset', command=lambda: self.show_frame(DatasetView))
        home_menu.add_command(label='Encode dataset...', command=lambda: self.show_frame(EncodeView))
        home_menu.add_separator()
        home_menu.add_command(label='Exit', command=self.destroy)

        # Create Record menu
        record_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='Record', menu=record_menu)
        record_menu.add_command(label='Start record...', command=lambda: self.show_frame(RecordView))
        record_menu.add_command(label='Stop record...', command=lambda: self.stop_encoding())
        

        # # Create Tools menu
        # tools_menu = Menu(self.menubar, tearoff=0)
        # self.menubar.add_cascade(label='Tools', menu=tools_menu)
        # tools_menu.add_command(label='Check database connection...', command=None)
        # tools_menu.add_command(label='Check network connection...', command=None)

        self.config(menu=self.menubar)

        # Create container frame
        container = Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        
        for frame_class in (DatasetView, EncodeView, RecordView):
            frame = frame_class(container, self)
            self.frames[frame_class] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(EncodeView)

    def stop_encoding(self):
            record_view = self.frames[RecordView]
            record_view.stop_video_capture()
            record_view.tkraise()

    def show_frame(self, frame_class):
        if frame_class == RecordView:
            record_view = self.frames[RecordView]
            record_view.start_video_capture()
            record_view.tkraise()
        else:
            record_view = self.frames[RecordView]
            record_view.stop_video_capture()
            frame = self.frames[frame_class]
            frame.tkraise()


if __name__ == "__main__":
    app = App()
    app.mainloop()

    pyinstaller --onefile --hidden-import cmake --hidden-import dlib --hidden-import face_recognition --hidden-import firebase_admin --hidden-import numpy --hidden-import opencv-python --hidden-import pendulum --hidden-import python-dotenv --hidden-import pyttsx3 --hidden-import termcolor app.py