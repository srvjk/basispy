import basis
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glm
import graphics_opengl as gogl
import cells
import logging
import configparser


class WorldLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.message_buffer = []

    def emit(self, record):
        try:
            msg = self.format(record)
            self.message_buffer.append(msg)
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)


class WorldViewer(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.config = None
        self.config_file_name = 'multiagentmind.ini'
        self.win_x = 10
        self.win_y = 10
        self.win_width = 1024
        self.win_height = 768
        self.read_config()
        self.may_be_paused = False
        self.window = self.init_glfw()
        imgui.create_context()
        self.render_engine = GlfwRenderer(self.window)
        glfw.set_window_size_callback(self.window, self.window_size_callback)
        glfw.set_window_pos_callback(self.window, self.window_pos_callback)

        glfw.make_context_current(self.window)

        gogl.resource_manager.load_shader("sprite", "sprite.vs", "sprite.fs")
        gogl.resource_manager.load_shader("polygon", "polygon.vs", "polygon.fs")
        gogl.resource_manager.load_shader("freetypetext", "freetypetext.vs", "freetypetext.fs")

        self.renderer = None
        self.text_renderer = None
        self.on_window_resize()

        glfw.set_window_pos(self.window, self.win_x, self.win_y)

        # alpha blending (for transparency, semi-transparency, etc.)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.board = self.system.get_entity_by_name("Board")
        gogl.resource_manager.load_texture("background.png", False, "background")
        gogl.resource_manager.load_texture("agent.png", True, "agent")
        gogl.resource_manager.load_texture("obstacle.png", True, "obstacle")

        self.agent = None
        self.agent_id = None

        self.log_handler = WorldLogHandler()

        # ссылки на логгеры (нужны только для того, чтобы не запрашивать логгеры каждый раз при отрисовке окна):
        self.multiagentmind_logger = None  # "локальный" логгер для этого модуля
        self.system_logger = None          # системный логгер

    def read_config(self):
        self.config = configparser.ConfigParser()
        if not self.config.read(self.config_file_name):
            return

        try:
            self.win_width = int(self.config['window']['width'])
            self.win_height = int(self.config['window']['height'])
            self.win_x = int(self.config['window']['x'])
            self.win_y = int(self.config['window']['y'])
        except KeyError:
            pass  # поскольку все поля имеют значения по умолчанию

        self.check_config()

    def check_config(self):
        if self.win_width < 100:
            self.win_width = 100
        if self.win_height < 100:
            self.win_height = 100

    def write_config(self):
        self.config['window']['width'] = str(self.win_width)
        self.config['window']['height'] = str(self.win_height)
        self.config['window']['x'] = str(self.win_x)
        self.config['window']['y'] = str(self.win_y)
        try:
            with open(self.config_file_name, mode='w+t') as fp:
                self.config.write(fp)
        except OSError:
            return

    def on_window_resize(self):
        glfw.make_context_current(self.window)

        gl.glViewport(0, 0, self.win_width, self.win_height)

        sprite_shader = gogl.resource_manager.get_shader("sprite")
        sprite_shader.use()
        sprite_shader.set_integer("image", 0)
        #projection = glm.ortho(0.0, self.win_width, self.win_height, 0.0)
        projection = glm.ortho(0.0, self.win_width, 0.0, self.win_height)
        sprite_shader.set_matrix4("projection", projection)
        self.renderer = gogl.SpriteRenderer(sprite_shader)

        text_shader = gogl.resource_manager.get_shader("freetypetext")
        text_shader.use()
        text_shader.set_integer("text", 0)
        projection = glm.ortho(0.0, self.win_width, 0.0, self.win_height)
        text_shader.set_matrix4("projection", projection)
        self.text_renderer = gogl.TextRenderer(text_shader)
        self.text_renderer.make_face("res/TerminusTTFWindows-4.46.0.ttf")

        poly_shader = gogl.resource_manager.get_shader("polygon")
        poly_shader.use()
        #projection = glm.ortho(0.0, self.win_width, self.win_height, 0.0)
        projection = glm.ortho(0.0, self.win_width, 0.0, self.win_height)
        poly_shader.set_matrix4("projection", projection)

    def display_frame(self, frame):
        """
        Отобразить информацию по одному временнОму кадру
        :return:
        """
        for ent in frame.entities:
            name = ent.name if ent.name else 'noname'
            text = "{} ({}, {})".format(str(ent.uuid), basis.qual_class_name(ent), name)
            imgui.text(text)

    def draw_control_window(self):
        imgui.begin("Control")

        imgui.text("Step {}".format(self.system.get_global_step_counter()))

        if self.system.timing_mode == basis.TimingMode.UnrealTime:
            imgui.text("Non-real time mode")
        elif self.system.timing_mode == basis.TimingMode.RealTime:
            imgui.text("Real time mode")

        imgui.text("Model time {:.3f} s (speed = {:.2f})".format(
            self.system.model_time_s(),
            self.system.model_time_speed
        ))
        imgui.same_line()
        if imgui.button("Faster"):
            self.system.model_time_speed *= 1.5
        imgui.same_line()
        if imgui.button("Slower"):
            self.system.model_time_speed /= 1.5
        imgui.same_line()
        if imgui.button("1 : 1"):
            self.system.model_time_speed = 1.0

        pause_button_text = "Resume" if self.system.pause else "Pause"
        if imgui.button(pause_button_text):
            self.system.pause = not self.system.pause
        imgui.same_line()
        if imgui.button(">"):
            self.system.do_single_step = True

        imgui.text("System steps: {}".format(self.system.get_global_step_counter()))
        imgui.text("System fps: {:.2f}".format(self.system.get_fps()))

        imgui.end()

    def draw_info_window(self):
        imgui.begin("Info")

        imgui.text("Step {}".format(self.system.get_global_step_counter()))

        if not self.agent:
            if self.agent_id:
                self.agent = self.system.get_entity_by_id(self.agent_id)
            else:
                self.agent = basis.first_of(self.system.get_entities_by_type_recursively(cells.Agent))

        if self.agent:
            imgui.text("Agent found")
            xr = round(self.agent.position.x)
            imgui.text("Agent pos.: ({}, {})".format(self.agent.position.x, self.agent.position.y))
            imgui.text("Agent ort.: ({}, {})".format(self.agent.orientation.x, self.agent.orientation.y))
            imgui.text("Short memory: {} items".format(self.agent.short_memory.size()))

            imgui.text_colored("Current frame:", 1.0, 1.0, 0.0)
            if self.agent.current_frame:
                self.display_frame(self.agent.current_frame)

            imgui.text_colored("Last frame:", 0.0, 1.0, 1.0)
            last_frame = self.agent.short_memory.most_recent_frame()
            if last_frame:
                self.display_frame(last_frame)

            if self.agent.message:
                imgui.text(self.agent.message)
        else:
            imgui.text("No agents found!")

        imgui.end()

    def draw_entities_window(self):
        imgui.begin("Entities")

        imgui.text("Entities total: {}".format(len(self.system.entity_uuid_index)))
        imgui.new_line()

        imgui.text("Entities by type:")
        imgui.new_line()
        for k, v in self.system.statistics.counter_by_type.items():
            imgui.text("{} : {}".format(k, v))

        imgui.new_line()

        imgui.text("Named entities:")

        imgui.columns(3)
        imgui.separator()
        imgui.text("ID")
        imgui.next_column()
        imgui.text("Name")
        imgui.next_column()
        imgui.text("Step")
        imgui.next_column()
        imgui.separator()

        for k, v in self.system.entity_uuid_index.items():
            if not v.name:
                continue
            imgui.selectable(str(k)[:5] + '...', False, imgui.SELECTABLE_SPAN_ALL_COLUMNS)
            imgui.next_column()
            name = v.name if v.name else "-"
            imgui.text(name)
            imgui.next_column()
            imgui.text(str(v.get_local_step_counter()))
            imgui.next_column()

        imgui.end()

    def draw_log_window(self):
        if not self.multiagentmind_logger:
            self.multiagentmind_logger = logging.getLogger("multiagentmind")
            if self.multiagentmind_logger:
                self.multiagentmind_logger.addHandler(self.log_handler)
        if not self.system_logger:
            self.system_logger = logging.getLogger("system")
            if self.system_logger:
                self.system_logger.addHandler(self.log_handler)

        imgui.begin("Log", flags=imgui.WINDOW_NO_SCROLLBAR)

        imgui.begin_child("log_text", 0.0, -50.0, border=False)
        for item in self.log_handler.message_buffer:
            imgui.text(item)
            imgui.set_scroll_here(1.0)
        imgui.end_child()

        imgui.dummy(0, 50)

        n_max = 100
        list_len = len(self.log_handler.message_buffer)
        if  list_len > n_max:
            overfill = list_len - n_max
            del self.log_handler.message_buffer[:overfill]

        imgui.end()

    def window_size_callback(self, window, width, height):
        self.win_width = width
        self.win_height = height
        self.on_window_resize()

    def window_pos_callback(self, window, x, y):
        self.win_x = x
        self.win_y = y

    def step(self):
        glfw.make_context_current(self.window)

        glfw.poll_events()
        glfw.set_window_title(self.window, "Cells")
        glfw.set_window_size(self.window, self.win_width, self.win_height)

        if glfw.window_should_close(self.window):
            self.write_config()
            self.system.shutdown()

        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        self.render_engine.process_inputs()

        imgui.new_frame()

        self.draw_info_window()
        self.draw_entities_window()
        self.draw_control_window()
        self.draw_log_window()

        if self.board:
            board_image_size = min(self.win_width, self.win_height)
            board_pos_x = (self.win_width - board_image_size) / 2.0
            board_pos_y = (self.win_height - board_image_size) / 2.0
            self.board.draw(self.renderer,
                            (board_pos_x, board_pos_y),
                            (board_image_size, board_image_size)
                            )

        info_str = "Step {}".format(self.system.get_global_step_counter())
        self.text_renderer.draw_text(info_str, 20, 120, 0.5, glm.vec3(1.0, 0.0, 1.0))
        # self.draw_board()

        imgui.render()
        self.render_engine.render(imgui.get_draw_data())
        glfw.swap_buffers(self.window)

    def init_glfw(self):
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
            self.win_width,  # width, is required here but overwritten by "glfw.set_window_size()" above
            self.win_height,  # height, is required here but overwritten by "glfw.set_window_size()" above
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
