import arcade
import math
import random
import arcade.gui
from arcade.camera import Camera2D
import sqlite3
from stats_sender import StatsSender
import requests


# https://77.110.116.116:29254/cCjgKdsprM6geoQvp3/panel/
# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ИГРЫ ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCREEN_TITLE = "Battle Arena"

# Настройки графики и масштабирования
TILE_SCALING = 3
TILE_SIZE = 16
GRID_SIZE = TILE_SIZE * TILE_SCALING
CHARACTER_SCALING = 5
ENEMY_SCALE = 3
FLYING_SCALE = 1

# Настройки физики и баланса
SPEED = 2
ENEMY_SPEED = 2.5
SWORD_SPEED = 5.5
CAMERA_LERP = 0.12

# Предварительная загрузка шрифта для всех экранов
arcade.load_font("Kenney Future.ttf")


class Particle(arcade.Sprite):
    """ Класс визуального эффекта (частицы). """
    def __init__(self, x, y, color):
        """ Инициализация частицы в заданных координатах с выбранным цветом. """
        # Создаем круглую текстуру для частицы
        super().__init__(arcade.make_circle_texture(8, color))

        self.center_x = x
        self.center_y = y

        # Задаем случайное направление полета
        self.change_x = random.uniform(-5, 5)
        self.change_y = random.uniform(-5, 5)

        # Жизненный цикл частицы (в кадрах)
        self.lifetime = 60

        # Начальный размер
        self.width = 12
        self.height = 12

    def update(self, delta_time: float = 1 / 60):
        """ Обновление состояния частицы каждый кадр. """
        # Движение по осям
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Постепенное уменьшение прозрачности (исчезновение)
        if self.alpha > 10:
            self.alpha -= 255 / self.lifetime
        else:
            self.alpha = 0

        # Постепенное уменьшение размера частицы
        if self.width > 1:
            self.width *= 0.9
            self.height *= 0.9

        # Уменьшаем оставшееся время жизни
        self.lifetime -= 1

        # Удаляем частицу из игры, когда время жизни вышло
        if self.lifetime == 0:
            self.remove_from_sprite_lists()


class Sword(arcade.Sprite):
    """ Класс снаряда (меча), который выпускает игрок. """
    def __init__(self, file_name, scale, x, y, direction):
        """Инициализация меча: установка начальной позиции и вектора скорости."""
        super().__init__(file_name, scale)

        # Скорость вращения меча вокруг своей оси
        self.rotate_speed = 15

        self.center_x = x
        self.center_y = y
        self.speed = SWORD_SPEED

        # Определяем направление полета в зависимости от того, куда смотрел игрок
        if direction == "up":
            self.change_y = self.speed
        elif direction == "down":
            self.change_y = -self.speed
        elif direction == "left":
            self.change_x = -self.speed
        elif direction == "right":
            self.change_x = self.speed

    def update(self, delta_time: float):
        """ Обновление положения и угла поворота меча каждый кадр. """
        # Движение меча по координатам
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Вращение меча для визуального эффекта броска
        self.angle += self.rotate_speed


class Bossammo(arcade.Sprite):
    """ Класс снаряда, который выпускает Босс. """
    def __init__(self, x, y, target_x, target_y, texture_name):
        """ Инициализация снаряда босса с расчетом направления к цели. """
        super().__init__(texture_name, TILE_SCALING)

        self.center_x = x
        self.center_y = y
        self.angle = 0

        # Снаряды босса быстрее, чем обычное оружие
        self.rotate_speed = 15
        self.speed = SWORD_SPEED * 1.5

        # Расчет расстояния до цели (игрока)
        dist_x = target_x - x
        dist_y = target_y - y
        distance = math.sqrt(dist_x ** 2 + dist_y ** 2)

        # Математический расчет вектора движения (нормализация вектора)
        if distance > 0:
            self.change_x = (dist_x / distance) * self.speed
            self.change_y = (dist_y / distance) * self.speed

    def update(self, delta_time: float = 1 / 60):
        """ Обновление позиции и вращение снаряда. """
        # Движение снаряда по рассчитанному вектору
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Визуальное вращение снаряда в полете
        self.angle += self.rotate_speed


class Player(arcade.Sprite):
    """ Класс главного героя. """
    def __init__(self, skin_id):
        """ Инициализация игрока, загрузка всех текстур и установка начальных параметров. """
        super().__init__()

        # Характеристики игрока
        self.skin_id = skin_id
        self.hp = 3
        self.neyyazvimost = 0  # Таймер неуязвимости после получения урона
        self.otdacha_x = 0  # Переменные для эффекта отбрасывания (если планировалось)
        self.otdacha_y = 0

        # Состояние анимации
        self.last_direction = "right"
        self.current_frame = 0
        self.is_attacking = False
        self.scale = CHARACTER_SCALING

        # Настройки скорости анимации
        self.animation_timer = 0
        self.time_per_frame = 0.1  # Как быстро сменяются кадры (в секундах)

        # Словарь для хранения всех текстур анимаций
        self.animations = {
            "idle": {"up": [], "down": [], "left": [], "right": []},
            "walk": {"up": [], "down": [], "left": [], "right": []},
            "attack": {"up": [], "down": [], "left": [], "right": []},
        }

        # Автоматическая загрузка текстур из файлов по шаблону "действие направление_номер"
        if self.skin_id == 0:
            for action in self.animations:
                for direction in self.animations[action]:
                    for i in range(1, 5):
                        # Формируем имя файла
                        file = f"skin/{action} {direction}{i}.png"
                        self.animations[action][direction].append(arcade.load_texture(file))
        else:
            for action in self.animations:
                for direction in self.animations[action]:
                    for i in range(1, 5):
                        file = f"skin1/{action} {direction}{i}.png"
                        self.animations[action][direction].append(arcade.load_texture(file))

        # Установка начальной текстуры (игрок стоит лицом вправо)
        self.texture = self.animations["idle"]["right"][0]

    def update_animation(self, delta_time: float = 1 / 60):
        """ Логика выбора нужного кадра анимации в зависимости от скорости и действий. """
        # Таймер для контроля частоты смены кадров
        self.animation_timer += delta_time
        if self.animation_timer < self.time_per_frame:
            return

        self.animation_timer = 0
        self.current_frame += 1

        # Определение текущего действия для выбора списка текстур
        if self.is_attacking:
            action = "attack"
        elif self.change_x != 0 or self.change_y != 0:
            action = "walk"

            # Обновляем направление взгляда при движении
            if self.change_y > 0:
                self.last_direction = "up"
            elif self.change_y < 0:
                self.last_direction = "down"
            elif self.change_x > 0:
                self.last_direction = "right"
            elif self.change_x < 0:
                self.last_direction = "left"
        else:
            action = "idle"

        # Получаем список кадров для текущего действия и направления
        active_list = self.animations[action][self.last_direction]

        # Проверка на выход за пределы списка (зацикливание анимации)
        if self.current_frame >= len(active_list):
            self.current_frame = 0

            # Если закончилась анимация атаки, возвращаем игрока в состояние покоя
            if self.is_attacking:
                self.is_attacking = False
                active_list = self.animations["idle"][self.last_direction]

        # Установка итоговой текстуры на спрайт
        self.texture = active_list[self.current_frame]


