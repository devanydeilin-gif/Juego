# Devuelve el último nivel guardado para el usuario, o 1 si no hay ninguno
def get_last_level(email):
    records = load_records()
    lst = records.get(email) or records.get('__global__') or []
    if lst and isinstance(lst, list):
        try:
            return int(lst[0].get('level', 1))
        except Exception:
            return 1
    return 1
import pygame
import json
import os
import random
import math
import hashlib
from datetime import datetime
from game import Game
from levels import get_level_config


# Current logged-in user info (set via set_current_user)
current_user = None

def set_current_user(user_info):
    global current_user
    current_user = user_info


RECORDS_FILE = os.path.join(os.path.dirname(__file__), 'records.json')


# ---------------- BLOCKCHAIN ----------------
def create_block(prev_hash, level, duration):
    block = {
        "id": None,  # se asignará automáticamente
        "level": level,
        "duration": duration,
        "timestamp": datetime.now().isoformat(),
        "prev_hash": prev_hash
    }
    # player_name puede ser añadido por el llamador; incluir en hash si existe
    pname = block.get('player_name', '')
    block_str = f"{block['level']}{block['duration']}{block['timestamp']}{block['prev_hash']}{pname}"
    block["hash"] = hashlib.sha256(block_str.encode()).hexdigest()
    return block

