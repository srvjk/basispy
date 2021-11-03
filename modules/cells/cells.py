import basis
import sys
import random
from enum import Enum
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl
import glm
from PIL import Image
from numpy import asarray


class Link:
    def __init__(self):
        self.weight = 0
        self.src_neuron = None
        self.dst_neuron = None
        self.weight = 1.0  # вес связи без учета её знака
        self.sign = 1  # знак связи (+1 для возбуждающих и -1 для тормозящих связей)


class BasicNeuron:
    def __init__(self):
        self.out_links = list()
        self.pos = [0, 0]
        self.pre_mediator_quantity = 0
        self.post_mediator_quantity = 0
        self.firing_mediator_threshold = 1.0  # порог количества медиатора, необходимый для срабатывания
        self.out_mediator_quantum = 0.1  # количество медиатора, которое будет отправлено нейронам-получателям

    def set_activity(self, activity):
        pass

    def is_active(self):
        if self.post_mediator_quantity >= self.firing_mediator_threshold:
            return True
        return False

    def add_mediator(self, mediator_quantity):
        pass

    def fire(self):
        pass

    def swap_mediator_buffers(self):
        pass


class Sensor(BasicNeuron):
    def __init__(self):
        super().__init__()

    def set_activity(self, activity):
        if activity:
            self.post_mediator_quantity = self.firing_mediator_threshold
        else:
            self.post_mediator_quantity = 0


class Neuron(BasicNeuron):
    def __init__(self):
        super().__init__()

    def add_mediator(self, mediator_quantity):
        self.pre_mediator_quantity += mediator_quantity

    def fire(self):
        """
        Рабочая функция нейрона - 'выстрел' потенциала действия

        Раздаёт медиатор по всем исходящим связям с учетом их весов и полярностей.
        Кол-во медиатора фиксировано для данного нейрона, но при передаче умножается на вес и полярность связи,
        так что разные постсинаптические нейроны получат разное итоговое кол-во медиатора.
        """
        if self.post_mediator_quantity >= self.firing_mediator_threshold:
            for link in self.out_links:
                link.dst_neuron.add_mediator(self.out_mediator_quantum * link.weight * link.sign)

    def swap_mediator_buffers(self):
        self.post_mediator_quantity = self.pre_mediator_quantity
        self.pre_mediator_quantity = 0


class Layer:
    def __init__(self, name):
        self.name = name
        self.neurons = list()

    def create(self, neur_num, neur_class):
        self.neurons = [neur_class() for _ in range(neur_num)]

    def connect(self, target_layer):
        for src in self.neurons:
            for dst in target_layer.neurons:
                # прямые связи:
                fwd_link = Link()
                fwd_link.src_neuron = src
                fwd_link.dst_neuron = dst
                src.out_links.append(fwd_link)

                # обратные связи
                back_link = Link()
                back_link.src_neuron = dst
                back_link.dst_neuron = src
                dst.out_links.append(back_link)


class Net(basis.Entity):
    def __init__(self):
        super().__init__()
        self.layers = list()

    def new_layer(self, layer_name, neur_num, neur_class):
        layer = Layer(layer_name)
        layer.create(neur_num, neur_class)
        self.layers.append(layer)
        return layer

    def print(self):
        print("Layers: {}".format(len(self.layers)))
        for layer in self.layers:
            print("{}: {}".format(layer.name, len(layer.neurons)))

    def step(self):
        super().step()

        # фаза 1: пройтись во всем нейронам и активировать, какие надо
        # порядок обхода не имеет значения
        for layer in self.layers:
            for neuron in layer.neurons:
                neuron.fire()

        # фаза 2: поменять местами буферы накопления активности для следующей итерации
        for layer in self.layers:
            for neuron in layer.neurons:
                neuron.swap_mediator_buffers()


class AgentAction(Enum):
    NoAction = 0,
    MoveForward = 1,
    TurnLeft = 2,
    TurnRight = 3


class Obstacle(basis.Entity):
    def __init__(self):
        super().__init__()
        self.position = glm.vec2(0, 0)


