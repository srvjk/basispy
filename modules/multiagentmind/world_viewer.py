import basis
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glm
import graphics_opengl as gogl
import cells


class WorldViewer(basis.Entity):
    initial_win_size = (initial_win_width, initial_win_height) = (1024, 768)

    def __init__(self, system):
        super().__init__(system)
        self.may_be_paused = False
        self.window = init_glfw()
        imgui.create_context()
        self.render_engine = GlfwRenderer(self.window)
        glfw.set_window_size_callback(self.window, self.window_size_callback)

        glfw.make_context_current(self.window)

        self.win_width = WorldViewer.initial_win_width
        self.win_height = WorldViewer.initial_win_height
        gogl.resource_manager.load_shader("sprite", "sprite.vs", "sprite.fs")
        gogl.resource_manager.load_shader("polygon", "polygon.vs", "polygon.fs")
        gogl.resource_manager.load_shader("freetypetext", "freetypetext.vs", "freetypetext.fs")

        self.renderer = None
        self.text_renderer = None
        self.on_window_resize()

        # alpha blending (for transparency, semi-transparency, etc.)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.board = self.system.get_entity_by_name("Board")
        gogl.resource_manager.load_texture("background.png", False, "background")
        gogl.resource_manager.load_texture("agent.png", True, "agent")
        gogl.resource_manager.load_texture("obstacle.png", True, "obstacle")

        self.agent = None
        self.agent_id = None

    def on_window_resize(self):
        glfw.make_context_current(self.window)

        gl.glViewport(0, 0, self.win_width, self.win_height)

        sprite_shader = gogl.resource_manager.get_shader("sprite")
        sprite_shader.use()
        sprite_shader.set_integer("image", 0)
        projection = glm.ortho(0.0, self.win_width, self.win_height, 0.0)
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
        projection = glm.ortho(0.0, self.win_width, self.win_height, 0.0)
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
            imgui.text("Agent pos.: ({}, {})".format(int(self.agent.position.x), int(self.agent.position.y)))
            imgui.text("Agent ort.: ({}, {})".format(int(self.agent.orientation.x), int(self.agent.orientation.y)))
            imgui.text("Short memory: {} items".format(self.agent.short_memory.size()))

            imgui.text_colored("Current frame:", 1.0, 1.0, 0.0)
            if self.agent.current_frame:
                self.display_frame(self.agent.current_frame)

            imgui.text_colored("Last frame:", 0.0, 1.0, 1.0)
            last_frame = self.agent.short_memory.most_recent_frame()
            if last_frame:
                self.display_frame(last_frame)
        else:
            imgui.text("No agents found!")

        imgui.end()

    def draw_entities_window(self):
        imgui.begin("Entities")

        imgui.text("Entities total: {}".format(len(self.system.entity_uuid_index)))

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
            imgui.selectable(str(k)[:5] + '...', False, imgui.SELECTABLE_SPAN_ALL_COLUMNS)
            imgui.next_column()
            name = v.name if v.name else "-"
            imgui.text(name)
            imgui.next_column()
            imgui.text(str(v.get_local_step_counter()))
            imgui.next_column()

        imgui.end()

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
        self.draw_entities_window()
        self.draw_control_window()

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
        WorldViewer.initial_win_width,  # width, is required here but overwritten by "glfw.set_window_size()" above
        WorldViewer.initial_win_height,  # height, is required here but overwritten by "glfw.set_window_size()" above
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
