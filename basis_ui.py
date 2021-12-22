import basis
import glfw
import OpenGL.GL as gl
import imgui
from imgui.integrations.glfw import GlfwRenderer

def normalize_color(r : float, g : float, b : float):
    x = 1.5 / (r + g + b)

    r *= x
    g *= x
    b *= x

    return r, g, b

def make_color_dim(r : float, g : float, b : float, factor=0.3):
    r, g, b = normalize_color(r, g, b)

    r *= factor
    g *= factor
    b *= factor

    return r, g, b

def make_color_bright(r : float, g : float, b : float, factor=1.3):
    r, g, b = normalize_color(r, g, b)

    max_val = max(r, g, b)
    ratio = min(1.0 / max_val, factor)

    r *= ratio
    g *= ratio
    b *= ratio

    return r, g, b


class GuiHelper(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        glfw.init()

    def step(self):
        pass


class EntityObserver:
    def __init__(self):
        pass

    def draw_entity(self, entity):
        text = "{} : {}".format(entity.uuid, entity.name)
        is_open = imgui.tree_node(text)
        imgui.next_column()
        if hasattr(entity, 'selected'):
            button_text = "[ ]"
            if entity.selected:
                button_text = "[*]"
            if imgui.button(button_text):
                entity.selected = not entity.selected
        imgui.next_column()
        if is_open:
            for child in entity.entities:
                self.draw_entity(child)
            imgui.tree_pop()

    def draw(self, root_entity):
        imgui.columns(2, "tree", True)

        self.draw_entity(root_entity)


class ControlPanel(basis.Entity):
    initial_win_size = (initial_win_width, initial_win_height) = (1024, 768)

    def __init__(self, system):
        super().__init__(system)
        self.imgui_context = imgui.create_context()
        imgui.set_current_context(self.imgui_context)
        self.window = create_glfw_window()
        self.render_engine = GlfwRenderer(self.window)
        io = imgui.get_io()
        io.fonts.add_font_default()

        glfw.set_window_size_callback(self.window, self.window_size_callback)

        glfw.make_context_current(self.window)

        self.win_width = ControlPanel.initial_win_width
        self.win_height = ControlPanel.initial_win_height

        self.renderer = None
        self.on_window_resize()

        self.entity_observer = EntityObserver()

    def on_window_resize(self):
        pass

    def window_size_callback(self, window, width, height):
        self.win_width = width
        self.win_height = height
        self.on_window_resize()

    def step(self):
        glfw.make_context_current(self.window)
        imgui.set_current_context(self.imgui_context)
        glfw.poll_events()

        glfw.set_window_title(self.window, "Basis Control Panel")
        glfw.set_window_size(self.window, self.win_width, self.win_height)

        if glfw.window_should_close(self.window):
            self.system.shutdown()

        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        imgui.new_frame()

        self.entity_observer.draw(self.system)

        imgui.render()
        self.render_engine.render(imgui.get_draw_data())
        glfw.swap_buffers(self.window)
        self.render_engine.process_inputs()


def create_glfw_window(win_width=800, win_height=600):
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
        win_width,  # width, is required here but overwritten by "glfw.set_window_size()" above
        win_height,  # height, is required here but overwritten by "glfw.set_window_size()" above
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