class Agent(basis.Entity):
    def __init__(self):
        super().__init__()
        self.board = None
        self.position = glm.vec2(0, 0)
        self.orientation = glm.vec2(1, 0)

        # neural net
        self.net = self.new(Net)
        layer1 = self.net.new_layer("in", 8, Sensor)
        layer2 = self.net.new_layer("mid", 4, Neuron)
        layer3 = self.net.new_layer("out", 2, Neuron)
        layer1.connect(layer2)
        layer2.connect(layer3)
        self.system.activate(self.net)

    def set_board(self, board):
        self.board = board
        self.board.add_agent(self)

    def step(self):
        if not self.board:
            return

        '''
        front_sensor_color = self.board.get_cell_color(
            self.position[0] + self.orientation[0], self.position[1] + self.orientation[1])
        sensor_active = False
        if front_sensor_color != self.board.back_color and front_sensor_color != self.board.color_no_color:
            sensor_active = True
        self.net.layers[0].neurons[0].set_activity(sensor_active)
        '''

        choice = random.choice(list(AgentAction))
        if choice == AgentAction.NoAction:
            pass
        if choice == AgentAction.MoveForward:
            self.position += self.orientation
            self.position.x = max(0, self.position.x)
            self.position.x = min(self.position.x, self.board.size - 1)
            self.position.y = max(0, self.position.y)
            self.position.y = min(self.position.y, self.board.size - 1)
        if choice == AgentAction.TurnLeft:
            self.orientation = glm.rotate(self.orientation, glm.pi() / 2.0)
        if choice == AgentAction.TurnRight:
            self.orientation = glm.rotate(self.orientation, -glm.pi() / 2.0)


def angle(vec1, vec2):
    """
    Вычислить ориентированный угол (в радианах) между двумя векторами.
    Положительное направление вращения - против часовой стрелки от vec1 к vec2.
    """
    sign = 1.0
    len_1_len_2 = glm.length(vec1) * glm.length(vec2)
    dot = glm.dot(vec1, vec2)

    epsilon = 1e-6
    if abs(dot) < epsilon:
        pseudo_dot = vec1.x * vec2.y - vec2.x * vec1.y
        sin_alpha = pseudo_dot / len_1_len_2
        if sin_alpha < 0:
            sign = -1.0

    ang = glm.acos(dot / len_1_len_2)
    double_pi = glm.pi() * 2.0
    n = glm.floor(ang / double_pi)
    if n > 0:
        ang -= n * double_pi

    return sign * ang