class Enemy(arcade.Sprite):
    """ Базовый класс врага. """
    def __init__(self, x, y, wall_list, texture_name, napravlenie):
        """ Инициализация врага, его характеристик и типа движения. """
        super().__init__(texture_name, ENEMY_SCALE)

        self.state_timer = 0  # Таймер для смены действий при случайном блуждании
        self.naprav = napravlenie  # Тип движения: 1 - горизонт, 2 - вертикаль, 3 - свободный
        self.hp = 2

        # Переменные для реализации плавного отбрасывания назад
        self.otdacha_x = 0
        self.otdacha_y = 0

        self.center_x = x
        self.center_y = y
        self.wall_list = wall_list

        # Индивидуальная скорость (немного разная для каждого врага)
        self.speed = random.uniform(ENEMY_SPEED - 0.5, ENEMY_SPEED + 0.5)
        self.change_x = self.speed
        self.change_y = self.speed

        # Параметры для визуальных эффектов
        self.state_time = 0
        self.base_scale = ENEMY_SCALE * random.uniform(1, 1.5)

    def update(self, delta_time: float = 1 / 60):
        """ Обновление физики отдачи и визуальных эффектов (дыхание/покачивание). """
        old_x = self.center_x
        old_y = self.center_y

        # Обработка отдачи по оси X с проверкой столкновений
        self.center_x += self.otdacha_x
        if arcade.check_for_collision_with_list(self, self.wall_list):
            self.center_x = old_x
            self.otdacha_x = 0

        # Обработка отдачи по оси Y с проверкой столкновений
        self.center_y += self.otdacha_y
        if arcade.check_for_collision_with_list(self, self.wall_list):
            self.center_y = old_y
            self.otdacha_y = 0

        # Плавное затухание силы отдачи
        self.otdacha_x *= 0.9
        self.otdacha_y *= 0.9

        # Визуальный эффект "дыхания" через изменение масштаба (синусоида)
        self.state_time += 0.1
        self.scale = self.base_scale + math.sin(self.state_time) * 0.1

        # Визуальный эффект покачивания из стороны в сторону
        self.angle = math.sin(self.state_time * 2) * 5

    def patrol(self, delta_time: float = 1 / 60):
        """ Логика автоматического перемещения врага по карте. """

        # Режим 1: Патрулирование строго по горизонтали
        if self.naprav == 1:
            self.center_x += self.change_x
            if arcade.check_for_collision_with_list(self, self.wall_list):
                self.change_x *= -1
                self.center_x += self.change_x

        # Режим 2: Патрулирование строго по вертикали
        elif self.naprav == 2:
            self.center_y += self.change_y
            if arcade.check_for_collision_with_list(self, self.wall_list):
                self.change_y *= -1
                self.center_y += self.change_y

        # Режим 3: Случайное блуждание (броуновское движение)
        else:
            self.state_timer -= delta_time
            if self.state_timer <= 0:
                act = random.randint(0, 4)
                if act == 0:  # Стоять на месте
                    self.change_x = 0
                    self.change_y = 0
                elif act == 1:  # Идти влево
                    self.change_x = -self.speed
                    self.change_y = 0
                elif act == 2:  # Идти вправо
                    self.change_x = self.speed
                    self.change_y = 0
                elif act == 3:  # Идти вверх
                    self.change_x = 0
                    self.change_y = self.speed
                elif act == 4:  # Идти вниз
                    self.change_x = 0
                    self.change_y = -self.speed
                self.state_timer = random.uniform(1.0, 2.0)

            # Перемещение со столкновениями
            self.center_x += self.change_x
            if arcade.check_for_collision_with_list(self, self.wall_list):
                self.center_x -= self.change_x
                self.state_timer = 0  # Смена направления при ударе о стену

            self.center_y += self.change_y
            if arcade.check_for_collision_with_list(self, self.wall_list):
                self.center_y -= self.change_y
                self.state_timer = 0

    def presledovanie(self, player):
        """ Логика движения в сторону игрока с учетом препятствий. """
        dist_x = player.center_x - self.center_x
        dist_y = player.center_y - self.center_y
        distance = math.sqrt(dist_x ** 2 + dist_y ** 2)

        if distance > 0:
            move_x = (dist_x / distance) * self.speed
            move_y = (dist_y / distance) * self.speed

            # Пытаемся сделать шаг к игроку
            self.center_x += move_x
            self.center_y += move_y

            # Если упёрлись в стену — отменяем шаг
            if arcade.check_for_collision_with_list(self, self.wall_list):
                self.center_x -= move_x
                self.center_y -= move_y


class Bat(Enemy):
    """ Класс летучей мыши. Наследуется от Enemy. Особенность: игнорирует стены при движении (летает над ними) """
    def __init__(self, x, y, wall_list, player):
        """Инициализация мыши: передаем текстуру полета и фиксируем тип движения 3."""
        super().__init__(x, y, wall_list, "enemy_fly.png", napravlenie=3)

        self.player = player
        self.hp = 1

        # Летающие враги быстрее наземных
        self.speed = ENEMY_SPEED * 1.5
        self.base_scale = 3

    def update(self, delta_time: float = 1 / 60):
        """Обновление базовых эффектов (пульсация) из родительского класса."""
        super().update(delta_time)

    def presledovanie(self, player):
        """ Упрощенная логика преследования. """
        dist_x = player.center_x - self.center_x
        dist_y = player.center_y - self.center_y
        distance = math.sqrt(dist_x ** 2 + dist_y ** 2)

        if distance > 0:
            # Прямой полет к цели сквозь любые препятствия
            self.center_x += (dist_x / distance) * self.speed
            self.center_y += (dist_y / distance) * self.speed

    def patrol(self, delta_time: float = 1 / 60):
        """ Логика поведения мыши. """
        dist = arcade.get_distance_between_sprites(self, self.player)

        # Если дистанция до игрока больше 600 пикселей, начинаем сближение
        if dist >= 600:
            self.presledovanie(self.player)


