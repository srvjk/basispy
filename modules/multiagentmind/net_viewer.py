import basis
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl
import glm
import graphics_opengl as gogl
import cells
import configparser


class NetViewer(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.config = None
        self.config_file_name = 'multiagentmind.ini'
        self.win_x = 10
        self.win_y = 10
        self.win_width = 1024
        self.win_height = 768
        self.win_maximized = 0
        self.read_config()
        self.may_be_paused = False
        self.window = self.init_glfw()
        glfw.set_window_size_callback(self.window, self.window_size_callback)
        glfw.set_window_pos_callback(self.window, self.window_pos_callback)
        glfw.set_window_maximize_callback(self.window, self.window_maximize_callback)

        glfw.make_context_current(self.window)

        self.renderer = None
        self.text_renderer = None
        self.on_window_resize()

        glfw.set_window_pos(self.window, self.win_x, self.win_y)
        if self.win_maximized:
            glfw.maximize_window(self.window)

        # alpha blending (for transparency, semi-transparency, etc.)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.agent = None
        self.agent_id = None

    def read_config(self):
        self.config = configparser.ConfigParser()
        if not self.config.read(self.config_file_name):
            return

        try:
            self.win_width = int(self.config['window']['width'])
            self.win_height = int(self.config['window']['height'])
            self.win_x = int(self.config['window']['x'])
            self.win_y = int(self.config['window']['y'])
            self.win_maximized = int(self.config['window']['maximized'])
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
        self.config['window']['maximized'] = str(self.win_maximized)
        try:
            with open(self.config_file_name, mode='w+t') as fp:
                self.config.write(fp)
        except OSError:
            return

    def on_window_resize(self):
        glfw.make_context_current(self.window)

        gl.glViewport(0, 0, self.win_width, self.win_height)

    def window_size_callback(self, window, width, height):
        self.win_width = width
        self.win_height = height
        self.on_window_resize()

    def window_pos_callback(self, window, x, y):
        self.win_x = x
        self.win_y = y

    def window_maximize_callback(self, window, maximized):
        self.win_maximized = maximized

    def draw_memory(self, memory, pos, size):
        x0 = pos[0]
        y0 = pos[1]
        width = size[0]
        height = size[1]

    def step(self):
        if not self.agent:
            if self.agent_id:
                self.agent = self.system.get_entity_by_id(self.agent_id)
            else:
                self.agent = basis.first_of(self.system.get_entities_by_type_recursively(cells.Agent))

        glfw.make_context_current(self.window)

        glfw.poll_events()
        glfw.set_window_title(self.window, "Cells")
        glfw.set_window_size(self.window, self.win_width, self.win_height)

        if glfw.window_should_close(self.window):
            self.write_config()
            self.system.shutdown()

        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        self.draw_memory(self.agent.memory, (0, 0), (self.win_width, self.win_height))

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
