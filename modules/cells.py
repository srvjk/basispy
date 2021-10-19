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
        self._position = [0, 0]

    @property
    def position(self):
        return self._position

    def set_position(self, x, y):
        self._position = [x, y]


class Agent(basis.Entity):
    def __init__(self):
        super().__init__()
        self.board = None
        self._position = [0, 0]
        self._orientation = [1, 0]

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

    @property
    def position(self):
        return self._position

    @property
    def orientation(self):
        return self._orientation

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
            self.position[0] += self.orientation[0]
            self.position[1] += self.orientation[1]
            self.position[0] = max(0, self.position[0])
            self.position[0] = min(self.position[0], self.board.size - 1)
            self.position[1] = max(0, self.position[1])
            self.position[1] = min(self.position[1], self.board.size - 1)
        if choice == AgentAction.TurnLeft:
            dir_x, dir_y = self._orientation
            self.orientation[0] = dir_y
            self.orientation[1] = -dir_x
        if choice == AgentAction.TurnRight:
            dir_x, dir_y = self._orientation
            self.orientation[0] = -dir_y
            self.orientation[1] = dir_x


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
            obstacle.set_position(x, y)
            self.obstacles.append(obstacle)

    def get_cell_color(self, x, y):
        if x < 0 or x >= self.size or y < 0 or y >= self.size:
            return self.color_no_color
        return self.compressed_visual_field.get_at((x, y))

    def draw(self, renderer):
        resource_manager = self.system.find_entity_by_name("ResourceManager")
        renderer.draw_sprite(resource_manager.get_texture("background"), glm.vec2(0.0, 0.0),
                             glm.vec2(self.size_in_pixels(), self.size_in_pixels()), 0.0, glm.vec3(1.0))

        for obstacle in self.obstacles:
            if isinstance(obstacle, Obstacle):
                try:
                    renderer.draw_sprite(resource_manager.get_texture("obstacle"),
                                         glm.vec2(obstacle.position[0] * self.cell_size,
                                                  obstacle.position[1] * self.cell_size),
                                         glm.vec2(self.cell_size, self.cell_size), 0.0, glm.vec3(1.0))
                except AttributeError:
                    pass

        for agent in self.agents:
            if isinstance(agent, Agent):
                try:
                    renderer.draw_sprite(resource_manager.get_texture("agent"),
                                         glm.vec2(agent.position[0] * self.cell_size,
                                                  agent.position[1] * self.cell_size),
                                         glm.vec2(self.cell_size, self.cell_size), 0.0, glm.vec3(1.0))
                except AttributeError:
                    pass

        # после всей отрисовки создаём вспомогательное сжатое представление доски:
        #pygame.transform.scale(self.visual_field, (self.size, self.size), self.compressed_visual_field)

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

    def set_float(self, name, value, use_shader = False):
        if use_shader:
            self.use()
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, name), value)

    def set_integer(self, name, value, use_shader = False):
        if use_shader:
            self.use()
        gl.glUniform1i(gl.glGetUniformLocation(self.shader_program, name), value)

    def set_vector2f(self, name, x, y, use_shader = False):
        if use_shader:
            self.use()
        gl.glUniform2f(gl.glGetUniformLocation(self.shader_program, name), x, y)

    def set_vector3f(self, name, vector, use_shader = False):
        if use_shader:
            self.use()
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, name), vector.x, vector.y, vector.z)

    def set_vector4f(self, name, vector, use_shader = False):
        if use_shader:
            self.use()
        gl.glUniform4f(gl.glGetUniformLocation(self.shader_program, name), vector.x, vector.y, vector.z, vector.w)

    def set_matrix4(self, name, matrix, use_shader = False):
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
        self.filter_min = gl.GL_LINEAR
        self.filter_max = gl.GL_LINEAR

    def generate(self, width, height, data):
        self.width = width
        self.height = height
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.id)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, self.internal_format, width, height, 0, self.image_format,
                        gl.GL_UNSIGNED_BYTE, data)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, self.wrap_s)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, self.wrap_t)
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

    def load_shader(self, shader_name, v_shader_file, f_shader_file, g_shader_file = None):
        v_shader_code = ""
        f_shader_code = ""
        g_shader_code = ""

        with open(v_shader_file) as f:
            v_shader_code = f.read()
        with open(f_shader_file) as f:
            f_shader_code = f.read()
        if g_shader_file:
            with open(g_shader_file) as f:
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

        image = Image.open(texture_file)
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

        gl.glVertexAttribPointer(0, 4, gl.GL_FLOAT, gl.GL_FALSE, 16, None) # MAY BE WRONG!
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

        self.shader.set_matrix4("model", model)
        self.shader.set_vector3f("spriteColor", color)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        texture.bind()

        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)
        gl.glBindVertexArray(0)


class Viewer(basis.Entity):
    def __init__(self):
        super().__init__()
        self.window = init_glfw()
        imgui.create_context()
        self.render_engine = GlfwRenderer(self.window)
        self.win_width = 1024
        self.win_height = 768
        resource_manager = self.system.find_entity_by_name("ResourceManager")
        resource_manager.load_shader("sprite", "modules/sprite.vs", "modules/sprite.frag")
        projection = glm.ortho(0.0, self.win_width, self.win_height, 0.0)
        shader = resource_manager.get_shader("sprite")
        shader.use()
        shader.set_integer("image", 0)
        shader.set_matrix4("projection", projection)
        self.renderer = SpriteRenderer(shader)
        self.board = self.system.find_entity_by_name("Board")
        resource_manager.load_texture("modules/background.jpg", False, "background")
        resource_manager.load_texture("modules/agent.png", True, "agent")
        resource_manager.load_texture("modules/obstacle.png", False, "obstacle")

    def draw_toolbar(self):
        imgui.begin("Toolbar")

        imgui.text("Some text")

        imgui.end()

    '''
    def draw_board(self):
        imgui.begin("Board")

        imgui.text("Some other text")

        draw_list = imgui.get_window_draw_list()
        draw_list.add_circle(100, 60, 30, imgui.get_color_u32_rgba(1, 1, 0, 1), thickness=1)
        draw_list.add_rect(20, 35, 90, 80, imgui.get_color_u32_rgba(1, 1, 0, 1), thickness=3)

        imgui.end()
    '''

    def step(self):
        glfw.poll_events()
        glfw.set_window_title(self.window, "Cells")
        glfw.set_window_size(self.window, self.win_width, self.win_height)

        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        self.render_engine.process_inputs()

        imgui.new_frame()

        self.draw_toolbar()
        if self.board:
            self.board.draw(self.renderer)
        #self.draw_board()

        imgui.render()
        self.render_engine.render(imgui.get_draw_data())
        glfw.swap_buffers(self.window)


def init_glfw():
    # Initialize the GLFW library
    if not glfw.init():
        return

    # OpenGL 3 or above is required
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    # OpenGL context should be forward-compatible
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)

    # Create a window in windowed mode and it's OpenGL context
    primary = glfw.get_primary_monitor()  # for GLFWmonitor
    window = glfw.create_window(
        1024,  # width, is required here but overwritten by "glfw.set_window_size()" above
        768,  # height, is required here but overwritten by "glfw.set_window_size()" above
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


