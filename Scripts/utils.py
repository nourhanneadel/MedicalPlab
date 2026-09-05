import os
import re

import sqlite3
import pdfplumber

def extractTextFromPDF(path_to_pdf, txt_dir, verbose=False):
    ''' This function takes a path to a pdf and extracts it to a text file with same name.txt '''

    if path_to_pdf.endswith('.pdf'):
        with pdfplumber.open(path_to_pdf) as pdf:
            dir_path = os.path.dirname(path_to_pdf)
            base_name = os.path.splitext(os.path.basename(path_to_pdf))[0]

            txt_file_path = os.path.join(txt_dir, base_name + '.txt')

            with open(txt_file_path, 'w', encoding='utf-8') as txt:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        txt.write(text + '\n')
            if verbose:
                print(f"Extracted text from {path_to_pdf} to {txt_file_path}")



def extractQuestionsFromTXT(path_to_txt):
    ''' 
    This function takes a text file and outputs a list of dictionaries with keys:
    ['Q', 'Question', 'Choices', 'Answer', 'Explanation', 'Topic'] 
    '''

    with open(path_to_txt, 'r', encoding='utf-8') as txt:
        text = txt.read()

    base_name = os.path.splitext(os.path.basename(path_to_txt))[0]

    # Split into blocks starting with Q-1, Q-2, etc.
    blocks = re.split(r"\nQ-\d+\s*\n", text)[1:]  # Skip header

    result = []

    for i, block in enumerate(blocks):
        # Extract ANSWER and EXPLANATION
        answer_match = re.search(r"ANSWER:\s*(.*?)\n", block, re.DOTALL)
        answer = answer_match.group(1).strip() if answer_match else "N/A"

        explanation_match = re.search(r"EXPLANATION:\s*(.*)", block, re.DOTALL)
        explanation = explanation_match.group(1).strip() if explanation_match else "N/A"

        # Extract choices if they exist
        choices = re.findall(r"([A-E])\. (.*?)\n", block)
        choice_texts = [text.strip() for _, text in choices]

        # Extract question text
        if choices:
            question_end = block.find(choices[0][0] + ".")
            question_text = block[:question_end].strip()
        else:
            # No choices — cut off at ANSWER or EXPLANATION if found
            question_text = block
            if answer_match:
                question_text = block[:answer_match.start()].strip()
            elif explanation_match:
                question_text = block[:explanation_match.start()].strip()
            question_text = question_text.strip()

        result.append({
            "Q": i + 1,
            "Question": question_text,
            "Choices": choice_texts,
            "Answer": answer,
            "Explanation": explanation,
            "Topic": base_name
        })

    return result

def saveQuestionsToJson(qa_list, output_path, verobse=False):
    ''' Save the list of questions to a JSON file '''
    import json

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(qa_list, f, indent=4, ensure_ascii=False)

    if verobse:
        print(f"Questions saved to {output_path}")
    


def create_database(db_path="questions.db", verbose=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        q INTEGER,
        question TEXT NOT NULL,
        choice_a TEXT,
        choice_b TEXT,
        choice_c TEXT,
        choice_d TEXT,
        choice_e TEXT,
        answer TEXT,
        explanation TEXT,
        topic TEXT
    )
    ''')

    conn.commit()
    conn.close()

    if verbose:
        print(f"Database created at: {db_path}")


def insert_questions(qa_list, db_path="questions.db", verbose=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for qa in qa_list:
        # Ensure exactly 5 choices
        choices = qa['Choices'] + [""] * (5 - len(qa['Choices']))

        cursor.execute('''
        INSERT INTO questions (
            q, question, choice_a, choice_b, choice_c, choice_d, choice_e, answer, explanation, topic
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            qa['Q'],
            qa['Question'],
            choices[0],
            choices[1],
            choices[2],
            choices[3],
            choices[4],
            qa['Answer'],
            qa['Explanation'],
            qa['Topic']
        ))

    conn.commit()
    conn.close()

    if verbose:
        print(f"{len(qa_list)} questions inserted into {db_path}")

