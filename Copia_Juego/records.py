import json
import os
import hashlib
from datetime import datetime

RECORDS_FILE = os.path.join(os.path.dirname(__file__), 'records.json')


def _create_block(prev_hash, level, duration):
    block = {
        "id": None,
        "level": level,
        "duration": duration,
        "timestamp": datetime.now().isoformat(),
        "prev_hash": prev_hash,
    }
    # player_name could be added by the caller; include in hash if present
    pname = block.get('player_name', '')
    block_str = f"{block['level']}{block['duration']}{block['timestamp']}{block['prev_hash']}{pname}"
    block["hash"] = hashlib.sha256(block_str.encode()).hexdigest()
    return block


def load_records():
    """Carga records desde RECORDS_FILE.
    Devuelve un dict mapping email->list. Si el archivo contiene una lista (formato antiguo), lo migra a {'__global__': list}.
    """
    if not os.path.exists(RECORDS_FILE):
        return {}
    try:
        with open(RECORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return {}

    if isinstance(data, list):
        new = {'__global__': data}
        try:
            with open(RECORDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(new, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return new

    if isinstance(data, dict):
        return data

    return {}


def write_raw_records(raw):
    """Escribe el contenido raw (list o dict) en RECORDS_FILE de forma segura."""
    try:
        with open(RECORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def save_player_block(level, duration, email=None, player_name=None):
    """Guarda un bloque (nivel/duración) para un usuario concreto (por email).
    Si email es None se guarda en '__global__'. Mantiene hasta 50 bloques por usuario.
    """
    raw = load_records()
    key = email if email else '__global__'
    user_list = raw.get(key, []) if isinstance(raw, dict) else []

    prev_hash = '0'*64
    if user_list and isinstance(user_list, list) and 'hash' in user_list[0]:
        prev_hash = user_list[0]['hash']

    block = _create_block(prev_hash, level, duration)
    if player_name:
        block['player_name'] = player_name
        pname = block.get('player_name', '')
        block_str = f"{block['level']}{block['duration']}{block['timestamp']}{block['prev_hash']}{pname}"
        block['hash'] = hashlib.sha256(block_str.encode()).hexdigest()
    block['id'] = len(user_list) + 1
    user_list.insert(0, block)
    user_list = user_list[:50]

    if isinstance(raw, dict):
        raw[key] = user_list
        write_raw_records(raw)
    else:
        write_raw_records(user_list)


def get_last_level(email):
    """Devuelve el último nivel guardado para el usuario (o 1 si no hay ninguno)."""
    records = load_records()
    lst = records.get(email) or records.get('__global__') or []
    if lst and isinstance(lst, list):
        try:
            return int(lst[0].get('level', 1))
        except Exception:
            return 1
    return 1