class Board(basis.Entity):
    def __init__(self):
        super().__init__()
        self.agents = list()
        self.obstacles = list()
        self.size = 100
        self.cell_size = 3
        #self.visual_field = pygame.Surface((self.size_in_pixels(), self.size_in_pixels()))
        #self.compressed_visual_field = pygame.Surface((self.size, self.size))  # поле, сжатое до 1 пиксела на клетку
        self.back_color = (10, 10, 10)
        self.color_no_color = (0, 0, 0)  # цвет для обозначения пространства за пределами поля и т.п.

    def size_in_cells(self):
        return self.size

    def size_in_pixels(self):
        return self.size * self.cell_size

    def add_agent(self, agent):
        self.agents.append(agent)

    def create_obstacles(self, density):
        num_cells = self.size * self.size
        num_obstacles = int(num_cells * density)
        for i in range(num_obstacles):
            x = random.randrange(0, self.size)
            y = random.randrange(0, self.size)
            obstacle = Obstacle()
            obstacle.position = glm.vec2(x, y)
            self.obstacles.append(obstacle)

    def get_cell_color(self, x, y):
        if x < 0 or x >= self.size or y < 0 or y >= self.size:
            return self.color_no_color
        return self.compressed_visual_field.get_at((x, y))

    def draw(self, renderer, pos, size):
        x0 = pos[0]
        y0 = pos[1]
        width = size[0]
        height = size[1]
        cell_width = width / self.size
        cell_height = height / self.size

        resource_manager = self.system.find_entity_by_name("ResourceManager")

        polygon = Polygon(resource_manager.get_shader("polygon"))
        polygon.set_points([
            glm.vec2(0.0, 0.0),
            glm.vec2(1.0, 0.0),
            glm.vec2(1.0, 1.0),
            glm.vec2(0.0, 1.0),
            glm.vec2(0.0, 0.0)
        ])
        polygon.draw(glm.vec2(x0, y0), glm.vec2(width, height), 0.0, glm.vec3(0.1, 0.1, 0.1), True)

        for obstacle in self.obstacles:
            if isinstance(obstacle, Obstacle):
                try:
                    renderer.draw_sprite(resource_manager.get_texture("obstacle"),
                                         glm.vec2(x0 + obstacle.position.x * cell_width,
                                                  y0 + obstacle.position.y * cell_height),
                                         glm.vec2(cell_width, cell_height), 0.0, glm.vec3(1.0))
                except AttributeError:
                    pass

        for agent in self.agents:
            if isinstance(agent, Agent):
                try:
                    ang = angle(glm.vec2(1, 0), agent.orientation)
                    renderer.draw_sprite(resource_manager.get_texture("agent"),
                                         glm.vec2(x0 + agent.position.x * cell_width,
                                                  y0 + agent.position.y * cell_height),
                                         glm.vec2(cell_width, cell_height), glm.degrees(ang), glm.vec3(1.0))
                except AttributeError:
                    pass

        # после всей отрисовки создаём вспомогательное сжатое представление доски:
        #pygame.transform.scale(self.visual_field, (self.size, self.size), self.compressed_visual_field)

        for agent in self.agents:
            if isinstance(agent, Agent):
                agent_center = glm.vec2(x0 + agent.position.x * cell_width + 0.5 * cell_width,
                                        y0 + agent.position.y * cell_height + 0.5 * cell_height)
                polygon = Polygon(resource_manager.get_shader("polygon"))
                polygon.set_points([
                    glm.vec2(0.0, 0.0),
                    agent.orientation
                ])
                polygon.draw(agent_center, glm.vec2(cell_width, cell_width), 0.0, glm.vec3(1.0, 1.0, 0.5), False)
                # polygon.set_points([
                #     glm.vec2(0.0, 0.0),
                #     glm.vec2(1.0, 1.0)
                # ])
                # polygon.draw(glm.vec2(x0, y0), glm.vec2(width, height), 0.0, glm.vec3(0.5, 0.5, 0.5), False)

'''

class Viewer(basis.Entity):
    def __init__(self):
        super().__init__()
        pygame.init()
        pygame.display.set_caption('Cells')
        self.board = None
        size = width, height = 640, 480
        self.bk_color = (0, 0, 0)
        self.point_color = (100, 100, 100)
        self.info_color = (255, 255, 100)
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.background_surface = None
        self.show_grid = True
        self.show_net_view = True
        self.delay = 0.5
        self.clock = pygame.time.Clock()
        self.toggle_grid_button = None
        self.recreate_ui()

        # pgu initialization
        self.pgu_app = gui.App()
        gen_ctrl = GeneralControl()
        self.container = gui.Container(align=1, valign=-1)
        self.container.add(gen_ctrl, 0, 0)

        gen_ctrl.grid_btn.connect(gui.CLICK, self.toggle_grid)
        gen_ctrl.net_view_button.connect(gui.CLICK, self.toggle_net_view)
        gen_ctrl.info_view_button.connect(gui.CLICK, self.toggle_info_view)

        self.net_view = None
        self.info_view = None

        self.pgu_app.init(self.container)

    def recreate_ui(self):
        self.background_surface = pygame.Surface(self.screen.get_size()).convert()
        self.background_surface.fill(self.bk_color)

    def set_board(self, board):
        self.board = board

    def toggle_grid(self):
        self.show_grid = not self.show_grid

    def toggle_net_view(self):
        if self.net_view:
            self.container.remove(self.net_view)
            self.net_view = None
        else:
            self.net_view = NetView(width=320, height=240)
            self.container.add(self.net_view, 200, 200)
        self.container.repaint()

    def toggle_info_view(self):
        if self.info_view:
            self.container.remove(self.info_view)
            self.info_view = None
        else:
            self.info_view = InfoView(width=320, height=240)
            self.container.add(self.info_view, 200, 500)
        self.container.repaint()

    def step(self):
        time_delta = self.clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.VIDEORESIZE:
                print("new size {}x{}".format(event.w, event.h))
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                self.recreate_ui()
            if event.type == pygame.USEREVENT:
                pass
            else:
                self.pgu_app.event(event)

        self.screen.blit(self.background_surface, (0, 0))

        actual_size = pygame.display.get_window_size()

        # draw the board
        if self.board:
            board_size = min(actual_size[0], actual_size[1])
            scaled_cell_size = board_size / self.board.size

            self.board.draw()
            scaled_visual_field = pygame.transform.scale(self.board.visual_field, (board_size, board_size))
            self.screen.blit(scaled_visual_field, (0, 0))

            # self.screen.blit(self.board.compressed_visual_field, (board_size, 0))

            if self.show_grid:
                y = scaled_cell_size / 2.0
                for row in range(self.board.size):
                    x = scaled_cell_size / 2.0
                    for col in range(self.board.size):
                        point_rect = pygame.Rect(x, y, 1, 1)
                        pygame.draw.rect(self.screen, self.point_color, point_rect)
                        x += scaled_cell_size
                    y += scaled_cell_size

            agent = None
            if len(self.board.agents) > 0:
                agent = self.board.agents[0]
            if agent:
                p1 = (agent.position[0] * scaled_cell_size + scaled_cell_size / 2.0,
                      agent.position[1] * scaled_cell_size + scaled_cell_size / 2.0)
                p2 = (p1[0] + agent.orientation[0] * scaled_cell_size,
                      p1[1] + agent.orientation[1] * scaled_cell_size)
                pygame.draw.line(self.screen, self.info_color, p1, p2, 1)

        self.pgu_app.paint()
        pygame.display.update()
'''