def load_records():
    """Carga el archivo de records y devuelve un dict mapping email->list.
    Si el archivo contiene una lista (formato antiguo), migra a {'__global__': list} y lo persiste.
    """
    if not os.path.exists(RECORDS_FILE):
        return {}
    try:
        with open(RECORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return {}

    # Si el archivo está en formato antiguo (lista), migrarlo
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


def get_any_records(raw=None):
    """Devuelve una lista de records adecuada para vistas que esperan una lista.
    - Si raw es None, carga desde archivo.
    - Si existe la clave '__global__', devuelve esa lista.
    - Si raw es dict sin '__global__', concatena todas las listas (orden: por clave) y devuelve la concatenación.
    """
    if raw is None:
        raw = load_records()
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        if '__global__' in raw:
            return raw.get('__global__', [])
        # concatenar listas de todos los usuarios (mantener orden de inserción en cada lista)
        out = []
        for k in raw:
            v = raw.get(k) or []
            if isinstance(v, list):
                out.extend(v)
        return out
    return []

def clear_records():
    if os.path.exists(RECORDS_FILE):
        os.remove(RECORDS_FILE)

def save_block(level, duration, email=None, player_name=None):
    """Guarda un bloque para un usuario concreto (por email). Si email es None, lo guarda en '__global__'.
    player_name es opcional y se incluirá como metadata en el bloque.
    """
    raw = load_records()
    key = email if email else '__global__'
    user_list = raw.get(key, []) if isinstance(raw, dict) else []

    # prev_hash dependiente del usuario
    prev_hash = '0'*64
    if user_list and isinstance(user_list, list) and 'hash' in user_list[0]:
        prev_hash = user_list[0]['hash']

    block = create_block(prev_hash, level, duration)
    if player_name:
        block['player_name'] = player_name
        # recalcular hash incluyendo player_name
        pname = block.get('player_name', '')
        block_str = f"{block['level']}{block['duration']}{block['timestamp']}{block['prev_hash']}{pname}"
        block['hash'] = hashlib.sha256(block_str.encode()).hexdigest()
    block['id'] = len(user_list) + 1
    user_list.insert(0, block)
    # mantener solo los 50 más recientes para ese usuario
    user_list = user_list[:50]

    if isinstance(raw, dict):
        raw[key] = user_list
        write_raw_records(raw)
    else:
        # si por alguna razón raw no es dict, escribir solo la lista
        write_raw_records(user_list)

def verify_chain(records):
    """Verifica la integridad de una lista de bloques. records puede ser lista o raw dict.
    Devuelve índices de bloques alterados (1-based).
    """
    lst = get_any_records(records)
    alerts = []
    for i in range(len(lst)):
        if 'hash' in lst[i] and i+1 < len(lst):
            if 'hash' in lst[i+1]:
                if lst[i]['prev_hash'] != lst[i+1]['hash']:
                    alerts.append(i+1)
    return alerts

# ---------------- BOTONES ----------------
class Button:
    def __init__(self, rect, text, font, color=(70,70,70), hover=(100,100,100)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.color = color
        self.hover = hover
        self.icon = None
        # animación de escala
        self.scale = 1.0
        self.target_scale = 1.0

    def draw(self, screen, mouse_pos):
        is_hover = self.rect.collidepoint(mouse_pos)
        color = self.hover if is_hover else self.color

        # actualizar target_scale según hover
        self.target_scale = 1.06 if is_hover else 1.0
        # interpolar escala suavemente
        self.scale += (self.target_scale - self.scale) * 0.2

        # renderizar botón en una superficie para poder escalar
        w, h = self.rect.size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, color, (0,0,w,h), border_radius=12)
        pygame.draw.rect(surf, (255,255,255), (0,0,w,h), 3, border_radius=12)

        # Dibujar icono + texto si existe
        if self.icon:
            icon_surf = self.icon
            iw, ih = icon_surf.get_size()
            txt = self.font.render(self.text, True, (255,255,255))
            tw = txt.get_width()
            group_w = iw + 8 + tw
            group_x = (w - group_w) // 2
            icon_pos = (group_x, (h - ih)//2)
            text_pos = (group_x + iw + 8, (h - txt.get_height())//2)
            surf.blit(icon_surf, icon_pos)
            surf.blit(txt, text_pos)
        else:
            txt = self.font.render(self.text, True, (255,255,255))
            surf.blit(txt, txt.get_rect(center=(w//2, h//2)))

        # escalar y blitear centrado en el rect original
        if abs(self.scale - 1.0) > 0.001:
            new_w = max(1, int(w * self.scale))
            new_h = max(1, int(h * self.scale))
            scaled = pygame.transform.smoothscale(surf, (new_w, new_h))
            blit_x = self.rect.centerx - new_w//2
            blit_y = self.rect.centery - new_h//2
            screen.blit(scaled, (blit_x, blit_y))
        else:
            screen.blit(surf, self.rect.topleft)

    def is_clicked(self, mouse_pos, mouse_pressed):
        return mouse_pressed[0] and self.rect.collidepoint(mouse_pos)

# ---------------- GRADIENTE DE FONDO ----------------
def draw_gradient_bg(screen, top_color, bottom_color):
    height = screen.get_height()
    for y in range(height):
        ratio = y / height
        r = int(top_color[0]*(1-ratio) + bottom_color[0]*ratio)
        g = int(top_color[1]*(1-ratio) + bottom_color[1]*ratio)
        b = int(top_color[2]*(1-ratio) + bottom_color[2]*ratio)
        pygame.draw.line(screen, (r,g,b), (0,y), (screen.get_width(), y))

# ---------------- ESTRELLAS EN MOVIMIENTO ----------------
def init_stars(num_stars=50, screen_size=(800,600)):
    return [(random.randint(0, screen_size[0]), random.randint(0,screen_size[1])) for _ in range(num_stars)]

def update_draw_stars(screen, stars):
    for i, (x,y) in enumerate(stars):
        pygame.draw.circle(screen, (255,255,255), (x, y), 2)
        stars[i] = (x, (y+1)%screen.get_height())


# (Login functionality removed)


# ---------------- MAIN ----------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Nave Espacial: Esquiva y Dispara")
    clock = pygame.time.Clock()

    # Variables globales
    global confirm_exit
    confirm_exit = False

    # Fuentes
    font = pygame.font.SysFont(None, 32)
    title_font = pygame.font.SysFont(None, 64)
    small_font = pygame.font.SysFont(None, 20)

    # Botones (distribución dinámica y centrada)
    def create_icon(label, size=32):
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size//2, size//2
        # colores
        fg = (255, 255, 255)
        key = label.lower()
        # Soportar etiquetas en español e inglés
        if key.startswith('nueva') or key.startswith('new') or key.startswith('continu') or key.startswith('continuar') or key.startswith('restart') or key.startswith('continue'):
            # triángulo (play)
            points = [(size*0.25, size*0.2), (size*0.25, size*0.8), (size*0.75, size*0.5)]
            pygame.draw.polygon(s, fg, points)
        elif 'instru' in key or 'instruction' in key:
            pygame.draw.circle(s, fg, (cx, cy), size//2 - 2, 2)
            f = pygame.font.SysFont(None, max(12, size//1))
            txt = f.render('i', True, fg)
            s.blit(txt, txt.get_rect(center=(cx, cy-2)))
        elif 'record' in key or 'record' in key:
            # estrella simple
            pts = [
                (cx, size*0.12), (cx+size*0.12, cy-2), (size- size*0.12, cy-2),
                (cx+size*0.06, cy+size*0.12), (cx+size*0.18, size- size*0.12),
                (cx, cy+size*0.03), (cx-size*0.18, size- size*0.12), (cx-size*0.06, cy+size*0.12),
                (size*0.12, cy-2), (cx-size*0.12, cy-2)
            ]
            pygame.draw.polygon(s, fg, pts)
        elif 'jugador' in key or 'jugadores' in key or 'player' in key or 'players' in key:
            # persona: cabeza + cuerpo
            pygame.draw.circle(s, fg, (cx, cy-6), size//6)
            pygame.draw.rect(s, fg, (cx-size*0.18, cy, int(size*0.36), int(size*0.32)))
        elif 'sal' in key or 'exit' in key or 'quit' in key:
            pygame.draw.line(s, fg, (size*0.2, size*0.2), (size*0.8, size*0.8), 4)
            pygame.draw.line(s, fg, (size*0.8, size*0.2), (size*0.2, size*0.8), 4)
        else:
            pygame.draw.circle(s, fg, (cx, cy), size//4)
        return s

    labels = ['NEW GAME', 'RESTART', 'INSTRUCTIONS', 'RECORDS', 'PLAYERS']
    btn_w, btn_h = 300, 64
    v_gap = 18
    cols = 1
    rows = len(labels)
    center_x = screen.get_width() // 2

    # Márgenes superiores e inferiores (no cambiar tamaños de botones)
    # Aumentamos top_margin para separar más el bloque de botones del título
    top_margin = 160
    bottom_margin = 80
    screen_h = screen.get_height()
    available = screen_h - top_margin - bottom_margin

    # espacio necesario con el v_gap actual (incluye espacio para el botón 'Salir')
    exit_h = 48
    extra_between_exit = 18
    needed = rows * btn_h + (rows - 1) * v_gap + extra_between_exit + exit_h

    # Si no cabe, reducir v_gap (hasta un mínimo razonable) para ajustar todo dentro de available
    if needed > available:
        # calcular nuevo v_gap para que todo quepa
        new_v_gap = int((available - rows * btn_h - extra_between_exit - exit_h) / max(1, (rows - 1))) if rows > 1 else 8
        v_gap = max(8, new_v_gap)
        needed = rows * btn_h + (rows - 1) * v_gap + extra_between_exit + exit_h

    # Centrar verticalmente el bloque dentro de los márgenes disponibles
    start_y = top_margin + max(0, (available - (rows * btn_h + (rows - 1) * v_gap + extra_between_exit + exit_h)) // 2)

    menu_buttons = []
    for idx, label in enumerate(labels):
        x = center_x - btn_w//2
        y = start_y + idx * (btn_h + v_gap)
        rect = (x, y, btn_w, btn_h)
        btn = Button(rect, label, font)
        key = label.lower()
        # Iconos especiales por etiqueta en inglés/español
        if 'new' in key or key.startswith('nueva'):
            # icono '+' para Nueva Partida / New Game
            s = pygame.Surface((36,36), pygame.SRCALPHA)
            lw = max(3, 36//10)
            pygame.draw.line(s, (255,255,255), (18,6), (18,30), lw)
            pygame.draw.line(s, (255,255,255), (6,18), (30,18), lw)
            btn.icon = s
        elif 'restart' in key:
            # triángulo (play) para RESTART
            s = pygame.Surface((36,36), pygame.SRCALPHA)
            points = [(36*0.25, 36*0.2), (36*0.25, 36*0.8), (36*0.75, 36*0.5)]
            pygame.draw.polygon(s, (255,255,255), points)
            btn.icon = s
        elif 'continue' in key or 'continu' in key:
            # crear icono reloj simple para continuar/restart
            s = pygame.Surface((36,36), pygame.SRCALPHA)
            pygame.draw.circle(s, (255,255,255), (18,18), 16, 2)
            pygame.draw.line(s, (255,255,255), (18,18), (18,8), 2)
            pygame.draw.line(s, (255,255,255), (18,18), (26,18), 2)
            btn.icon = s
        else:
            btn.icon = create_icon(label, 36)
        menu_buttons.append((label, btn))

    # botón Exit centrado debajo
    exit_w, exit_h = 220, 48
    exit_x = (screen.get_width() - exit_w)//2
    exit_y = start_y + rows * (btn_h + v_gap) + 18
    # asegurar que el botón Salir quede dentro del área visible
    bottom_limit = screen.get_height() - 40
    if exit_y + exit_h > bottom_limit:
        exit_y = bottom_limit - exit_h
    btn_exit = Button((exit_x, exit_y, exit_w, exit_h), 'EXIT', font, color=(150,30,30), hover=(220,60,60))
    btn_exit.icon = create_icon('Exit', 28)

    state = 'menu'  # menu, game, instructions, records
    level = 1
    lives = 3
    game = None
    paused = False
    confirm_exit = False

    stars = init_stars(80)


    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # (Login UI removed) no procesamos InputBox aquí

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and state == 'game':
                    paused = not paused
                    confirm_exit = False  # Reiniciamos el estado de confirmación
                if event.key == pygame.K_ESCAPE and state in ('instructions', 'records', 'players'):
                    state = 'menu'
                # No cerrar con ESC desde 'players'; usar V para volver
                if event.key == pygame.K_v and state == 'players':
                    state = 'menu'
                if event.key == pygame.K_s and state == 'game' and paused:
                    confirm_exit = True
                if event.key == pygame.K_RETURN and state == 'game' and paused and confirm_exit:
                    state = 'menu'
                    game = None
                    paused = False
                    confirm_exit = False

            # Manejo de clicks del ratón (ej. botones del menú)
            if event.type == pygame.MOUSEBUTTONDOWN:
                pass

        # ---------------- MENU ----------------
        if state == 'menu':
            draw_gradient_bg(screen, (0,0,50), (0,0,0))
            update_draw_stars(screen, stars)

            # --- TÍTULO RESPONSIVO CON SOMBRA ---
            screen_w = screen.get_width()
            screen_h = screen.get_height()
            shine = int(128 + 127 * math.sin(pygame.time.get_ticks() * 0.005))
            title_text = 'NAVE ESPACIAL'
            title_surf = title_font.render(title_text, True, (255,255,shine))
            # sombra: renderizamos el texto en negro y lo desplazamos varias veces
            shadow_surf = title_font.render(title_text, True, (0,0,0))
            # posición responsiva: a 12% de la altura de la ventana
            title_center_y = max(40, int(screen_h * 0.12))
            title_rect = title_surf.get_rect(center=(screen_w//2, title_center_y))
            # dibujar sombras con offsets
            for ox, oy, a in ((3,3,180), (1,1,100)):
                # usamos la misma superficie negra (sin alpha) para simular sombra
                screen.blit(shadow_surf, shadow_surf.get_rect(center=(title_rect.centerx+ox, title_rect.centery+oy)))
            # dibujar título principal
            screen.blit(title_surf, title_rect)

            # --- PANEL SUPERIOR DERECHO: perfil del usuario ---
            try:
                if current_user:
                    cu_name = current_user.get('name', 'Jugador')
                    cu_email = current_user.get('email')
                    cu_level = get_last_level(cu_email)
                    panel_w, panel_h = 100, 70
                    panel_x = screen_w - panel_w - 20
                    panel_y = 20
                    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                    panel_surf.fill((0,0,0,160))
                    pygame.draw.rect(panel_surf, (255,255,255), panel_surf.get_rect(), 2, border_radius=8)
                    name_txt = small_font.render(cu_name, True, (0,255,200))
                    level_txt = small_font.render(f"Nivel: {cu_level}", True, (200,200,255))
                    panel_surf.blit(name_txt, (10, 10))
                    panel_surf.blit(level_txt, (10, 36))
                    screen.blit(panel_surf, (panel_x, panel_y))
            except Exception:
                pass

            # --- REPOSICIONAR BOTONES SEGÚN TÍTULO ---
            # recalcular márgenes a partir de la posición del título
            top_margin_dynamic = title_rect.bottom + 24
            bottom_margin = max(60, int(screen_h * 0.13))
            available = screen_h - top_margin_dynamic - bottom_margin

            # recalcular v_gap si es necesario (mismo método que antes)
            exit_h = 48
            extra_between_exit = 18
            needed = rows * btn_h + (rows - 1) * v_gap + extra_between_exit + exit_h
            if needed > available:
                new_v_gap = int((available - rows * btn_h - extra_between_exit - exit_h) / max(1, (rows - 1))) if rows > 1 else 8
                v_gap = max(8, new_v_gap)
                needed = rows * btn_h + (rows - 1) * v_gap + extra_between_exit + exit_h

            start_y = top_margin_dynamic + max(0, (available - (rows * btn_h + (rows - 1) * v_gap + extra_between_exit + exit_h)) // 2)

            # actualizar rects de los botones para la nueva posición
            center_x = screen_w // 2
            for idx, (label, b) in enumerate(menu_buttons):
                x = center_x - btn_w//2
                y = start_y + idx * (btn_h + v_gap)
                b.rect.topleft = (x, y)
                b.rect.size = (btn_w, btn_h)
                b.draw(screen, mouse_pos)

            # botón Salir centrado debajo, asegurando visibilidad
            exit_x = (screen_w - exit_w)//2
            exit_y = start_y + rows * (btn_h + v_gap) + 18
            bottom_limit = screen_h - 40
            if exit_y + exit_h > bottom_limit:
                exit_y = bottom_limit - exit_h
            btn_exit.rect.topleft = (exit_x, exit_y)
            btn_exit.rect.size = (exit_w, exit_h)
            btn_exit.draw(screen, mouse_pos)

            # (antes mostraba mensajes de Firebase aquí, ahora eliminado)

            # manejar clicks en botones del menú por etiqueta
            handled = False
            for label, b in menu_buttons:
                if b.is_clicked(mouse_pos, mouse_pressed):
                    if label == 'NEW GAME':
                        level = 1
                        lives = 3
                        game = Game(screen, get_level_config(level), lives)
                        game.start_time = pygame.time.get_ticks()
                        game.kills = 0
                        state = 'game'
                        pygame.time.wait(150)
                    elif label == 'RESTART':
                        # Reiniciar en el último nivel del usuario actual (si hay sesión)
                        try:
                            email = current_user.get('email') if current_user else None
                        except Exception:
                            email = None
                        try:
                            level = int(get_last_level(email))
                        except Exception:
                            level = 1
                        lives = 3
                        game = Game(screen, get_level_config(level), lives)
                        game.start_time = pygame.time.get_ticks()
                        game.kills = 0
                        state = 'game'
                        pygame.time.wait(150)
                    elif label == 'INSTRUCTIONS':
                        state = 'instructions'
                        pygame.time.wait(150)
                    elif label == 'RECORDS':
                        state = 'records'
                        pygame.time.wait(150)
                    elif label == 'PLAYERS':
                        state = 'players'
                        pygame.time.wait(150)
                    elif label == 'EXIT':
                        running = False
                        pygame.time.wait(150)
                    handled = True
                    break
            if not handled and btn_exit.is_clicked(mouse_pos, mouse_pressed):
                running = False
                pygame.time.wait(150)

        # ---------------- INSTRUCCIONES ----------------
        elif state == 'instructions':
            draw_gradient_bg(screen, (0,0,30), (0,0,10))
            update_draw_stars(screen, stars)

            # PANEL SEMI-TRANSPARENTE
            panel_rect = pygame.Rect(50, 100, screen.get_width()-100, 400)
            panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
            panel_surf.fill((0,0,0,180))  # negro semi-transparente
            pygame.draw.rect(panel_surf, (255,255,255), panel_surf.get_rect(), 3, border_radius=12)
            # Blitear el panel semi-transparente al screen para que sea visible
            screen.blit(panel_surf, panel_rect.topleft)

            # TÍTULO
            title_txt = title_font.render("INSTRUCCIONES", True, (255, 255, 0))
            screen.blit(title_txt, (screen.get_width()//2 - title_txt.get_width()//2, 30))

            instructions = [
                ("FLECHAS", "Mover la nave"),
                ("ESPACIO", "Disparar"),
                ("P", "Pausar el juego"),
                ("S", "Volver al menú (pausa)"),
                ("ENTER", "Confirmar salida al menú"),
                ("R", "Reiniciar partida (cuando game over)")
            ]

            for i, (key, desc) in enumerate(instructions):
                # Dibujar “tecla” como rectángulo con borde (tamaño reducido a 120x48)
                key_surf = pygame.Surface((120,48), pygame.SRCALPHA)
                key_surf.fill((50,50,50,220))
                pygame.draw.rect(key_surf, (255,255,255), key_surf.get_rect(), 2, border_radius=6)

                # Texto de la tecla (centrado en el recuadro 120x48)
                ktxt = font.render(key, True, (255,255,255))
                key_surf.blit(ktxt, ktxt.get_rect(center=(60,24)))

                # Posición dentro del panel
                key_x = panel_rect.x + 20
                key_y = panel_rect.y + 30 + i*60
                screen.blit(key_surf, (key_x, key_y))

                # Texto de la acción (desplazado a la derecha)
                desc_txt = font.render(desc, True, (200,200,255))
                screen.blit(desc_txt, (key_x + 140, key_y + 14))

            # INSTRUCCIÓN PARA VOLVER
            back = small_font.render('Presiona ESC para volver', True, (200,200,200))
            screen.blit(back, (screen.get_width()//2 - back.get_width()//2, panel_rect.bottom + 20))

        # ---------------- PLAYERS ----------------
        elif state == 'players':
            draw_gradient_bg(screen, (10,10,30), (0,0,10))
            update_draw_stars(screen, stars)
            title = title_font.render('Jugadores', True, (200,200,255))
            screen.blit(title, (320, 20))
            # Lista de jugadores basada en records.json
            raw = load_records()
            display_players = []
            if isinstance(raw, dict):
                for k in raw:
                    if k == '__global__':
                        continue
                    lst = raw.get(k) or []
                    if not isinstance(lst, list) or len(lst) == 0:
                        continue
                    # intentar obtener nombre del primer bloque que tenga player_name
                    name = None
                    for blk in lst:
                        if blk.get('player_name'):
                            name = blk.get('player_name')
                            break
                    if not name:
                        # fallback: parte local del email capitalizada
                        try:
                            name = k.split('@')[0].capitalize()
                        except Exception:
                            name = k
                    # calcular nivel máximo alcanzado
                    try:
                        max_level = max(int(blk.get('level', 1)) for blk in lst if isinstance(blk, dict))
                    except Exception:
                        max_level = 1
                    display_players.append({'email': k, 'name': name, 'max_level': max_level})
            else:
                # si raw es lista, no hay separación por jugador; mostrar anónimo
                display_players = [{'email': '__global__', 'name': '__global__', 'max_level': max((r.get('level',1) for r in raw), default=1)}]

            # Mostrar cada jugador con una barra de nivel (niveles 1..10)
            bar_x = 260
            bar_w = 360
            bar_h = 18
            for i, p in enumerate(display_players):
                y = 120 + i*60
                txt = font.render(f"{i+1}. {p['name']}", True, (255,255,255))
                screen.blit(txt, (80, y))
                # fondo de la barra
                pygame.draw.rect(screen, (60,60,60), (bar_x, y+6, bar_w, bar_h), border_radius=6)
                # porcentaje según nivel (1..10)
                pct = max(1, min(10, int(p.get('max_level', 1)))) / 10.0
                fill_w = int(bar_w * pct)
                pygame.draw.rect(screen, (0,200,0), (bar_x, y+6, fill_w, bar_h), border_radius=6)
                # texto del nivel al lado
                lvl_txt = small_font.render(f"Nivel Máximo: {p.get('max_level',1)}", True, (255,255,255))
                screen.blit(lvl_txt, (bar_x + bar_w + 12, y+2))

            back = small_font.render('Presiona ESC para volver', True, (200,200,200))
            screen.blit(back, (50, 520))


            # ---------------- RECORDS ----------------
        elif state == 'records':
            draw_gradient_bg(screen, (0,0,15), (0,0,40))
            update_draw_stars(screen, stars)

            title = title_font.render('Registro', True, (200,200,255))
            screen.blit(title, (320, 20))
            
            # Verificar integridad de la cadena
            raw = load_records()
            records = get_any_records(raw)
            alerts = verify_chain(raw)
            
            # Encabezados de la tabla (añadimos Jugador)
            headers = ["ID", "Jugador", "Nivel", "Duración", "Estado", "Hash", "PrevHash"]
            # Ajuste: reducir espacio de Nivel/Duración para darle más ancho a Estado
            x_pos = [60, 96, 200, 270, 380, 520, 660]
            y_start = 100
            # Dibujar encabezados
            for header, x in zip(headers, x_pos):
                txt = font.render(header, True, (255,255,0))
                screen.blit(txt, (x, y_start))
            # Línea separadora
            pygame.draw.line(screen, (255,255,255), (40, y_start + 30), (760, y_start + 30), 2)
            # Construir lista de records para mostrar que incluya nombre de jugador
            display_records = []
            if isinstance(raw, dict):
                # construir un mapping email->name buscando player_name en los bloques
                email_to_name = {}
                for k in raw:
                    if k == '__global__':
                        continue
                    lst = raw.get(k) or []
                    if isinstance(lst, list):
                        for blk in lst:
                            if blk.get('player_name'):
                                email_to_name[k] = blk.get('player_name')
                                break

                # iterar por clave (email o '__global__') y anexar metadatos
                for k in raw:
                    lst = raw.get(k) or []
                    if isinstance(lst, list):
                        for blk in lst:
                            b = dict(blk)
                            # Preferir player_name en el propio bloque
                            if blk.get('player_name'):
                                b['player'] = blk.get('player_name')
                            else:
                                # si no hay player_name, usar mapping por email
                                if k == '__global__':
                                    b['player'] = '__global__'
                                else:
                                    name = email_to_name.get(k)
                                    if name:
                                        b['player'] = name
                                    else:
                                        # fallback: parte local del email
                                        try:
                                            local = k.split('@')[0]
                                            b['player'] = local.capitalize()
                                        except Exception:
                                            b['player'] = k
                            display_records.append(b)
            else:
                # formato antiguo: lista global
                for blk in records:
                    b = dict(blk)
                    b['player'] = blk.get('player_name') or '__global__'
                    display_records.append(b)

            # Mostrar registros (mostramos player en la segunda columna)
            for i, r in enumerate(display_records[:10]):
                y = y_start + 50 + i*40
                # ID
                txt = font.render(f"{i+1}", True, (255,255,255))
                screen.blit(txt, (x_pos[0], y))
                # Jugador (nombre o email)
                player_txt = str(r.get('player', ''))
                txt = font.render(player_txt, True, (255,255,255))
                screen.blit(txt, (x_pos[1], y))
                # Nivel
                txt = font.render(f"{r.get('level', 0)}", True, (255,255,255))
                screen.blit(txt, (x_pos[2], y))
                # Duración
                txt = font.render(f"{r.get('duration', 0):.1f}s", True, (255,255,255))
                screen.blit(txt, (x_pos[3], y))
                # Estado
                color = (255,0,0) if i+1 in alerts else (0,255,0)
                estado = "ALTERADO" if i+1 in alerts else "VÁLIDO"
                txt = font.render(estado, True, color)
                screen.blit(txt, (x_pos[4], y))
                # Hash actual
                hash_actual = r.get('hash', '')[:8]
                txt = font.render(hash_actual, True, (150,150,150))
                screen.blit(txt, (x_pos[5], y))
                # Hash previo
                prev_hash = r.get('prev_hash', '')[:8]
                txt = font.render(prev_hash, True, (150,150,150))
                screen.blit(txt, (x_pos[6], y))

            btn_clear = Button((550, 520, 200, 40), 'Limpiar Records', font)
            btn_break = Button((320, 520, 200, 40), 'Romper Cadena', font, color=(120,40,40), hover=(180,60,60))
            btn_clear.draw(screen, mouse_pos)
            btn_break.draw(screen, mouse_pos)
            if btn_clear.is_clicked(mouse_pos, mouse_pressed):
                clear_records()
                pygame.time.wait(150)
            if btn_break.is_clicked(mouse_pos, mouse_pressed):
                # Romper la integridad de la cadena en un bloque aleatorio (excepto el primero)
                records = load_records()
                if len(records) > 1:
                    import random
                    idx = random.randint(1, len(records)-1)
                    records[idx]['hash'] = 'X' * 64
                    with open(RECORDS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(records, f, ensure_ascii=False, indent=2)
                pygame.time.wait(150)
            back = small_font.render('Presiona ESC para volver', True, (200,200,200))
            screen.blit(back, (50, 520))
        # ---------------- GAME ----------------
        elif state == 'game':
            keys = pygame.key.get_pressed()
            if paused:
                draw_gradient_bg(screen, (0,0,30), (0,0,10))
                update_draw_stars(screen, stars)
                game.draw()
                pause_text = title_font.render('PAUSA', True, (255,255,0))
                screen.blit(pause_text, pause_text.get_rect(center=(400,300)))
                
                # Si está activada la confirmación de salida, mostrar el mensaje
                if confirm_exit:
                    # Fondo semi-transparente para el mensaje
                    s = pygame.Surface((600, 100))
                    s.set_alpha(128)
                    s.fill((0,0,0))
                    screen.blit(s, (100, 320))
                    
                    # Mensaje de confirmación
                    confirm_text = font.render('¿Seguro que quieres EXIT? Presiona ENTER para confirmar', True, (255,255,255))
                    screen.blit(confirm_text, confirm_text.get_rect(center=(400,350)))
                else:
                    # Mostrar instrucción de cómo salir
                    exit_text = small_font.render('Presiona S para volver al menú', True, (200,200,200))
                    screen.blit(exit_text, exit_text.get_rect(center=(400,350)))
            else:
                result = game.update()
                if result == 'lose_life':
                    lives -= 1
                    if lives > 0:
                        game.reset(get_level_config(level), lives)
                    else:
                        duration = (pygame.time.get_ticks() - game.start_time) / 1000.0
                        # Guardar por usuario si hay sesión activa
                        try:
                            email = current_user.get('email') if current_user else None
                            player_name = current_user.get('name') if current_user else None
                        except Exception:
                            email = None
                            player_name = None
                        # incluir player_name como metadata
                        try:
                            save_block(level, duration, email, player_name=player_name)
                        except Exception:
                            # fallback: intentar guardar con records.save_player_block si disponible
                            try:
                                from records import save_player_block
                                save_player_block(level, duration, email, player_name=player_name)
                            except Exception:
                                pass
                        start_time = pygame.time.get_ticks()
                        while pygame.time.get_ticks() - start_time < 2000:
                            for _ev in pygame.event.get():
                                # consumir events para mantener la ventana responsiva
                                # ignoramos QUIT temporalmente para mostrar el mensaje
                                pass
                            draw_gradient_bg(screen, (0,0,30), (0,0,10))
                            update_draw_stars(screen, stars)
                            game_over = title_font.render('GAME OVER', True, (255,0,0))
                            screen.blit(game_over, game_over.get_rect(center=(400,300)))
                            pygame.display.flip()
                            clock.tick(60)
                        state = 'menu'
                        game = None
                elif result == 'level_complete':
                    level += 1
                    if level > 10:
                        duration = (pygame.time.get_ticks() - game.start_time) / 1000.0
                        try:
                            email = current_user.get('email') if current_user else None
                            player_name = current_user.get('name') if current_user else None
                        except Exception:
                            email = None
                            player_name = None
                        try:
                            save_block(10, duration, email, player_name=player_name)
                        except Exception:
                            try:
                                from records import save_player_block
                                save_player_block(10, duration, email, player_name=player_name)
                            except Exception:
                                pass
                        start_time = pygame.time.get_ticks()
                        while pygame.time.get_ticks() - start_time < 2000:
                            for _ev in pygame.event.get():
                                pass
                            draw_gradient_bg(screen, (0,0,30), (0,0,10))
                            update_draw_stars(screen, stars)
                            game_over = title_font.render('GAME OVER', True, (255,0,0))
                            screen.blit(game_over, game_over.get_rect(center=(400,300)))
                            pygame.display.flip()
                            clock.tick(60)
                        state = 'menu'
                        game = None
                    else:
                        start_time = pygame.time.get_ticks()
                        while pygame.time.get_ticks() - start_time < 1500:
                            for _ev in pygame.event.get():
                                pass
                            draw_gradient_bg(screen, (0,0,30), (0,0,10))
                            update_draw_stars(screen, stars)
                            level_msg = title_font.render(f'NIVEL {level}', True, (255,255,0))
                            screen.blit(level_msg, level_msg.get_rect(center=(400,300)))
                            pygame.display.flip()
                            clock.tick(60)
                        game.reset(get_level_config(level), lives)

                if state == 'game' and game is not None:
                    screen.fill((0,0,0))
                    draw_gradient_bg(screen, (0,0,30), (0,0,10))
                    update_draw_stars(screen, stars)
                    game.draw()
                    for i in range(lives):
                        pygame.draw.polygon(screen, (255,0,0), [(20+i*30, 20), (25+i*30, 10), (30+i*30, 20), (25+i*30, 30)])
                    level_text = font.render(f"Nivel: {level}", True, (255,255,255))
                    screen.blit(level_text, (10, 50))
                    kills_text = font.render(f"Kills: {getattr(game,'kills',0)}", True, (255,255,255))
                    screen.blit(kills_text, (10, 90))
                    if hasattr(game,'start_time'):
                        current_time = (pygame.time.get_ticks() - game.start_time) / 1000.0
                        time_text = font.render(f"Tiempo: {current_time:.1f}s", True, (255,255,255))
                        screen.blit(time_text, (10, 130))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == '__main__':
    main()


# --------------------- USER-SPECIFIC SIMPLE LAUNCH ---------------------
def main_user(user_info):
    """Lightweight entry that shows player name and last level.
    This is intentionally simple and does not modify the main game flow.
    """
    import pygame
    from records import get_last_level

    user_email = user_info.get("email") if user_info else None
    user_name = user_info.get("name") if user_info else "Jugador"

    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Nave Espacial - Perfil")
    font = pygame.font.SysFont(None, 30)

    current_level = get_last_level(user_email)

    running = True
    clock = pygame.time.Clock()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 50))
        text = font.render(f"Jugador: {user_name} | Nivel actual: {current_level}", True, (255, 255, 0))
        screen.blit(text, (20, 20))
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()