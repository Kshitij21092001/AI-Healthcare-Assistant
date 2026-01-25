from doctor_engine import init_db, add_doctor

init_db()

add_doctor("Dr. Ankit Sharma", "General Physician", "99999-11111","kshitijphotos1@gmail.com")
add_doctor("Dr. Raman Verma", "General Physician", "99999-22222", "kshitijphotos1@gmail.com")
add_doctor("Dr. Seema Gupta", "Hematology", "99999-33333", "kshitijphotos1@gmail.com")
add_doctor("Dr. Priya Mehta", "Infectious Disease", "99999-44444", "kshitijphotos1@gmail.com")
add_doctor("Dr. Kiran Yadav", "Endocrinology", "99999-55555", "kshitijphotos1@gmail.com")
add_doctor("Dr. Harshit Jain", "Nephrology", "99999-66666", "kshitijphotos1@gmail.com")
add_doctor("Dr. Rohit Mishra", "Cardiology", "99999-77777", "kshitijphotos1@gmail.com")
add_doctor("Dr. Neha Kapoor", "Pathology", "99999-88888", "kshitijphotos1@gmail.com")

print("Doctors database initialized.")
