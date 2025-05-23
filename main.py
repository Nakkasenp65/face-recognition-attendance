import datetime
import os.path
import subprocess
import tkinter as tk
import util
import cv2
import numpy as np
from PIL import Image, ImageTk

import face_recognition
import customtkinter as ctk
from customtkinter import CTkImage


import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage



class App:

    

   

    def __init__(self):
        
        self.db_dir = './db'
        total_known_faces = 0
        for path in os.listdir(self.db_dir):
            if path.endswith('.jpg'):
                total_known_faces += 1
        print('Total local registered face: ',total_known_faces)

        self.bucket = storage.bucket()
        self.ref = db.reference('Students')
        
        self.total_student_object = self.ref.get()
        if self.total_student_object is None:
            self.student_id = 0
        else:
            self.student_id = len(self.ref.get())-1
        print('Total firebase registered student: ', self.student_id)

        if total_known_faces != self.student_id:
            print('Syncing database images with localdb...')
            self.sync_database_images_with_localdb()
            print('Syncing completed.')
        else: 
            print('Database images and localdb are synced.')
            print('Starting app...')

        self.main_window = tk.Tk()
        self.main_window.geometry("960x500+350+100")
        self.main_window.title("Face Recognition")

        self.show_total_students_label = util.get_text_ctk_label(self.main_window, 'Total students: ', 16, 'black')
        self.show_total_students_label.place(x=720, y=70)

        self.show_total_students_label = util.get_text_ctk_label(self.main_window, str(self.student_id), 16, 'black')
        self.show_total_students_label.place(x=850, y=70)

        self.title_text_main_window = util.get_text_ctk_label(self.main_window, "Face Recognition", 24, "black")
        self.title_text_main_window.place(x=720, y=20)

        self.login_button_main_window = util.get_ctk_button(self.main_window, "Login", "black", self.login )
        self.login_button_main_window.place(x=820, y=325)

        self.register_button_main_window = util.get_ctk_button(self.main_window, "Register", "black", self.register_new_user )
        self.register_button_main_window.place(x=820, y=385)

        self.show_profile_button_new_user_window = util.get_ctk_button(self.main_window, 'Profile','blue', self.show_profile)
        self.show_profile_button_new_user_window.place(x=820, y=445)

        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(x=10, y=0, width=700, height=500)

        self.add_webcam(self.webcam_label)

        if not os.path.exists(self.db_dir):
            os.mkdir(self.db_dir)

    def sync_database_images_with_localdb(self):
        # total_student = self.student_id
        for i in range(1, self.student_id+1):
            blob = self.bucket.get_blob(f'Images/{i}.jpg')
            array = np.frombuffer(blob.download_as_string(), np.uint8)
            imgStudent = cv2.imdecode(array, cv2.COLOR_BGRA2BGR)
            cv2.imwrite(os.path.join(self.db_dir, str(i) + '.jpg'), imgStudent)
            print(i, '.jpg sync')


    def add_webcam(self, label):
        if 'cap' not in self.__dict__:
            self.cap = cv2.VideoCapture(0)

        self._label = label

        self.process_webcam()

    def process_webcam(self):

        ret, frame = self.cap.read()
        self.most_recent_capture_arr = frame
        img_ = cv2.cvtColor(self.most_recent_capture_arr, cv2.COLOR_BGR2RGB)
        self.most_recent_capture_pil = Image.fromarray(img_)
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)

        self._label.imgtk = imgtk
        self._label.configure(image=imgtk)

        self._label.after(20, self.process_webcam)

    def login(self):
        unknown_img_path = './.tmp.jpg'

        cv2.imwrite(unknown_img_path, self.most_recent_capture_arr)

        output = str(subprocess.check_output(['face_recognition', self.db_dir, unknown_img_path]))
        print(output)
        static_student_id = output.split(',')[1][:-3]
        print(static_student_id)

        try:
            check_id = int(static_student_id)
            os.remove(unknown_img_path)
        except ValueError:
            util.show_error("Sorry, no face detected.\n\nPlease, Try again.")
            os.remove(unknown_img_path)
            return

        student_already_attended = self.ref.child(static_student_id).get()['last_attendance']
        student_already_attended = student_already_attended.split(' ')[0]
        if  student_already_attended == datetime.datetime.now().strftime("%d/%m/%Y"):
            util.show_checkmark("You already attended today.")
            return
        else :
            student_name = self.ref.child(static_student_id).get()['name']
            student_name = student_name.split(' ')[0]

            total_attendance = self.ref.child(static_student_id).get()['total_attendance']
            total_attendance += 1

            last_attendance = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            self.ref.child(static_student_id).update({'last_attendance': last_attendance,
                                                      'total_attendance': total_attendance})
            print('Student ID: ', static_student_id)
            notification = "Hello again, "+student_name+"\nDate: "+last_attendance
            util.show_checkmark(notification)

    def show_profile(self):
        unknown_img_path = './.tmp.jpg'

        cv2.imwrite(unknown_img_path, self.most_recent_capture_arr)

        output = str(subprocess.check_output(['face_recognition', self.db_dir, unknown_img_path]))
        os.remove(unknown_img_path)
        print(output)
        static_student_id = output.split(',')[1][:-3]
        print(static_student_id)

        if static_student_id.__contains__("unknown_person"):
            util.show_error("Sorry, you are not registered.\n\nTry registering first.")
            return
        elif static_student_id.__contains__("no_persons_found"):
            util.show_error("Sorry, no face detected.\n\nPlease, Try again")
            return
        else:
            pass

        student_data = self.ref.child(static_student_id).get()
        if student_data is None:
            util.show_error("Error retrieving student information.")
            return

        student_name = student_data.get('name', 'N/A')
        student_major = student_data.get('major', 'N/A')
        student_starting_year = student_data.get('starting_year', 'N/A')
        student_year = student_data.get('year', 'N/A')
        student_total_attendance = student_data.get('total_attendance', 'N/A')
        student_last_attendance = student_data.get('last_attendance', 'N/A')

        student_information = (
            "Student id: " + static_student_id
            + "\nName: " + student_name
            + "\nMajor: " + student_major
            + "\nStarting year: " + student_starting_year
            + "\nYear: " + str(student_year)
            + "\nTotal attendance: " + str(student_total_attendance)
            + "\nLast attendance: " + student_last_attendance
        )

        self.register_new_user_window = ctk.CTkToplevel(self.main_window)
        self.register_new_user_window.geometry("1200x520+370+120")
        self.register_new_user_window.resizable(False, False)
        self.register_new_user_window.title("Register New User")
        self.register_new_user_window.configure(bg='white')

        self.capture_label = util.get_img_label(self.register_new_user_window)
        self.capture_label.place(x=10, y=0, width=700, height=500)

        self.add_profile_img_to_label(static_student_id, self.capture_label)

        self.profile_label_register_new_user = util.get_text_ctk_label(self.register_new_user_window, 'Profile', 24, 'white')
        self.profile_label_register_new_user.place(x=750, y=20)

        self.information_label_register_new_user = util.get_information_text_ctk_label(self.register_new_user_window, student_information, 24, 'white')
        self.information_label_register_new_user.place(x=750, y=60)

    def register_new_user(self):

        is_no_face = False
        is_registered = False
        unknown_img_path = './.tmp.jpg'

        cv2.imwrite(unknown_img_path, self.most_recent_capture_arr)
        output = str(subprocess.check_output(['face_recognition', self.db_dir, unknown_img_path]))
        print(output)
        os.remove(unknown_img_path)
        if output.__contains__("unknown_person"):
            is_registered = False
        elif output.__contains__("no_persons_found"):
            is_no_face = True
        else:
            is_registered = True

        if is_registered:
            print(is_registered)
            util.show_error("You are already registered.")
            return
        elif is_no_face:
            print(is_no_face)
            util.show_error("Sorry, no face detected.\n\nPlease, Try again.")
            return
        else:


            '#custom tkinter window'
            self.register_new_user_window = ctk.CTkToplevel(self.main_window)
            self.register_new_user_window.geometry("1200x520+370+120")
            self.register_new_user_window.resizable(False, False)
            self.register_new_user_window.title("Register New User")

            '#accept button'
            self.accept_button_register_new_user_window = util.get_ctk_button(self.register_new_user_window, 'Accept', 'green', self.accept_register_new_user)
            self.accept_button_register_new_user_window.place(x=750, y=450)

            '#try again button'
            self.try_again_button_register_new_user_window = util.get_ctk_button(self.register_new_user_window, 'Try Again', 'red', self.try_again_register_new_user)
            self.try_again_button_register_new_user_window.place(x=930, y=450)

            '#capture label'
            self.capture_label = util.get_img_label(self.register_new_user_window)
            self.capture_label.place(x=10, y=0, width=700, height=500)

            self.add_img_to_label(self.capture_label)

            '# Name Field'
            self.name_entry_label_register_new_user = util.get_text_ctk_label(self.register_new_user_window, 'Full name:', 16, 'white')
            self.name_entry_label_register_new_user.place(x=770, y=40)

            self.name_entry_text_register_new_user = util.get_entry_input(self.register_new_user_window, 'Your name')
            self.name_entry_text_register_new_user.place(x=750, y=70)

            '# Faculty Field'
            self.major_entry_label_register_new_user = util.get_text_ctk_label(self.register_new_user_window, 'Major:', 16, 'white')
            self.major_entry_label_register_new_user.place(x=770, y=160)

            self.major_entry_text_register_new_user = util.get_combobox(self.register_new_user_window)
            self.major_entry_text_register_new_user.place(x=750, y=190)

            '# Starting Year Field'
            self.starting_year_label_register_new_user = util.get_text_ctk_label(self.register_new_user_window, 'Starting Year:', 16, 'white')
            self.starting_year_label_register_new_user.place(x=770, y=280)

            self.starting_year_entry_text_register_new_user = util.get_entry_input(self.register_new_user_window, 'Starting year')
            self.starting_year_entry_text_register_new_user.place(x=750, y=310)



    def try_again_register_new_user(self):
        self.register_new_user_window.destroy()

    def add_img_to_label(self, label):
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        label.imgtk = imgtk
        label.configure(image=imgtk)

        self.register_new_user_capture = self.most_recent_capture_arr.copy()

    def add_profile_img_to_label(self, number_id, label):

        profile_img = cv2.imread(os.path.join(self.db_dir, str(number_id) + '.jpg'))
        img_ = cv2.cvtColor(profile_img, cv2.COLOR_BGR2RGB)
        profile_img = Image.fromarray(img_)

        imgtk = ImageTk.PhotoImage(image=profile_img)
        label.imgtk = imgtk
        label.configure(image=imgtk)

    def start(self):
        self.main_window.mainloop()

    def add_to_db(self,name, major, starting_year, student_id):
        ref= db.reference('Students')
        data = {
            'name': name,
            'major': major,
            'starting_year': starting_year,
            'year': 2023 - int(starting_year),
            'total_attendance': 0,
            'last_attendance': 'Never'
        }
        ref.child(str(student_id)).set(data)

    
    def upload_image(self, fileName):
        bucket = storage.bucket()
        blob = bucket.blob('Images/' + fileName)
        blob.upload_from_filename(os.path.join(self.db_dir, fileName))

    def accept_register_new_user(self):

        name = self.name_entry_text_register_new_user.get()
        major = self.major_entry_text_register_new_user.get()
        starting_year = self.starting_year_entry_text_register_new_user.get()

        if not name or not major or not starting_year:
            util.empty_fields(self.register_new_user_window)
            print("Please fill in all fields.")
            return

        else:
            self.student_id += 1
            cv2.imwrite(os.path.join(self.db_dir, str(self.student_id) + '.jpg'), self.register_new_user_capture)
            print(f'Images/' + str(self.student_id) + '.jpg')
            file_name = str(self.student_id) + '.jpg'
            self.upload_image(file_name)
            self.add_to_db(name, major, starting_year, self.student_id)

            self.show_total_students_label.configure(text=str(self.student_id))
            util.show_checkmark("Registered success.")
            self.register_new_user_window.destroy()


if __name__ == "__main__":
    app = App()
    app.start()