class Shader:
    def __init__(self):
        self.shader_program = None

    def compile(self, vertex_source, fragment_source, geometry_source=""):
        vertex_shader = gl.glCreateShader(gl.GL_VERTEX_SHADER)
        gl.glShaderSource(vertex_shader, vertex_source)
        gl.glCompileShader(vertex_shader)
        compile_status = gl.glGetShaderiv(vertex_shader, gl.GL_COMPILE_STATUS)
        if not compile_status:
            print("Vertex shader compilation failed")

        fragment_shader = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)
        gl.glShaderSource(fragment_shader, fragment_source)
        gl.glCompileShader(fragment_shader)
        compile_status = gl.glGetShaderiv(fragment_shader, gl.GL_COMPILE_STATUS)
        if not compile_status:
            print("Fragment shader compilation failed")

        geometry_shader = None
        if geometry_source:
            geometry_shader = gl.glCreateShader(gl.GL_GEOMETRY_SHADER)
            gl.glShaderSource(geometry_shader, geometry_source)
            gl.glCompileShader(geometry_shader)
            compile_status = gl.glGetShaderiv(vertex_shader, gl.GL_COMPILE_STATUS)
            if not compile_status:
                print("Geometry shader compilation failed")

        self.shader_program = gl.glCreateProgram()
        gl.glAttachShader(self.shader_program, vertex_shader)
        gl.glAttachShader(self.shader_program, fragment_shader)
        if geometry_shader:
            gl.glAttachShader(self.shader_program, geometry_shader)
        gl.glLinkProgram(self.shader_program)
        link_status = gl.glGetProgramiv(self.shader_program, gl.GL_LINK_STATUS)
        if not link_status:
            print("Shader linking failed")

        gl.glDeleteShader(vertex_shader)
        gl.glDeleteShader(fragment_shader)
        if geometry_shader:
            gl.glDeleteShader(geometry_shader)

    def use(self):
        gl.glUseProgram(self.shader_program)

    def set_float(self, name, value, use_shader=False):
        if use_shader:
            self.use()
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, name), value)

    def set_integer(self, name, value, use_shader=False):
        if use_shader:
            self.use()
        gl.glUniform1i(gl.glGetUniformLocation(self.shader_program, name), value)

    def set_vector2f(self, name, x, y, use_shader=False):
        if use_shader:
            self.use()
        gl.glUniform2f(gl.glGetUniformLocation(self.shader_program, name), x, y)

    def set_vector3f(self, name, vector, use_shader=False):
        if use_shader:
            self.use()
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, name), vector.x, vector.y, vector.z)

    def set_vector4f(self, name, vector, use_shader=False):
        if use_shader:
            self.use()
        gl.glUniform4f(gl.glGetUniformLocation(self.shader_program, name), vector.x, vector.y, vector.z, vector.w)

    def set_matrix4(self, name, matrix, use_shader=False):
        if use_shader:
            self.use()
        gl.glUniformMatrix4fv(gl.glGetUniformLocation(self.shader_program, name), 1, False, glm.value_ptr(matrix))


