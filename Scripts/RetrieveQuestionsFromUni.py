import sqlite3
import random

def get_U_questions_by_ids(ids, db_path="merged.db"):
    ''' Retrieve questions from the database by their IDs '''
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    placeholders = ', '.join('?' for _ in ids)
    query = f"""
    SELECT
        id,
        question,
        choice_a,
        choice_b,
        choice_c,
        choice_d,
        -- map 'A','B','C','D' to the actual choice text
        CASE answer
            WHEN 'A' THEN choice_a
            WHEN 'B' THEN choice_b
            WHEN 'C' THEN choice_c
            WHEN 'D' THEN choice_d
        END AS correct_answer,
        topic,
        level
    FROM uni
    WHERE id IN ({placeholders})
    """    
    cursor.execute(query, ids)
    results = cursor.fetchall()

    conn.close()
    
    return results

def getRandom_u_questions(n, topic=None, level=None, exclude_ids=None, db_path="merged.db"):
    """
    Retrieve n random questions from the database filtered by topic and/or level, optionally excluding IDs.

    :param n: Number of random questions to retrieve
    :param topic: (Optional) Topic to filter questions by
    :param level: (Optional) Level to filter questions by
    :param exclude_ids: (Optional) List of question IDs to exclude
    :param db_path: Path to the database file
    :return: List of question dicts
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = 'SELECT id FROM uni'
    conditions = []
    params = []

    if topic is not None and str(topic).strip():
        conditions.append('LOWER(topic) = LOWER(?)')
        params.append(str(topic).strip())
    if level is not None:
        conditions.append('level = ?')
        params.append(level)
    if exclude_ids:
        placeholders = ', '.join('?' for _ in exclude_ids)
        conditions.append(f'id NOT IN ({placeholders})')
        params.extend(exclude_ids)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    cursor.execute(query, params)
    all_ids = [row[0] for row in cursor.fetchall()]

    # If no unseen questions remain matching the filter (e.g. user has seen all available questions),
    # fall back to all questions matching topic/level so the user can continue practicing.
    if not all_ids and exclude_ids:
        fallback_query = 'SELECT id FROM uni'
        fallback_conditions = []
        fallback_params = []
        if topic is not None and str(topic).strip():
            fallback_conditions.append('LOWER(topic) = LOWER(?)')
            fallback_params.append(str(topic).strip())
        if level is not None:
            fallback_conditions.append('level = ?')
            fallback_params.append(level)
        if fallback_conditions:
            fallback_query += ' WHERE ' + ' AND '.join(fallback_conditions)
        cursor.execute(fallback_query, fallback_params)
        all_ids = [row[0] for row in cursor.fetchall()]

    if not all_ids:
        conn.close()
        return []

    sample_size = min(n, len(all_ids))
    random_ids = random.sample(all_ids, sample_size)
    questions = get_U_questions_by_ids(random_ids, db_path)
    conn.close()
    # Convert tuples to dicts for API compatibility
    result = []
    for q in questions:
        result.append({
            "id": q[0],
            "question": q[1],
            "choices": [q[2], q[3], q[4], q[5]],
            "answer": q[6],
            "topic": q[7] if len(q) > 7 else None,
            "level": q[8] if len(q) > 8 else None
        })
    return result