class Boss(Enemy):
    """ Класс финального босса. """
    def __init__(self, x, y, wall_list, player):
        """ Инициализация босса: огромный масштаб, много HP и начальные таймеры атак. """
        super().__init__(x, y, wall_list, "boss.png", napravlenie=3)

        self.player = player
        self.hp = 20
        self.base_scale = 15
        self.alpha = 150  # Начальное значение прозрачности

        # Таймеры для контроля частоты выстрелов и ульты
        self.shoot_timer = 0
        self.ultra_timer = 0
        self.speed = 1

    def update(self, delta_time: float = 1 / 60):
        """ Обновление визуальных эффектов: босс плавно мерцает и меняет размер. """
        self.state_time += 0.1

        # Эффект изменения прозрачности через синус (от 100 до 220)
        self.alpha = int(160 + math.sin(self.state_time * 2) * 60)

        # Эффект пульсации масштаба
        self.scale = self.base_scale + math.sin(self.state_time) * 0.2

        # Легкое покачивание (вращение) для живости спрайта
        self.angle = math.sin(self.state_time * 1.5) * 4

    def boss_logic(self, delta_time, ammo_list):
        """ Интеллект босса. Вызывается отдельно в игровом цикле. """
        # --- ПЕРВАЯ ФАЗА: Дальний бой (Здоровье > 5) ---
        if self.hp > 5:
            self.patrol(delta_time)
            self.shoot_timer += delta_time
            self.ultra_timer += delta_time

            # Обычный выстрел в игрока раз в секунду
            if self.shoot_timer >= 1:
                self.shoot_timer = 0
                texture = random.choice(["boss_ammo1.png", "boss_ammo2.png", "boss_ammo3.png"])

                # Создаем снаряд, летящий в текущие координаты игрока
                ammo = Bossammo(self.center_x, self.center_y, self.player.center_x, self.player.center_y, texture)
                ammo_list.append(ammo)

            # Ультимативная атака по кругу раз в 5 секунд
            if self.ultra_timer >= 5:
                self.ultra_timer = 0
                self.ultra_attack(ammo_list)

        # --- ВТОРАЯ ФАЗА: Ярость (Здоровье <= 5) ---
        else:
            # Босс прекращает стрельбу, ускоряется и таранит игрока
            self.speed = 3
            self.presledovanie(self.player)

    def ultra_attack(self, ammo_list):
        """ Создает круговую волну из 8 снарядов, разлетающихся равномерно. """
        num_ammo = 8
        for i in range(num_ammo):
            # Рассчитываем угол для каждого снаряда (360 / 8 = 45 градусов)
            angle = math.radians(i * (360 / num_ammo))

            # Находим точку в пространстве, куда должен лететь снаряд для задания вектора
            target_x = self.center_x + math.cos(angle) * 100
            target_y = self.center_y + math.sin(angle) * 100

            texture = random.choice(["boss_ammo1.png", "boss_ammo2.png", "boss_ammo3.png"])
            ammo = Bossammo(self.center_x, self.center_y, target_x, target_y, texture)
            ammo_list.append(ammo)