class Texture:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.id = gl.glGenTextures(1)
        self.internal_format = gl.GL_RGB
        self.image_format = gl.GL_RGB
        self.wrap_s = gl.GL_REPEAT
        self.wrap_t = gl.GL_REPEAT
        self.filter_min = gl.GL_NEAREST_MIPMAP_LINEAR #.GL_LINEAR
        self.filter_max = gl.GL_LINEAR

    def generate(self, width, height, data):
        self.width = width
        self.height = height
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.id)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, self.internal_format, width, height, 0, self.image_format,
                        gl.GL_UNSIGNED_BYTE, data)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, self.wrap_s)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, self.wrap_t)
        gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, self.filter_min)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, self.filter_max)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def bind(self):
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.id)


class ResourceManager(basis.Entity):
    def __init__(self):
        super().__init__()
        self.shaders = dict()
        self.textures = dict()
        self.resource_dir = "res"

    def set_resource_dir(self, dir_name):
        self.resource_dir = dir_name

    def load_shader(self, shader_name, v_shader_file, f_shader_file, g_shader_file=None):
        v_shader_code = ""
        f_shader_code = ""
        g_shader_code = ""

        v_shader_path = "{}/{}".format(self.resource_dir, v_shader_file)
        f_shader_path = "{}/{}".format(self.resource_dir, f_shader_file)
        g_shader_path = None
        if g_shader_file:
            g_shader_path = "{}/{}".format(self.resource_dir, g_shader_file)

        with open(v_shader_path) as f:
            v_shader_code = f.read()
        with open(f_shader_path) as f:
            f_shader_code = f.read()
        if g_shader_path:
            with open(g_shader_path) as f:
                g_shader_code = f.read()

        shader = Shader()
        shader.compile(v_shader_code, f_shader_code, g_shader_code)

        self.shaders[shader_name] = shader
        return self.shaders[shader_name]

    def load_texture(self, texture_file, alpha, texture_name):
        texture = Texture()
        if alpha:
            texture.internal_format = gl.GL_RGBA
            texture.image_format = gl.GL_RGBA

        texture_path = "{}/{}".format(self.resource_dir, texture_file)

        image = Image.open(texture_path)
        data = asarray(image)
        texture.generate(data.shape[1], data.shape[0], data)  # Attention: in np.array height is the first param!

        self.textures[texture_name] = texture

        return texture

    def get_shader(self, shader_name):
        return self.shaders[shader_name]

    def get_texture(self, texture_name):
        return self.textures[texture_name]

    def clear(self):
        for k, v in self.shaders.items():
            gl.glDeleteProgram(v.id)
        for k, v in self.textures.items():
            gl.glDeleteTextures(1, v.id)


class SpriteRenderer:
    def __init__(self, shader):
        self.vao = None
        self.shader = shader
        self.init_render_data()

    def init_render_data(self):
        vertices = [
            # 1st triangle
            # pos     tex
            0.0, 1.0, 0.0, 1.0,
            1.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 0.0,
            # 2nd triangle
            # pos     tex
            0.0, 1.0, 0.0, 1.0,
            1.0, 1.0, 1.0, 1.0,
            1.0, 0.0, 1.0, 0.0
        ]

        self.vao = gl.glGenVertexArrays(1)
        vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, len(vertices) * 4, (gl.GLfloat * len(vertices))(*vertices),
                        gl.GL_STATIC_DRAW)
        gl.glBindVertexArray(self.vao)

        gl.glVertexAttribPointer(0, 4, gl.GL_FLOAT, gl.GL_FALSE, 16, None)
        gl.glEnableVertexAttribArray(0)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindVertexArray(0)

    def draw_sprite(self, texture, position, size, rotate, color):
        model = glm.mat4(1.0)
        model = glm.translate(model, glm.vec3(position, 0.0))
        model = glm.translate(model, glm.vec3(0.5 * size[0], 0.5 * size[1], 0.0))
        model = glm.rotate(model, glm.radians(rotate), glm.vec3(0.0, 0.0, 1.0))
        model = glm.translate(model, glm.vec3(-0.5 * size[0], -0.5 * size[1], 0.0))
        model = glm.scale(model, glm.vec3(size, 1.0))

        self.shader.use()
        self.shader.set_matrix4("model", model)
        self.shader.set_vector3f("spriteColor", color)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        texture.bind()

        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)
        gl.glBindVertexArray(0)


