import sqlite3
import random


def get_P_questions_by_ids(ids, db_path="merged.db"):
    ''' Retrieve questions from the database by their IDs '''
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    placeholders = ', '.join('?' for _ in ids)
    query = f'SELECT id, question, choice_a, choice_b, choice_c, choice_d, choice_e, answer FROM plabable_all WHERE id IN ({placeholders})'
    
    cursor.execute(query, ids)
    results = cursor.fetchall()

    conn.close()
    
    return results


def getRandom_p_questions(n, topic=None, exclude_ids=None, db_path="merged.db"):
    """
    Retrieve n random questions from the database, optionally filtered by topic and excluding IDs.

    :param n: Number of random questions to retrieve
    :param db_path: Path to the database file
    :param topic: Topic to filter questions by (optional)
    :param exclude_ids: List of IDs to exclude (optional)
    :return: List of question dicts
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = 'SELECT id FROM plabable_all'
    conditions = []
    params = []

    if topic is not None:
        conditions.append('topic = ?')
        params.append(topic)
    if exclude_ids:
        placeholders = ', '.join('?' for _ in exclude_ids)
        conditions.append(f'id NOT IN ({placeholders})')
        params.extend(exclude_ids)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    cursor.execute(query, params)
    all_ids = [row[0] for row in cursor.fetchall()]

    if not all_ids:
        conn.close()
        return []

    sample_size = min(n, len(all_ids))
    random_ids = random.sample(all_ids, sample_size)
    questions = get_P_questions_by_ids(random_ids, db_path)
    conn.close()
    # Convert tuples to dicts for API compatibility
    result = []
    for q in questions:
        result.append({
            "id": q[0],
            "question": q[1],
            "choices": [q[2], q[3], q[4], q[5], q[6]],
            "answer": q[7]
        })
    return result
