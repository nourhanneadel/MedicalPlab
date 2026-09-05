import sqlite3
import random


def get_P_questions_by_ids(ids, db_path="merged.db"):
    ''' Retrieve questions from the database by their IDs '''
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    placeholders = ', '.join('?' for _ in ids)
    query = f'SELECT question, choice_a, choice_b, choice_c, choice_d, choice_e, answer FROM plabable_all WHERE id IN ({placeholders})'
    
    cursor.execute(query, ids)
    results = cursor.fetchall()

    conn.close()
    
    return results


def getRandom_p_questions(n, topic=None, db_path="merged.db"):
    """
    Retrieve n random questions from the database, optionally filtered by topic.

    :param n: Number of random questions to retrieve
    :param db_path: Path to the database file
    :param topic: Topic to filter questions by (optional)
    :return: List of question tuples
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if topic is not None:
        cursor.execute('SELECT id FROM plabable_all WHERE topic = ?', (topic,))
    else:
        cursor.execute('SELECT id FROM plabable_all')
    all_ids = [row[0] for row in cursor.fetchall()]

    if len(all_ids) < n:
        if topic is not None:
            raise ValueError(f"Not enough questions in the topic '{topic}' to retrieve the requested number.")
        else:
            raise ValueError("Not enough questions in the database to retrieve the requested number.")

    random_ids = random.sample(all_ids, n)
    questions = get_P_questions_by_ids(random_ids, db_path)
    conn.close()
    # Convert tuples to dicts for API compatibility
    result = []
    for q in questions:
        result.append({
            "question": q[0],
            "choices": [q[1], q[2], q[3], q[4], q[5]],
            "answer": q[6]
        })
    return result
