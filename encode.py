import logging
import os
from dotenv import load_dotenv
from assets.firebase import Firebase
import face_recognition
import pickle
import cv2
from tqdm import tqdm

# Setup logging
logging.basicConfig(level=logging.DEBUG if os.getenv("DEBUG_MODE") == "True" else logging.INFO)

#load environment files
load_dotenv()

db = Firebase()
logging.info("Successfully connected to database.")

#get image directory path
logging.info("Getting all image...")

image_path = os.getenv("IMAGE_PATH")
image_reference = os.listdir(image_path)

#remove .gitignore files from array
if(".gitignore" in image_reference):
    image_reference.remove(".gitignore")

logging.info(f"{len(image_reference)} images are in this directory.")

id = [os.path.splitext(string)[0] for string in image_reference]

images = {}
known_id = []
known_name = []
image_face_encoding = []
tasknum = 0

# Load existing dataset
try:
    with open("yamori.bin", "rb") as f:
        existing_data = pickle.load(f)
    known_id = existing_data["id"]
    known_name = existing_data["names"]
    image_face_encoding = existing_data["encodings"]
except:
    logging.info("No existing dataset found, creating new one.")

for reference_id in tqdm(id):
    if reference_id in known_id:
        logging.info(f"{reference_id} has already been encoded, skipping...")
        continue

    try:
        #Converting image
        images[reference_id] = cv2.imread(os.path.join(image_path, f"{reference_id}.jpg"))
        rgb = cv2.cvtColor(images[reference_id], cv2.COLOR_BGR2RGB)
    except Exception as e:
        logging.error(f"Error reading or converting {reference_id} image, Error: {e}")
        continue

    # Detecting face in image
    boxes = face_recognition.face_locations(rgb, model='hog')
    logging.debug(f"Face has been detected in {reference_id} image.")
    
    # Encoding image
    encodings = face_recognition.face_encodings(rgb, boxes)
    logging.debug(f"{reference_id} has been encoded.")

    # Searching person in database
    try:
        person = db.select_from("users", [["id", int(reference_id)]])[0]
        name = person.get("name").title()
        logging.debug(f"{reference_id} has found.")
    except Exception as e:
        logging.error(f"Error while uploading to Firebase. Related issue with {reference_id}. Error: {e}")

    for encoding in encodings:
        image_face_encoding.append(encoding)
        known_id.append(reference_id)
        known_name.append(name)
        tasknum += 1
    logging.info(f"Successfully encoded {reference_id}.")

data = {"id": known_id, "names": known_name, "encodings": image_face_encoding}

#use pickle to save data into a file for later use
logging.info(f"Creating dataset...")
with open("yamori.bin", "wb") as f:
    pickle.dump(data, f)
logging.info(f"Dataset created.")
