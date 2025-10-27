import pygame
import pyrebase
import firebase_admin
import json
from firebase_admin import credentials, firestore
from main import get_level_config, main

# --------------------- CONFIGURACIÓN FIREBASE ---------------------
cred = credentials.Certificate(r"C:\Users\devan\Desktop\Copia_Juego\serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db_firestore = firestore.client()

firebaseConfig = {
    "apiKey": "AIzaSyDzcqRMYkWnFXKkPDG9kz3eo4OU1iHuqpo",
    "authDomain": "juego-7fb19.firebaseapp.com",
    "databaseURL": "https://juego-7fb19-default-rtdb.firebaseio.com/",
    "projectId": "juego-7fb19",
    "storageBucket": "juego-7fb19.firebasestorage.app",
    "messagingSenderId": "816954516543",
    "appId": "1:816954516543:web:b1dd6e5b9b374d4815c48a",
    "measurementId": "G-7LLNSMQNE7"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

# --------------------- FUNCIONES AUXILIARES DE ERRORES ---------------------
def parse_firebase_error(e):
    """Extrae el mensaje JSON de error de Firebase Auth."""
    try:
        # pyrebase normalmente devuelve (HTTPError, response.json())
        error_json = e.args[1]
        data = json.loads(error_json)
        message = data["error"]["message"]
        return message
    except Exception:
        return str(e)

def translate_firebase_error(code):
    """Traduce los códigos de error de Firebase a mensajes entendibles."""
    code = code.upper()
    if "EMAIL_EXISTS" in code:
        return " El correo ya está registrado."
    elif "INVALID_EMAIL" in code:
        return " El formato del correo es inválido."
    elif "WEAK_PASSWORD" in code:
        return " La contraseña debe tener al menos 6 caracteres."
    elif "EMAIL_NOT_FOUND" in code:
        return " No existe una cuenta con este correo."
    elif "INVALID_PASSWORD" in code or "INVALID_LOGIN_CREDENTIALS" in code:
        return " Contraseña incorrecta."
    elif "MISSING_PASSWORD" in code:
        return " Ingresa una contraseña."
    elif "MISSING_EMAIL" in code:
        return " Ingresa un correo electrónico."
    else:
        return f"Error desconocido: {code}"

# --------------------- FUNCIONES FIREBASE ---------------------
def register_user_firestore(payload):
    email = payload['email']
    password = payload['password']
    name = payload['name']

    try:
        user = auth.create_user_with_email_and_password(email, password)
        uid = user['localId']
        db_firestore.collection('users').document(uid).set({
            'name': name,
            'email': email
        })
        return True, "Usuario registrado correctamente en Firestore"
    except Exception as e:
        return False, parse_firebase_error(e)

def login_user(payload):
    email = payload['email']
    password = payload['password']
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        return True, f"Login exitoso: {user['email']}"
    except Exception as e:
        return False, parse_firebase_error(e)

# --------------------- COMPONENTES PYGAME ---------------------
class Button:
    def __init__(self, rect, text, font, color=(70,70,70), hover=(100,100,100)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.color = color
        self.hover = hover

    def draw(self, screen, mouse_pos):
        is_hover = self.rect.collidepoint(mouse_pos)
        color = self.hover if is_hover else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        pygame.draw.rect(screen, (255,255,255), self.rect, 3, border_radius=12)
        txt = self.font.render(self.text, True, (255,255,255))
        screen.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class InputBox:
    def __init__(self, rect, font, text='', is_password=False):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.text = text
        self.is_password = is_password
        self.active = False
        self.placeholder = ''

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return 'enter'
            else:
                if len(self.text) < 64:
                    self.text += event.unicode

    def set_placeholder(self, text):
        self.placeholder = text

    def set_active(self, val: bool):
        self.active = bool(val)

    def draw(self, screen):
        pygame.draw.rect(screen, (10,10,10), self.rect)
        display = ('*'*len(self.text)) if self.is_password and self.text else (self.text if self.text else self.placeholder)
        color = (255,255,255) if self.active else (160,160,160) if self.text else (120,120,120)
        txt = self.font.render(display, True, color)
        screen.blit(txt, (self.rect.x+8, self.rect.y+6))
        pygame.draw.rect(screen, (255,255,255) if self.active else (120,120,120), self.rect, 2, border_radius=8)

# --------------------- MENSAJES DINÁMICOS ---------------------
class GameMessage:
    def __init__(self, text, color=(255,255,255), duration=2, font=None, pos=None):
        self.text = text
        self.color = color
        self.duration = duration
        self.start_time = pygame.time.get_ticks()
        self.font = font
        self.pos = pos

    def draw(self, screen):
        elapsed = (pygame.time.get_ticks() - self.start_time) / 1000
        if elapsed > self.duration:
            return False
        alpha = 255
        if self.duration - elapsed < 0.5:
            alpha = int(255 * (self.duration - elapsed) / 0.5)
        txt_surf = self.font.render(self.text, True, self.color)
        txt_surf.set_alpha(alpha)
        x = self.pos[0] if self.pos else screen.get_width() // 2
        base_y = self.pos[1] if self.pos else int(screen.get_height() * 0.85)
        y_offset = int(20 * (elapsed / self.duration))
        y = base_y - y_offset
        rect = txt_surf.get_rect(center=(x, y))
        screen.blit(txt_surf, rect)
        return True

messages = []
def add_message(text, font, color=(255,255,255), duration=2, pos=None):
    messages.append(GameMessage(text, color, duration, font, pos))

def draw_messages(screen):
    for msg in messages[:]:
        alive = msg.draw(screen)
        if not alive:
            messages.remove(msg)

# --------------------- GRÁFICOS ---------------------
def draw_gradient_bg(screen, top_color, bottom_color):
    height = screen.get_height()
    for y in range(height):
        ratio = y / height
        r = int(top_color[0]*(1-ratio) + bottom_color[0]*ratio)
        g = int(top_color[1]*(1-ratio) + bottom_color[1]*ratio)
        b = int(top_color[2]*(1-ratio) + bottom_color[2]*ratio)
        pygame.draw.line(screen, (r,g,b), (0,y), (screen.get_width(), y))

def init_stars(num_stars=50, screen_size=(800,600)):
    import random
    return [(random.randint(0, screen_size[0]), random.randint(0,screen_size[1])) for _ in range(num_stars)]

def update_draw_stars(screen, stars):
    for i, (x,y) in enumerate(stars):
        pygame.draw.circle(screen, (255,255,255), (x, y), 2)
        stars[i] = (x, (y+1)%screen.get_height())

# --------------------- LOGIN ---------------------
def show_login(screen, fonts, initial_stars=None):
    clock = pygame.time.Clock()
    font, title_font, small_font = fonts
    stars = initial_stars or init_stars(80, (screen.get_width(), screen.get_height()))

    input_name = InputBox((250, 220, 300, 36), font)
    input_email = InputBox((250, 270, 300, 36), font)
    input_pass = InputBox((250, 320, 300, 36), font, is_password=True)
    input_name.set_placeholder('Tu nombre')
    input_email.set_placeholder('correo@ejemplo.com')
    input_pass.set_placeholder('6 dígitos')

    btn_login = Button((260, 380, 120, 42), 'Login', font, color=(0,150,255), hover=(0,200,255))
    btn_register = Button((420, 380, 120, 42), 'Registrar', font, color=(0,255,100), hover=(0,255,150))

    running = True
    focused = 0
    inputs = [input_name, input_email, input_pass]
    inputs[focused].set_active(True)

    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return ('quit', {})

            if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                inputs[focused].set_active(False)
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    focused = (focused - 1) % len(inputs)
                else:
                    focused = (focused + 1) % len(inputs)
                inputs[focused].set_active(True)
                continue

            res = inputs[focused].handle_event(event)
            if res == 'enter':
                return ('login', {'name': input_name.text, 'email': input_email.text, 'password': input_pass.text})

            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, inp in enumerate(inputs):
                    if inp.rect.collidepoint(event.pos):
                        inputs[focused].set_active(False)
                        focused = i
                        inputs[focused].set_active(True)
                        break
                if btn_login.is_clicked(event.pos):
                    return ('login', {'name': input_name.text, 'email': input_email.text, 'password': input_pass.text})
                if btn_register.is_clicked(event.pos):
                    return ('register', {'name': input_name.text, 'email': input_email.text, 'password': input_pass.text})

        draw_gradient_bg(screen, (0,0,50), (0,0,0))
        update_draw_stars(screen, stars)

        title = title_font.render('LOGIN', True, (255,255,255))
        screen.blit(title, title.get_rect(center=(screen.get_width()//2, 140)))

        lbl = small_font.render('Nombre:', True, (200,200,200))
        screen.blit(lbl, (180, 228))
        lbl = small_font.render('Email:', True, (200,200,200))
        screen.blit(lbl, (180, 278))
        lbl = small_font.render('Clave:', True, (200,200,200))
        screen.blit(lbl, (180, 328))

        input_name.draw(screen)
        input_email.draw(screen)
        input_pass.draw(screen)
        btn_login.draw(screen, mouse_pos)
        btn_register.draw(screen, mouse_pos)
        draw_messages(screen)

        pygame.display.flip()
        clock.tick(60)

    return ('back', {})

# --------------------- EJECUCIÓN PRINCIPAL ---------------------
if __name__ == '__main__':
    pygame.init()
    screen = pygame.display.set_mode((800,600))
    font = pygame.font.SysFont(None, 32)
    title_font = pygame.font.SysFont(None, 64)
    small_font = pygame.font.SysFont(None, 20)

    stars_global = init_stars(80, (screen.get_width(), screen.get_height()))

    while True:
        action, payload = show_login(screen, (font, title_font, small_font), stars_global)
        
        if action == 'quit':
            break

        elif action == 'register':
            success, msg = register_user_firestore(payload)
            if success:
                add_message("Registro exitoso! Inicia sesión...", font, (0,255,0), 3)
            else:
                add_message(translate_firebase_error(msg), font, (255,0,0), 4)
            print(msg)

        elif action == 'login':
            success, msg = login_user(payload)
            if success:
                add_message(f"Bienvenido {payload['name']}!", font, (0,255,0), 2)
                draw_messages(screen)
                pygame.display.flip()
                pygame.time.wait(500)
                # Establecer usuario actual en main y abrir el juego/menu
                from main import set_current_user, main
                set_current_user({'name': payload.get('name'), 'email': payload.get('email')})
                main()
                break
            else:
                add_message(translate_firebase_error(msg), font, (255,0,0), 3)
            print(msg)
