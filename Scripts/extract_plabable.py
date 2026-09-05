import os
from utils import extractTextFromPDF, extractQuestionsFromTXT
from utils import create_database, insert_questions
from utils import saveQuestionsToJson

data_dir = "Data/Plabable/Topics"
txt_dir = "Data/Plabable/Topics/txts"
json_dir = "Data/Plabable/Topics/json"

if not os.path.exists(txt_dir):
    os.makedirs(txt_dir)

if not os.path.exists(json_dir):
    os.makedirs(json_dir)


files = []
for pdf_filename in os.listdir(data_dir):
    if pdf_filename.endswith('.pdf'):
        full_path = os.path.join(data_dir, pdf_filename)
        files.append(full_path)


for file in files:
    extractTextFromPDF(file, txt_dir)

if os.path.exists("Data/Plabable/questions.db"):
    # Delete the existing database file
    os.remove("Data/Plabable/questions.db")

create_database("Data/Plabable/questions.db")

for txt_filename in os.listdir(txt_dir):
    if txt_filename.endswith('.txt'):
        full_path = os.path.join(txt_dir, txt_filename)
        questions = extractQuestionsFromTXT(full_path)

        print(f"{os.path.splitext(txt_filename)[0]} -> {len(questions)}")

        saveQuestionsToJson(questions, os.path.join(json_dir, txt_filename.replace('.txt', '.json')))        
        insert_questions(questions, "Data/Plabable/questions.db")