class Polygon:
    def __init__(self, shader):
        self.vao = None
        self.shader = shader
        self.vertices = list()
        self.vertex_count = 0

    def set_points(self, points):
        """points must be an array of glm.vec2 objects"""
        self.vertex_count = len(points)
        self.vertices.clear()
        for p in points:
            self.vertices.append(p.x)
            self.vertices.append(p.y)

        self.vao = gl.glGenVertexArrays(1)
        vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, len(self.vertices) * 4, (gl.GLfloat * len(self.vertices))(*self.vertices),
                        gl.GL_STATIC_DRAW)
        gl.glBindVertexArray(self.vao)

        gl.glVertexAttribPointer(0, 2, gl.GL_FLOAT, gl.GL_FALSE, 8, None)
        gl.glEnableVertexAttribArray(0)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindVertexArray(0)

    def draw(self, position, size, rotate, color, filled):
        model = glm.mat4(1.0)
        model = glm.translate(model, glm.vec3(position, 0.0))
        model = glm.translate(model, glm.vec3(0.5 * size[0], 0.5 * size[1], 0.0))
        model = glm.rotate(model, glm.radians(rotate), glm.vec3(0.0, 0.0, 1.0))
        model = glm.translate(model, glm.vec3(-0.5 * size[0], -0.5 * size[1], 0.0))
        model = glm.scale(model, glm.vec3(size, 1.0))

        self.shader.use()
        self.shader.set_matrix4("model", model)
        self.shader.set_vector3f("polygonColor", color)

        gl.glBindVertexArray(self.vao)
        if filled:
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, self.vertex_count)
        else:
            gl.glDrawArrays(gl.GL_LINE_STRIP, 0, self.vertex_count)
        #gl.glDrawArrays(gl.GL_POINTS, 0, self.vertex_count)
        gl.glBindVertexArray(0)