class GameView(arcade.View):
    """ Основной игровой экран. """
    def __init__(self, username):
        """ Базовая инициализация и создание камер. """
        super().__init__()
        self.stats_api = StatsSender()
        self.world_camera = Camera2D()  # Камера, которая следует за игроком
        self.gui_camera = Camera2D()  # Статичная камера для интерфейса (HP, таймер)
        self.username = username

    def setup(self):
        """ Полная настройка игрового мира. """
        # --- ИНИЦИАЛИЗАЦИЯ СПИСКОВ СПРАЙТОВ ---
        self.player_list = arcade.SpriteList(use_spatial_hash=False)
        self.enemy_list = arcade.SpriteList(use_spatial_hash=False)
        self.sword_list = arcade.SpriteList(use_spatial_hash=False)
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.floor_list = arcade.SpriteList(use_spatial_hash=True)
        self.deco_list = arcade.SpriteList(use_spatial_hash=True)
        self.heart_list = arcade.SpriteList(use_spatial_hash=False)
        self.particle_lict = arcade.SpriteList()  # (Примечание: в названии опечатка 'lict')
        self.ammo_list = arcade.SpriteList()

        data = self.stats_api.get(self.username)
        self.skin_id = data["active_skin"]

        # Статистика для БД
        self.enemies_killed = 0
        self.bats_killed = 0
        self.bosses_killed = 0
        self.swords_thrown = 0
        self.swords_missed = 0
        self.swords_hitted = 0

        # --- ЗАГРУЗКА РЕСУРСОВ ---
        self.sounds = {
            "arena": arcade.load_sound("arena_music.mp3"),
            "hit": arcade.load_sound("hit.mp3"),
            "death": arcade.load_sound("death.mp3"),
            "wave": arcade.load_sound("newwave.mp3"),
            "sworddeath": arcade.load_sound("sworddeath.mp3"),
            "gameover": arcade.load_sound("gameover.mp3"),
            "victory": arcade.load_sound("victory.mp3"),
            "swordfly": arcade.load_sound("swordfly.mp3"),
        }

        self.music_now = None
        self.current_wave = 0
        self.wave_transition = True
        self.wave_timer = 3.0

        # --- ЗАГРУЗКА КАРТЫ (.tmx) ---
        map_name = "arena.tmx"
        tile_map = arcade.load_tilemap(map_name, scaling=TILE_SCALING)

        # Извлекаем слои из Tiled
        self.floor_list = tile_map.sprite_lists['floor']
        self.wall_list = tile_map.sprite_lists['walls']
        self.deco_list = tile_map.sprite_lists['decor']

        # Размеры мира для ограничения камеры
        self.world_w = tile_map.width * tile_map.tile_width * TILE_SCALING
        self.world_h = tile_map.height * tile_map.tile_height * TILE_SCALING

        # Настройка размеров вьюпорта камер
        self.world_camera.viewport_width = self.width
        self.world_camera.viewport_height = self.height
        self.gui_camera.viewport_width = self.width
        self.gui_camera.viewport_height = self.height

        # --- СОЗДАНИЕ ИГРОКА ---
        self.player = Player(self.skin_id)
        self.speed_up_timer = 3
        self.can_run = None
        self.boss = None

        # Центрируем игрока и настраиваем камеру на него
        self.player.center_x = self.width / 2
        self.player.center_y = self.height / 2
        self.player_list.append(self.player)
        self.world_camera.position = (self.player.center_x, self.player.center_y)

        # Управление и физика
        self.key_pressed = set()
        self.physics_engine = arcade.PhysicsEngineSimple(self.player, self.wall_list)

        # --- ИНТЕРФЕЙС (UI) ---
        self.timer = 0.0

        # Текст анонса новой волны
        self.wave_announce_text = arcade.Text(
            "",
            self.window.width / 2,
            self.window.height / 2,
            arcade.color.GOLD,
            font_size=70,
            anchor_x="center",
            font_name="Kenney Future"
        )

        # Счетчик времени
        self.timer_text = arcade.Text(
            "00:00",
            140,
            self.window.height - 170,
            arcade.color.BLACK,
            font_size=40,
            anchor_x="right",
        )

        # Текст текущей волны
        self.wave_count = arcade.Text(
            f"Волна: {self.current_wave}",
            20, self.window.height - 120,
            arcade.color.BLACK,
            font_size=40,
        )

        # Отрисовка сердечек здоровья (HP)
        for i in range(self.player.hp):
            heart = arcade.Sprite("HP.png", scale=0.05)
            heart.center_x = 60 + (i * 90)
            heart.center_y = self.window.height - 40
            self.heart_list.append(heart)

        # Состояния завершения игры
        self.win_timer = 1.5
        self.lose_timer = 1.5
        self.death_sound_played = False

    def on_show_view(self):
        """ Вызывается, когда экран становится активным. Запускает фоновую музыку. """
        if self.music_now is None:
            self.music_now = arcade.play_sound(self.sounds["arena"], volume=0.2, loop=True)

    def spawn_particles(self, x, y, color, count):
        """ Создает группу частиц заданного цвета в указанной точке. """
        for i in range(count):
            particle = Particle(x, y, color)
            self.particle_lict.append(particle)

    def spawn_wave(self):
        """ Логика появления врагов (Бесконечные волны). """

        # Проверяем, кратна ли текущая волна 10 (10, 20, 30...)
        is_boss_wave = (self.current_wave % 10 == 0)

        # ДИНАМИЧЕСКИЙ РАСЧЕТ ВРАГОВ
        if is_boss_wave:
            # На волне с боссом обычных врагов нет, но есть чуть-чуть мышей для сложности
            # Чем дальше босс, тем больше мышей (на 10-й - 4 мыши, на 20-й - 5 мышей)
            enemy_count = 0
            bat_count = 3 + (self.current_wave // 10)
        else:
            # С каждой волной обычных врагов всё больше!
            # Формула: 4 изначально + по 1-2 новых каждый раунд
            enemy_count = 4 + int(self.current_wave * 1.5)
            # Мыши прибавляются каждые две волны
            bat_count = 2 + (self.current_wave // 2)

        enemy_textures = ["enemy.png", "enemy2.png", "enemy3.png"]

        # 1. Спавн обычных наземных врагов
        for i in range(enemy_count):
            self.napravlenie = random.randint(1, 3)
            placed = False

            # Ищем подходящее место, чтобы враг не застрял в стене
            while not placed:
                rx = random.randint(200, int(self.world_w) - 200)
                ry = random.randint(200, int(self.world_h) - 200)
                r_texture = random.choice(enemy_textures)

                enemy = Enemy(rx, ry, self.wall_list, r_texture, self.napravlenie)

                wall_hit = arcade.check_for_collision_with_list(enemy, self.wall_list)
                dist_player = arcade.get_distance_between_sprites(enemy, self.player)

                if not wall_hit and dist_player > 350:
                    self.enemy_list.append(enemy)
                    placed = True

        # 2. Спавн летучих мышей
        for i in range(bat_count):
            rx = random.randint(150, SCREEN_WIDTH - 150)
            ry = random.randint(150, SCREEN_HEIGHT - 150)

            bat = Bat(rx, ry, self.wall_list, self.player)
            self.enemy_list.append(bat)

        # 3. Спавн Босса
        if is_boss_wave:
            # Босс всегда появляется в центре карты
            self.boss = Boss(self.world_w / 2, self.world_h / 2, self.wall_list, self.player)
            self.enemy_list.append(self.boss)

    def on_resize(self, width: int, height: int):
        """ Корректировка камер при изменении размера окна игры. """
        self.world_camera.viewport_width = width
        self.world_camera.viewport_height = height
        self.gui_camera.viewport_width = width
        self.gui_camera.viewport_height = height

    def on_draw(self):
        """ Отрисовка всех игровых объектов и интерфейса. """
        self.clear()

        # --- Отрисовка игрового мира ---
        self.world_camera.use()

        self.floor_list.draw(pixelated=True)
        self.deco_list.draw(pixelated=True)
        self.wall_list.draw(pixelated=True)

        self.particle_lict.draw(pixelated=False)
        self.player_list.draw(pixelated=True)
        self.enemy_list.draw(pixelated=True)
        self.ammo_list.draw(pixelated=True)
        self.sword_list.draw(pixelated=True)

        # --- Отрисовка интерфейса (GUI) ---
        self.gui_camera.use()

        self.timer_text.draw()
        self.wave_count.draw()
        self.heart_list.draw(pixelated=True)

        # Плашка с номером волны во время затишья
        if self.wave_transition:
            self.wave_announce_text.draw()

    def on_update(self, delta_time: float):
        """
        Сердце игрового цикла. Обрабатывает ввод, физику,
        столкновения, логику врагов и состояние игры.
        """
        self.particle_lict.update(delta_time)

        # --- ЛОГИКА ДВИЖЕНИЯ ИГРОКА ---
        self.dx = 0
        self.dy = 0
        if arcade.key.A in self.key_pressed:
            self.dx -= 1
        if arcade.key.D in self.key_pressed:
            self.dx += 1
        if arcade.key.W in self.key_pressed:
            self.dy += 1
        if arcade.key.S in self.key_pressed:
            self.dy -= 1

        base_speed = SPEED * 2 if self.skin_id == 1 else SPEED
        self.current_speed = base_speed

        is_moving = self.dx != 0 or self.dy != 0

        # Эффект пыли при ходьбе
        if is_moving:
            self.spawn_particles(self.player.center_x, self.player.center_y - 20, arcade.color.GRAY, count=1)

        # Логика выносливости (бега на LSHIFT)
        if self.speed_up_timer >= 3:
            self.can_run = True
        if self.speed_up_timer <= 0:
            self.can_run = False
            self.speed_up_timer = 0

        if arcade.key.LSHIFT in self.key_pressed and is_moving and self.can_run:
            self.speed_up_timer -= delta_time
            self.current_speed = base_speed * 2
        else:
            if not arcade.key.LSHIFT in self.key_pressed:
                if self.speed_up_timer < 3:
                    self.speed_up_timer += delta_time
                else:
                    self.speed_up_timer = 3

        # Применяем скорость и фиксируем диагональное движение (фактор 0.7071)
        self.dx *= self.current_speed
        self.dy *= self.current_speed
        if self.dx != 0 and self.dy != 0:
            factor = 0.7071
            self.dx *= factor
            self.dy *= factor

        self.player.change_x = self.dx
        self.player.change_y = self.dy

        # Обновление физики и анимаций игрока
        self.player_list.update()
        self.sword_list.update()
        self.player_list.update_animation(delta_time)
        self.physics_engine.update()

        # --- ЛОГИКА ВРАГОВ ---
        for enemy in self.enemy_list:
            if len(self.player_list) > 0:
                dist = arcade.get_distance_between_sprites(enemy, self.player)
                if dist < 600:
                    enemy.presledovanie(self.player)
                else:
                    enemy.patrol()
            else:
                enemy.patrol()
            enemy.update(delta_time)

        # --- ОБРАБОТКА СТОЛКНОВЕНИЙ МЕЧА ---
        for sword in self.sword_list:
            # Удар о стены
            if arcade.check_for_collision_with_list(sword, self.wall_list):
                self.swords_missed += 1
                arcade.play_sound(self.sounds["sworddeath"])
                self.spawn_particles(sword.center_x, sword.center_y, arcade.color.GRAY_ASPARAGUS, count=25)
                sword.remove_from_sprite_lists()
                continue

            # Попадание во врагов
            hit_list = arcade.check_for_collision_with_list(sword, self.enemy_list)
            for enemy in hit_list:
                self.swords_hitted += 1
                sword.remove_from_sprite_lists()
                enemy.hp -= 1

                if enemy.hp != 0:
                    arcade.play_sound(self.sounds["hit"])
                    self.spawn_particles(enemy.center_x, enemy.center_y, arcade.color.WHITE, count=15)

                # Эффект отдачи (не действует на Босса)
                if not isinstance(enemy, Boss):
                    diff_x = enemy.center_x - self.player.center_x
                    diff_y = enemy.center_y - self.player.center_y
                    dist = math.sqrt(diff_x ** 2 + diff_y ** 2)
                    if dist > 0:
                        enemy.otdacha_x = (diff_x / dist) * 12
                        enemy.otdacha_y = (diff_y / dist) * 12

                # Смерть врага
                if enemy.hp <= 0:
                    arcade.play_sound(self.sounds["death"])
                    if isinstance(enemy, Boss):
                        self.spawn_particles(enemy.center_x, enemy.center_y, arcade.color.RED_DEVIL, count=100)
                        self.shake = 60  # Тряска экрана при смерти босса
                        self.bosses_killed += 1
                    elif isinstance(enemy, Bat):
                        self.spawn_particles(enemy.center_x, enemy.center_y, arcade.color.RED_DEVIL, count=20)
                        self.bats_killed += 1
                    else:
                        self.spawn_particles(enemy.center_x, enemy.center_y, arcade.color.RED_DEVIL, count=25)
                        self.enemies_killed += 1
                    enemy.remove_from_sprite_lists()

        # --- НЕУЯЗВИМОСТЬ И УРОН ИГРОКУ ---
        if self.player.neyyazvimost > 0:
            self.player.neyyazvimost -= delta_time
            # Эффект мигания при получении урона
            if int(self.timer * 15) % 2 == 0:
                self.player.alpha = 100
            else:
                self.player.alpha = 255
        else:
            self.player.alpha = 255
            # Контакт с телом врага
            hit_list_player = arcade.check_for_collision_with_list(self.player, self.enemy_list)
            if hit_list_player:
                arcade.play_sound(self.sounds["hit"])
                self.player.hp -= 1
                self.spawn_particles(self.player.center_x, self.player.center_y, arcade.color.RED_DEVIL, count=40)
                self.player.neyyazvimost = 2.0

        # --- ЛОГИКА БОССА И СНАРЯДОВ ---
        if self.boss is not None and self.boss in self.enemy_list:
            self.boss.boss_logic(delta_time, self.ammo_list)

        self.ammo_list.update(delta_time)

        # Попадание снаряда босса в игрока
        hit_player = arcade.check_for_collision_with_list(self.player, self.ammo_list)
        for hit in hit_player:
            if self.player.neyyazvimost <= 0:
                arcade.play_sound(self.sounds["hit"])
                self.player.hp -= 1
                self.spawn_particles(self.player.center_x, self.player.center_y, arcade.color.RED_DEVIL, count=40)
                self.player.neyyazvimost = 2.0
            hit.remove_from_sprite_lists()

        # Удаление снарядов босса при ударе о стены
        for ammo in self.ammo_list:
            if arcade.check_for_collision_with_list(ammo, self.wall_list):
                ammo.remove_from_sprite_lists()

        # --- УПРАВЛЕНИЕ КАМЕРОЙ (Сглаживание и границы) ---
        target = (self.player.center_x, self.player.center_y)
        camera_x, camera_y = self.world_camera.position

        smooth = (camera_x + (target[0] - camera_x) * CAMERA_LERP,
                  camera_y + (target[1] - camera_y) * CAMERA_LERP)

        half_w = self.world_camera.viewport_width / 2
        half_h = self.world_camera.viewport_height / 2

        # Ограничиваем камеру краями карты
        cam_x = max(half_w, min(self.world_w - half_w, smooth[0]))
        cam_y = max(half_h, min(self.world_h - half_h, smooth[1]))

        # Эффект тряски экрана
        if hasattr(self, "shake") and self.shake > 0:
            cam_x += random.uniform(-self.shake, self.shake)
            cam_y += random.uniform(-self.shake, self.shake)
            self.shake *= 0.9

        self.world_camera.position = (cam_x, cam_y)
        self.gui_camera.position = (self.width / 2, self.height / 2)

        # --- ТАЙМЕР И ЛОГИКА ВОЛН ---
        self.timer += delta_time
        minutes = int(self.timer) // 60
        seconds = int(self.timer) % 60
        self.timer_text.text = f"{minutes:02d}:{seconds:02d}"

        # --- ЛОГИКА ПЕРЕХОДА ВОЛН (Бесконечный режим) ---
        if len(self.enemy_list) == 0 and not self.wave_transition:
            # Мы просто всегда переходим к следующей волне, так как "Победы" больше нет
            self.wave_transition = True
            self.wave_timer = 3.0

        # Переход между волнами
        if self.wave_transition:
            self.wave_timer -= delta_time

            # Обновляем текст анонса динамически
            next_wave_num = self.current_wave + 1
            if next_wave_num % 10 == 0:
                self.wave_announce_text.text = f"ВОЛНА {next_wave_num}: БОСС!"
            else:
                self.wave_announce_text.text = f"Следующая волна: {next_wave_num}"

            if self.wave_timer <= 0:
                if self.music_now:  # Проверка на музыку, чтобы не упало
                    arcade.play_sound(self.sounds["wave"], loop=False)
                self.wave_transition = False
                self.current_wave += 1
                self.wave_count.text = f"Волна: {self.current_wave}"
                self.spawn_wave()

        # --- ОБНОВЛЕНИЕ GUI HP ---
        if len(self.heart_list) > self.player.hp:
            self.heart_list.pop().remove_from_sprite_lists()
        elif len(self.heart_list) < self.player.hp and self.player.hp > 0:
            i = len(self.heart_list)
            heart = arcade.Sprite("HP.png", scale=0.05)
            heart.center_x = 60 + (i * 90)
            heart.center_y = self.window.height - 40
            self.heart_list.append(heart)

        # Проверка смерти игрока
        if self.player.hp <= 0:

            if not self.death_sound_played:
                arcade.play_sound(self.sounds["death"])
                self.death_sound_played = True
                game_stats = {
                    'username': self.username,
                    'total_wave': self.current_wave,
                    'deaths': 1,
                    'kills': self.enemies_killed + self.bats_killed + self.bosses_killed,
                    'bats_killed': self.bats_killed,
                    'enemies_killed': self.enemies_killed,
                    'bosses_defeated': self.bosses_killed,
                    'swords_thrown': self.swords_thrown,
                    'swords_hitted': self.swords_hitted,
                    'swords_missed': self.swords_missed,
                    'balance': (self.bats_killed * 2) + (self.enemies_killed * 3) + (self.bosses_killed * 10)
                }
                self.stats_api.send(game_stats)

            self.player.remove_from_sprite_lists()
            self.spawn_particles(self.player.center_x, self.player.center_y, arcade.color.RED_DEVIL, count=40)

            self.lose_timer -= delta_time
            if self.lose_timer <= 0:
                if self.music_now:
                    arcade.stop_sound(self.music_now)
                arcade.play_sound(self.sounds["gameover"])
                view = GameOver(self)
                self.window.show_view(view)
                return

    def on_key_press(self, key, modifiers):
        """ Обработка нажатий клавиш. """
        if len(self.player_list) == 0:
            return

        if key == arcade.key.ESCAPE:
            pause_view = PauseView(self)
            self.window.show_view(pause_view)
            return

        self.key_pressed.add(key)

        # Логика атаки
        if not self.player.is_attacking:
            attack_slovar = {
                arcade.key.UP: "up",
                arcade.key.DOWN: "down",
                arcade.key.LEFT: "left",
                arcade.key.RIGHT: "right"
            }
            if key in attack_slovar:
                self.swords_thrown += 1
                arcade.play_sound(self.sounds["swordfly"])
                self.player.last_direction = attack_slovar[key]
                self.player.is_attacking = True
                self.player.current_frame = 0
                sword = Sword(
                    "skin/sword.png",
                    TILE_SCALING,
                    self.player.center_x,
                    self.player.center_y,
                    self.player.last_direction,
                )
                self.sword_list.append(sword)

    def on_key_release(self, key, modifiers):
        """ Обработка отпускания клавиш. """
        if key in self.key_pressed:
            self.key_pressed.remove(key)


class PauseView(arcade.View):
    """ Экран паузы. """
    def __init__(self, game_view):
        """ Инициализация экрана паузы с сохранением ссылки на текущую игру. """
        super().__init__()
        arcade.load_font("Kenney Future.ttf")

        self.game_view = game_view

        # Настройка интерфейса
        self.manager = arcade.gui.UIManager()
        self.anchor_layout = arcade.gui.UIAnchorLayout()
        self.v_box = arcade.gui.UIBoxLayout(space_between=20)

        # Текст заголовка
        pause_label = arcade.gui.UILabel(
            text="Пауза",
            font_size=35,
            font_name="Kenney Future",
            text_color=arcade.color.WHITE
        )
        self.v_box.add(pause_label)

        # Кнопка возврата в игру
        resume_button = arcade.gui.UIFlatButton(text="Продолжить", width=200)
        resume_button.on_click = self.on_click_resume
        self.v_box.add(resume_button)

        back_button = arcade.gui.UIFlatButton(text='В меню', width=200)
        back_button.on_click = self.on_click_exit
        self.v_box.add(back_button)
        # Компоновка элементов по центру
        self.anchor_layout.add(
            child=self.v_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.manager.add(self.anchor_layout)

    def on_click_resume(self, event):
        """ Возвращает игрока на тот же экран игры, с которого была вызвана пауза. """
        self.window.show_view(self.game_view)

    def on_click_exit(self, event):
        """ Возвращает игрока на экран менюшки"""
        if self.game_view.music_now:
            arcade.stop_sound(self.game_view.music_now)
            self.game_view.music_now = None
        username = self.game_view.username
        self.window.show_view(MenuView(username=username))

    def on_show_view(self):
        """ Включение менеджера интерфейса. """
        self.manager.enable()

    def on_hide_view(self):
        """ Отключение менеджера при закрытии паузы. """
        self.manager.disable()

    def on_draw(self):
        """ Отрисовка фона игры с эффектом затемнения и меню паузы. """
        self.clear()

        # Рисуем текущее состояние игры на заднем плане
        self.game_view.on_draw()

        # Создаем прямоугольник на весь экран для эффекта затемнения
        overlay_rect = arcade.rect.Rect(
            x=0,
            y=0,
            width=SCREEN_WIDTH * 2,
            height=SCREEN_HEIGHT * 2,
            left=0,
            right=self.window.width,
            top=0,
            bottom=self.window.height
        )

        # Рисуем полупрозрачный черный слой (150 из 255 прозрачности)
        arcade.draw_rect_filled(
            rect=overlay_rect,
            color=(0, 0, 0, 150)
        )

        # Отрисовка кнопок паузы
        self.manager.draw()


class GameOver(arcade.View):
    """ Экран поражения. """
    def __init__(self, game_view):
        """ Инициализация экрана завершения игры. """
        super().__init__()
        arcade.load_font("Kenney Future.ttf")

        self.game_view = game_view

        # Настройка интерфейса
        self.manager = arcade.gui.UIManager()
        self.v_box = arcade.gui.UIBoxLayout(space_between=20)

        # Главная надпись поражения
        label = arcade.gui.UILabel(
            text="GAME OVER",
            font_size=50,
            font_name="Kenney Future",
            text_color=arcade.color.RED
        )
        self.v_box.add(label)

        # Кнопка возврата в меню
        menu_button = arcade.gui.UIFlatButton(text="В главное меню", width=300)
        menu_button.on_click = self.on_click_menu
        self.v_box.add(menu_button)

        # Центрирование элементов
        self.anchor_layout = arcade.gui.UIAnchorLayout()
        self.anchor_layout.add(child=self.v_box, anchor_x="center_x", anchor_y="center_y")
        self.manager.add(self.anchor_layout)

    def on_click_menu(self, event):
        """ Возвращает игрока в стартовое меню. """
        username = self.game_view.username
        self.window.show_view(MenuView(username=username))

    def on_show_view(self):
        """ Включение менеджера UI при отображении экрана. """
        self.manager.enable()

    def on_hide_view(self):
        """ Отключение менеджера UI. """
        self.manager.disable()

    def on_draw(self):
        """ Отрисовка фона (последний кадр игры) и текста поражения. """
        self.clear()

        # Отрисовываем игру на фоне
        self.game_view.on_draw()

        # Полупрозрачное черное наложение для читаемости текста
        overlay_rect = arcade.rect.Rect(
            x=0,
            y=0,
            width=SCREEN_WIDTH * 2,
            height=SCREEN_HEIGHT * 2,
            left=0,
            right=self.window.width,
            top=0,
            bottom=self.window.height
        )

        arcade.draw_rect_filled(
            rect=overlay_rect,
            color=(0, 0, 0, 150)
        )

        self.manager.draw()


class MenuView(arcade.View):
    """ Главное меню игры. """
    def __init__(self, username=None):
        super().__init__()

        # Ресурсы и шрифты
        self.music = arcade.load_sound("menu_music.mp3")
        self.music_now = None
        arcade.load_font("Kenney Future.ttf")
        self.background = arcade.load_texture("fon.png")
        self.username = username

        # Настройка UI менеджера
        self.manager = arcade.gui.UIManager()
        self.anchor_layout = arcade.gui.UIAnchorLayout()

        # Текстура для кнопок и полей ввода
        texture = arcade.load_texture("menuknopka.png")
        patch = arcade.gui.NinePatchTexture(
            texture=texture,
            left=12, right=12, bottom=12, top=12,
        )

        # Общий стиль для всех кнопок меню
        button_style = {
            "normal": {
                "font_name": "Kenney Future",
                "font_size": 15,
                "font_color": arcade.color.DARK_BLUE_GRAY
            },
            "hover": {
                "font_name": "Kenney Future",
                "font_size": 15,
                "font_color": arcade.color.BLACK
            },
            "press": {
                "font_name": "Kenney Future",
                "font_size": 15,
                "font_color": arcade.color.WHITE
            }
        }

        # Контейнер для вертикального расположения элементов
        self.v_box = arcade.gui.UIBoxLayout(space_between=35)

        if self.username:
            nickname_label = arcade.gui.UILabel(
                text=f"👤 {self.username}",
                font_size=30,
                font_name="Kenney Future",
                text_color=arcade.color.GOLD
            )
            self.v_box.add(nickname_label)

        # Заголовок игры
        self.label = arcade.gui.UILabel(
            text="BATTLE ARENA",
            font_size=45,
            font_name="Kenney Future",
            text_color=arcade.color.GOLD
        )
        self.v_box.add(self.label)
        # Кнопка старта
        self.start_button = arcade.gui.UITextureButton(
            text="Начать игру",
            texture=patch,
            texture_hovered=patch,
            width=300,
            height=60,
            style=button_style
        )
        self.v_box.add(self.start_button)

        if not self.username:
            login_button = arcade.gui.UITextureButton(
                text="Войти / Регистрация",
                texture=patch,
                texture_hovered=patch,
                width=300,
                height=60,
                style=button_style
            )
            login_button.on_click = self.on_click_login
            self.v_box.add(login_button)
        else:
            logout_button = arcade.gui.UITextureButton(
                text="Выход из аккаунта",
                texture=patch,
                texture_hovered=patch,
                width=300,
                height=60,
                style=button_style
            )
            logout_button.on_click = self.on_click_logout
            self.v_box.add(logout_button)

        # Привязка событий
        self.start_button.on_click = self.on_click_start

        # Центрирование всего блока меню
        self.anchor_layout.add(child=self.v_box, anchor_x="center_x", anchor_y="center_y")
        self.manager.add(self.anchor_layout)

    def on_show_view(self):
        """ Включает UI и музыку при входе в меню. """
        self.manager.enable()
        if not self.music_now:
            self.music_now = arcade.play_sound(self.music, volume=0.8, loop=True)

    def on_click_login(self, event):
        if self.music_now:
            arcade.stop_sound(self.music_now)
            self.music_now = None
        self.window.show_view(LoginView())

    def on_click_logout(self, event):
        if self.music_now:
            arcade.stop_sound(self.music_now)
            self.music_now = None
        self.window.show_view(MenuView(username=None))

    def on_click_start(self, event):
        """ Логика проверки никнейма и запуска основной игры. """
        # Получаем текст и убираем лишние пробелы
        if not self.username:
            self.on_click_login(None)
            return
        if self.music_now:
            arcade.stop_sound(self.music_now)
            self.music_now = None
        # Запускаем игру, передавая очищенный никнейм
        game_view = GameView(self.username)
        game_view.setup()
        self.window.show_view(game_view)

    def on_hide_view(self):
        """ Отключение менеджера при уходе со страницы. """
        self.manager.disable()

    def on_draw(self):
        """ Отрисовка фона и элементов интерфейса. """
        self.clear()
        arcade.draw_texture_rect(self.background, arcade.rect.XYWH(
            self.window.width / 2, self.window.height / 2, SCREEN_WIDTH, SCREEN_HEIGHT * 1.5))
        self.manager.draw()


class LoginView(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.load_font("Kenney Future.ttf")
        self.music = arcade.load_sound("menu_music.mp3")
        self.music_now = None
        self.background = arcade.load_texture("fon.png")
        self.manager = arcade.gui.UIManager()
        self.anchor_layout = arcade.gui.UIAnchorLayout()
        texture = arcade.load_texture("menuknopka.png")
        patch = arcade.gui.NinePatchTexture(
            texture=texture,
            left=12, right=12, bottom=12, top=12,
        )
        button_style = {
            "normal": {
                "font_name": "Kenney Future",
                "font_size": 15,
                "font_color": arcade.color.DARK_BLUE_GRAY
            },
            "hover": {
                "font_name": "Kenney Future",
                "font_size": 15,
                "font_color": arcade.color.BLACK
            },
            "press": {
                "font_name": "Kenney Future",
                "font_size": 15,
                "font_color": arcade.color.WHITE
            }
        }
        self.v_box = arcade.gui.UIBoxLayout(space_between=20)
        title = arcade.gui.UILabel(
            text="ВХОД В АККАУНТ",
            font_size=45,
            font_name="Kenney Future",
            text_color=arcade.color.GOLD
        )
        self.v_box.add(title)
        self.username_input = arcade.gui.UIInputText(
            text='Логин',
            width=400,
            height=50,
            font_size=20,
            font_name="Kenney Future",
            text_color=arcade.color.BLACK,
            text_align="center"
        )
        self.username_input.style = {
            "normal": {"bg_color": (0, 0, 0, 0), "border_width": 0, "font_color": arcade.color.BLACK},
            "focused": {"bg_color": (0, 0, 0, 0), "border_width": 0, "font_color": arcade.color.BLACK}
        }
        username_bg = self.username_input.with_background(texture=patch).with_padding(top=10, left=10)
        self.v_box.add(username_bg.with_border(width=0))
        self.password_input = arcade.gui.UIInputText(
            text='Пароль',
            width=400,
            height=50,
            font_size=20,
            font_name="Kenney Future",
            text_color=arcade.color.BLACK,
            text_align="center"
        )
        self.password_input.style = {
            "normal": {"bg_color": (0, 0, 0, 0), "border_width": 0, "font_color": arcade.color.BLACK},
            "focused": {"bg_color": (0, 0, 0, 0), "border_width": 0, "font_color": arcade.color.BLACK}
        }
        password_bg = self.password_input.with_background(texture=patch).with_padding(top=10, left=10)
        self.v_box.add(password_bg.with_border(width=0))
        self.error_label = arcade.gui.UILabel(
            text="",
            font_size=16,
            font_name="Kenney Future",
            text_color=arcade.color.RED
        )
        self.v_box.add(self.error_label)
        login_button = arcade.gui.UITextureButton(
            text="Войти",
            texture=patch,
            texture_hovered=patch,
            width=300,
            height=60,
            style=button_style
        )
        login_button.on_click = self.on_login
        self.v_box.add(login_button)
        register_button = arcade.gui.UITextureButton(
            text="Регистрация",
            texture=patch,
            texture_hovered=patch,
            width=300,
            height=60,
            style=button_style
        )
        register_button.on_click = self.on_register
        self.v_box.add(register_button)
        self.anchor_layout.add(child=self.v_box, anchor_x="center_x", anchor_y="center_y")
        self.manager.add(self.anchor_layout)

    def on_show_view(self):
        self.manager.enable()
        if not self.music_now:
            self.music_now = arcade.play_sound(self.music, volume=0.8, loop=True)

    def on_hide_view(self):
        self.manager.disable()

    def on_login(self, event):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        if not username or not password:
            self.error_label.text = "Заполните все поля"
            return
        try:
            response = requests.post(
                'http://127.0.0.1:8080/api/game/login',
                json={'username': username, 'password': password},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.error_label.text = f" Добро пожаловать, {username}!"
                if self.music_now:
                    arcade.stop_sound(self.music_now)
                    self.music_now = None
                game_view = GameView(username)
                game_view.setup()
                self.window.show_view(MenuView(username=username))
            elif response.status_code == 401:
                self.error_label.text = "Неверный логин или пароль"
                self.password_input.text = ''
            else:
                self.error_label.text = f"Ошибка сервера: {response.status_code}"
        except requests.exceptions.ConnectionError:
            self.error_label.text = "Нет соединения с сервером"

    def on_register(self, event):
        if self.music_now:
            arcade.stop_sound(self.music_now)
            self.music_now = None
        self.window.show_view(RegisterView())

    def on_draw(self):
        self.clear()
        arcade.draw_texture_rect(self.background, arcade.rect.XYWH(
            self.window.width / 2, self.window.height / 2, SCREEN_WIDTH, SCREEN_HEIGHT * 1.5))
        self.manager.draw()


class RegisterView(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.load_font("Kenney Future.ttf")
        self.music = arcade.load_sound("menu_music.mp3")
        self.music_now = None
        self.background = arcade.load_texture("fon.png")
        self.manager = arcade.gui.UIManager()
        self.anchor_layout = arcade.gui.UIAnchorLayout()
        texture = arcade.load_texture("menuknopka.png")
        patch = arcade.gui.NinePatchTexture(
            texture=texture,
            left=12, right=12, bottom=12, top=12,
        )
        button_style = {
            "normal": {
                "font_name": "Kenney Future",
                "font_size": 15,
                "font_color": arcade.color.DARK_BLUE_GRAY
            },
            "hover": {
                "font_name": "Kenney Future",
                "font_size": 15,
                "font_color": arcade.color.BLACK
            },
            "press": {
                "font_name": "Kenney Future",
                "font_size": 15,
                "font_color": arcade.color.WHITE
            }
        }
        self.v_box = arcade.gui.UIBoxLayout(space_between=20)
        title = arcade.gui.UILabel(
            text="РЕГИСТРАЦИЯ",
            font_size=45,
            font_name="Kenney Future",
            text_color=arcade.color.GOLD
        )
        self.v_box.add(title)
        self.username_input = arcade.gui.UIInputText(
            text='Логин',
            width=400,
            height=50,
            font_size=20,
            font_name="Kenney Future",
            text_color=arcade.color.BLACK,
            text_align="center"
        )
        self.username_input.style = {
            "normal": {"bg_color": (0, 0, 0, 0), "border_width": 0, "font_color": arcade.color.BLACK},
            "focused": {"bg_color": (0, 0, 0, 0), "border_width": 0, "font_color": arcade.color.BLACK}
        }
        username_bg = self.username_input.with_background(texture=patch).with_padding(top=10, left=10)
        self.v_box.add(username_bg.with_border(width=0))
        self.password_input = arcade.gui.UIInputText(
            text='Пароль (мин. 6 символов)',
            width=400,
            height=50,
            font_size=20,
            font_name="Kenney Future",
            text_color=arcade.color.BLACK,
            text_align="center"
        )
        self.password_input.style = {
            "normal": {"bg_color": (0, 0, 0, 0), "border_width": 0, "font_color": arcade.color.BLACK},
            "focused": {"bg_color": (0, 0, 0, 0), "border_width": 0, "font_color": arcade.color.BLACK}
        }
        password_bg = self.password_input.with_background(texture=patch).with_padding(top=10, left=10)
        self.v_box.add(password_bg.with_border(width=0))
        self.error_label = arcade.gui.UILabel(
            text="",
            font_size=16,
            font_name="Kenney Future",
            text_color=arcade.color.RED
        )
        self.v_box.add(self.error_label)
        register_button = arcade.gui.UITextureButton(
            text="Зарегистрироваться",
            texture=patch,
            texture_hovered=patch,
            width=300,
            height=60,
            style=button_style
        )
        register_button.on_click = self.on_register
        self.v_box.add(register_button)
        login_button = arcade.gui.UITextureButton(
            text="Уже есть аккаунт?",
            texture=patch,
            texture_hovered=patch,
            width=300,
            height=60,
            style=button_style
        )
        login_button.on_click = self.on_login
        self.v_box.add(login_button)
        self.anchor_layout.add(child=self.v_box, anchor_x="center_x", anchor_y="center_y")
        self.manager.add(self.anchor_layout)

    def on_show_view(self):
        self.manager.enable()
        if not self.music_now:
            self.music_now = arcade.play_sound(self.music, volume=0.8, loop=True)

    def on_hide_view(self):
        self.manager.disable()

    def on_register(self, event):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        if not username or not password:
            self.error_label.text = "Заполните все поля"
            return

        if len(username) < 2:
            self.error_label.text = "Логин должен быть минимум 2 символа"
            return

        if len(password) < 6:
            self.error_label.text = "Пароль должен быть минимум 6 символов"
            return
        try:
            response = requests.post(
                'http://127.0.0.1:8080/api/game/register',
                json={'username': username, 'password': password},
                timeout=5
            )
            if response.status_code == 201:
                self.error_label.text = f"Аккаунт создан!"
                if self.music_now:
                    arcade.stop_sound(self.music_now)
                    self.music_now = None
                game_view = GameView(username)
                game_view.setup()
                self.window.show_view(MenuView(username=username))
            elif response.status_code == 409:
                self.error_label.text = "Этот логин уже используется"
                self.username_input.text = ''
            else:
                self.error_label.text = f"Ошибка сервера: {response.status_code}"
        except requests.exceptions.ConnectionError:
            self.error_label.text = "Нет соединения с сервером"

    def on_login(self, event):
        if self.music_now:
            arcade.stop_sound(self.music_now)
            self.music_now = None
        self.window.show_view(LoginView())

    def on_draw(self):
        self.clear()
        arcade.draw_texture_rect(self.background, arcade.rect.XYWH(
            self.window.width / 2, self.window.height / 2, SCREEN_WIDTH, SCREEN_HEIGHT * 1.5))
        self.manager.draw()

def main():
    """ Главная точка входа в приложение. """
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
    menu_view = MenuView()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()
