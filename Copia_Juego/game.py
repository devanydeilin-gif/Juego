import pygame
import random
import os

class Ship:
	def __init__(self, x, y):
		self.rect = pygame.Rect(x, y, 75, 50)
		self.speed = 7
		# intentar cargar sprite de nave desde assets/ship.png
		self.sprite = None
		try:
			# primero intentar la ruta absoluta que proporcionó el usuario
			user_img = r'C:\Users\devan\Desktop\Copia_Juego\nave.png'
			if os.path.exists(user_img):
				self.sprite = pygame.image.load(user_img).convert_alpha()
				self.sprite = pygame.transform.smoothscale(self.sprite, (self.rect.w, self.rect.h))
			else:
				img_path = os.path.join(os.path.dirname(__file__), 'assets', 'ship.png')
				if os.path.exists(img_path):
					self.sprite = pygame.image.load(img_path).convert_alpha()
					# escalar sprite al rect
					self.sprite = pygame.transform.smoothscale(self.sprite, (self.rect.w, self.rect.h))
		except Exception:
			self.sprite = None
		self.bullets = []

	def move(self, keys):
		if keys[pygame.K_LEFT] and self.rect.left > 0:
			self.rect.x -= self.speed
		if keys[pygame.K_RIGHT] and self.rect.right < 800:
			self.rect.x += self.speed
		if keys[pygame.K_UP] and self.rect.top > 0:
			self.rect.y -= self.speed
		if keys[pygame.K_DOWN] and self.rect.bottom < 600:
			self.rect.y += self.speed

	def shoot(self):
		bullet = pygame.Rect(self.rect.centerx-3, self.rect.top-10, 6, 12)
		self.bullets.append(bullet)

	def update_bullets(self):
		for bullet in self.bullets[:]:
			bullet.y -= 10
			if bullet.y < 0:
				self.bullets.remove(bullet)

	def draw(self, screen):
		if self.sprite:
			# dibujar sprite centrado en rect
			screen.blit(self.sprite, self.rect.topleft)
		else:
			# fallback: dibujar una nave poligonal (triángulo + ala)
			cx = self.rect.centerx
			cy = self.rect.centery
			w = self.rect.w
			h = self.rect.h
			# triángulo punta arriba
			points = [(cx, cy - h//2), (cx - w//2, cy + h//2), (cx + w//2, cy + h//2)]
			pygame.draw.polygon(screen, (0, 200, 255), points)
			# cockpit
			pygame.draw.circle(screen, (0, 120, 180), (cx, cy - 4), max(3, w//10))
		for bullet in self.bullets:
			pygame.draw.rect(screen, (255,255,0), bullet)

class Obstacle:
	def __init__(self, x, y, speed):
		self.rect = pygame.Rect(x, y, 75, 64)
		self.speed = speed
		# intentar cargar sprite para el obstáculo (ruta absoluta del usuario primero)
		self.sprite = None
		try:
			user_img = r'C:\Users\devan\Desktop\Copia_Juego\enemigos.png'
			if os.path.exists(user_img):
				self.sprite = pygame.image.load(user_img).convert_alpha()
				self.sprite = pygame.transform.smoothscale(self.sprite, (self.rect.w, self.rect.h))
			else:
				img_path = os.path.join(os.path.dirname(__file__), 'assets', 'enemy.png')
				if os.path.exists(img_path):
					self.sprite = pygame.image.load(img_path).convert_alpha()
					self.sprite = pygame.transform.smoothscale(self.sprite, (self.rect.w, self.rect.h))
		except Exception:
			self.sprite = None

	def update(self):
		self.rect.y += self.speed

	def draw(self, screen):
		if self.sprite:
			# dibujar sprite del enemigo
			screen.blit(self.sprite, self.rect.topleft)
		else:
			pygame.draw.rect(screen, (255,0,0), self.rect)

class Game:
	def __init__(self, screen, level_config, lives):
		self.screen = screen
		self.level_config = level_config
		self.lives = lives
		self.ship = Ship(375, 500)
		self.obstacles = []
		self.spawn_timer = 0
		self.score = 0
		# Kills = enemigos destruidos por disparos (persisten entre niveles dentro de la misma partida)
		self.kills = 0
		self.level_complete = False
		self.spawn_rate = level_config['spawn_rate']
		self.obstacle_speed = level_config['obstacle_speed']
		self.obstacles_to_pass = level_config['obstacles_to_pass']

	def reset(self, level_config, lives):
		self.level_config = level_config
		self.lives = lives
		self.ship = Ship(375, 500)
		self.obstacles = []
		self.spawn_timer = 0
		# Nota: no reiniciamos self.kills aquí para que el conteo de muertes
		# persista durante la sesión completa (varios niveles)
		self.score = 0
		self.level_complete = False
		self.spawn_rate = level_config['spawn_rate']
		self.obstacle_speed = level_config['obstacle_speed']
		self.obstacles_to_pass = level_config['obstacles_to_pass']

	def update(self):
		keys = pygame.key.get_pressed()
		self.ship.move(keys)
		if keys[pygame.K_SPACE]:
			if len(self.ship.bullets) < 5:
				self.ship.shoot()
		self.ship.update_bullets()

		self.spawn_timer += 1
		if self.spawn_timer >= self.spawn_rate:
			x = random.randint(0, max(0, 800 - 64))
			self.obstacles.append(Obstacle(x, -64, self.obstacle_speed))
			self.spawn_timer = 0

		for obstacle in self.obstacles[:]:
			obstacle.update()
			if obstacle.rect.top > 600:
				self.obstacles.remove(obstacle)
				self.score += 1
			# Colisión nave-obstáculo
			if obstacle.rect.colliderect(self.ship.rect):
				return "lose_life"
			# Colisión bala-obstáculo
			for bullet in self.ship.bullets[:]:
				if obstacle.rect.colliderect(bullet):
					# Eliminar bala y obstáculo y contar kill
					try:
						self.ship.bullets.remove(bullet)
					except ValueError:
						pass
					try:
						self.obstacles.remove(obstacle)
					except ValueError:
						pass
					self.kills += 1
					break

		if self.score >= self.obstacles_to_pass:
			return "level_complete"
		return None

	def draw(self):
		# Ya no limpiamos la pantalla aquí, lo hacemos en main.py
		self.ship.draw(self.screen)
		for obstacle in self.obstacles:
			obstacle.draw(self.screen)