class Viewer(basis.Entity):
    initial_win_size = (initial_win_width, initial_win_height) = (1024, 768)

    def __init__(self):
        super().__init__()
        self.window = init_glfw()
        imgui.create_context()
        self.render_engine = GlfwRenderer(self.window)
        glfw.set_window_size_callback(self.window, self.window_size_callback)

        glfw.make_context_current(self.window)

        self.win_width = Viewer.initial_win_width
        self.win_height = Viewer.initial_win_height
        resource_manager = self.system.find_entity_by_name("ResourceManager")
        resource_manager.load_shader("sprite", "sprite.vs", "sprite.fs")
        resource_manager.load_shader("polygon", "polygon.vs", "polygon.fs")

        self.renderer = None
        self.on_window_resize()

        # alpha blending (for transparency, semi-transparency, etc.)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.board = self.system.find_entity_by_name("Board")
        resource_manager.load_texture("background.png", False, "background")
        resource_manager.load_texture("agent.png", True, "agent")
        resource_manager.load_texture("obstacle.png", True, "obstacle")

    def on_window_resize(self):
        glfw.make_context_current(self.window)
        
        gl.glViewport(0, 0, self.win_width, self.win_height)
        projection = glm.ortho(0.0, self.win_width, self.win_height, 0.0)
        resource_manager = self.system.find_entity_by_name("ResourceManager")

        sprite_shader = resource_manager.get_shader("sprite")
        sprite_shader.use()
        sprite_shader.set_integer("image", 0)
        sprite_shader.set_matrix4("projection", projection)
        self.renderer = SpriteRenderer(sprite_shader)

        poly_shader = resource_manager.get_shader("polygon")
        poly_shader.use()
        poly_shader.set_matrix4("projection", projection)

    def draw_info_window(self):
        imgui.begin("Info")
        imgui.text("Some text")
        imgui.end()

    '''
    def draw_board(self):
        imgui.begin("Board")

        imgui.text("Some other text")

        draw_list = imgui.get_window_draw_list()
        wx, wy = imgui.get_window_position()
        draw_list.add_circle(wx + 100, wy + 60, 30, imgui.get_color_u32_rgba(1, 1, 0, 1), thickness=1)

        imgui.end()
    '''

    def window_size_callback(self, window, width, height):
        self.win_width = width
        self.win_height = height
        self.on_window_resize()

    def step(self):
        glfw.make_context_current(self.window)

        glfw.poll_events()
        glfw.set_window_title(self.window, "Cells")
        glfw.set_window_size(self.window, self.win_width, self.win_height)

        if glfw.window_should_close(self.window):
            self.system.shutdown()

        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        self.render_engine.process_inputs()

        imgui.new_frame()

        self.draw_info_window()

        if self.board:
            board_image_size = min(self.win_width, self.win_height)
            board_pos_x = (self.win_width - board_image_size) / 2.0
            board_pos_y = (self.win_height - board_image_size) / 2.0
            self.board.draw(self.renderer,
                            (board_pos_x, board_pos_y),
                            (board_image_size, board_image_size)
                            )
        #self.draw_board()

        imgui.render()
        self.render_engine.render(imgui.get_draw_data())
        glfw.swap_buffers(self.window)


class NetViewer(basis.Entity):
    initial_win_size = (initial_win_width, initial_win_height) = (800, 600)

    def __init__(self):
        super().__init__()
        self.window = init_glfw()
        self.render_engine = GlfwRenderer(self.window)
        glfw.set_window_size_callback(self.window, self.window_size_callback)

        glfw.make_context_current(self.window)

        self.win_width = NetViewer.initial_win_width
        self.win_height = NetViewer.initial_win_height

        self.renderer = None
        self.on_window_resize()

        # alpha blending (for transparency, semi-transparency, etc.)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    def on_window_resize(self):
        pass

    def window_size_callback(self, window, width, height):
        self.win_width = width
        self.win_height = height
        self.on_window_resize()

    def step(self):
        glfw.make_context_current(self.window)

        glfw.poll_events()
        glfw.set_window_title(self.window, "Net")
        glfw.set_window_size(self.window, self.win_width, self.win_height)

        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        self.render_engine.process_inputs()

        glfw.swap_buffers(self.window)


def init_glfw():
    # Initialize the GLFW library
    if not glfw.init():
        return

    # OpenGL 3 or above is required
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.RESIZABLE, True)
    # OpenGL context should be forward-compatible
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)

    # Create a window in windowed mode and it's OpenGL context
    primary = glfw.get_primary_monitor()  # for GLFWmonitor
    window = glfw.create_window(
        Viewer.initial_win_width,  # width, is required here but overwritten by "glfw.set_window_size()" above
        Viewer.initial_win_height,  # height, is required here but overwritten by "glfw.set_window_size()" above
        "pyimgui-examples-glfw",  # window name, is overwritten by "glfw.set_window_title()" above
        None,  # GLFWmonitor: None = windowed mode, 'primary' to choose fullscreen (resolution needs to be adjusted)
        None  # GLFWwindow
    )

    # Exception handler if window wasn't created
    if not window:
        glfw.terminate()
        return

    # Makes window current on the calling thread
    glfw.make_context_current(window)

    # Passing window to main()
    return window


def unit_test():
    a1 = angle(glm.vec2(1.0, 0.0), glm.vec2(0.0, 1.0))
    a2 = angle(glm.vec2(1.0, 0.0), glm.vec2(-1.0, 0.0))
    a3 = angle(glm.vec2(1.0, 0.0), glm.vec2(0.0, -1.0))

    return True


if __name__ == "__main__":
    res = unit_test()
    if res:
        print("cells.py: test ok")
    else:
        print("cells.py: test FAILED")


