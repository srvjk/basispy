import basis
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl
import glm
import graphics_opengl as gogl
import cells
import config_helper


class NetViewer(basis.Entity):
    def __init__(self, system):
        super().__init__(system)

        self.config = None
        self.config_file_name = 'multiagentmind.ini'
        self.toml = config_helper.TOMLHelper("config.toml")
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
        self.render_engine = GlfwRenderer(self.window)

        self.resource_manager = gogl.ResourceManager()

        self.resource_manager.load_shader("sprite", "sprite.vs", "sprite.fs")
        self.resource_manager.load_shader("polygon", "polygon.vs", "polygon.fs")
        self.resource_manager.load_shader("freetypetext", "freetypetext.vs", "freetypetext.fs")

        self.renderer = None
        self.text_renderer = None
        self.on_window_resize()

        glfw.set_window_pos(self.window, self.win_x, self.win_y)
        if self.win_maximized:
            glfw.maximize_window(self.window)

        # alpha blending (for transparency, semi-transparency, etc.)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.color_neuron_inactive = glm.vec3(0.5, 0.5, 0.5)
        self.color_neuron_active = glm.vec3(0.9, 0.9, 0.9)

        self.resource_manager.load_texture("background.png", False, "background")
        self.resource_manager.load_texture("neuron_inactive.png", True, "neuron_inactive")
        self.resource_manager.load_texture("neuron_active.png", True, "neuron_active")

        self.lnk_arc = gogl.Arc(self.resource_manager.get_shader("polygon"), 1.0, 10)  # дуга для рисования связи
        self.neuron_circle = gogl.FilledCircle(self.resource_manager.get_shader("polygon"), 32)  # круг для нейрона
        # индикатор состояния входа нейрона:
        #self.neuron_input_indicator = gogl.Line(self.resource_manager.get_shader("polygon"))
        self.neuron_input_indicator = gogl.Polygon(self.resource_manager.get_shader("polygon"))
        self.neuron_input_indicator.set_points([
            glm.vec2(0.0, 0.0),
            glm.vec2(1.0, 0.0),
            glm.vec2(1.0, 1.0),
            glm.vec2(0.0, 1.0),
            glm.vec2(0.0, 0.0)
        ])

        self.agent = None
        self.agent_id = None

    def read_config(self):
        config = self.system.get_entity_by_name("ConfigHelper")
        if not config:
            return

        section_name = basis.short_class_name(self)  # название раздела конфигурации для этого окна

        net_viewer = config.data.get(section_name, None)
        if net_viewer:
            window = net_viewer.get('window', None)
            if window:
                self.win_width = window.get('width', self.win_width)
                self.win_height = window.get('height', self.win_height)
                self.win_x = window.get('x', self.win_x)
                self.win_y = window.get('y', self.win_y)
                self.win_maximized = window.get('maximized', self.win_maximized)

        self.check_config()

    def check_config(self):
        if self.win_width < 100:
            self.win_width = 100
        if self.win_height < 100:
            self.win_height = 100

    def write_config(self):
        import tomlkit

        config = self.system.get_entity_by_name("ConfigHelper")
        if not config:
            return

        section_name = basis.short_class_name(self)  # название раздела конфигурации для этого окна

        net_viewer = config.data.get(section_name, None)
        if not net_viewer:
            net_viewer = tomlkit.table()
            config.data.add(section_name, net_viewer)

            window = tomlkit.table()
            net_viewer.add('window', window)

        window = net_viewer.get('window', None)
        if window is None:
            return

        window['width'] = self.win_width
        window['height'] = self.win_height
        window['x'] = self.win_x
        window['y'] = self.win_y
        window['maximized'] = self.win_maximized

    def on_window_resize(self):
        glfw.make_context_current(self.window)

        gl.glViewport(0, 0, self.win_width, self.win_height)

        sprite_shader = self.resource_manager.get_shader("sprite")
        sprite_shader.use()
        sprite_shader.set_integer("image", 0)
        projection = glm.ortho(0.0, self.win_width, 0.0, self.win_height)
        sprite_shader.set_matrix4("projection", projection)
        self.renderer = gogl.SpriteRenderer(sprite_shader)

        text_shader = self.resource_manager.get_shader("freetypetext")
        text_shader.use()
        text_shader.set_integer("text", 0)
        projection = glm.ortho(0.0, self.win_width, 0.0, self.win_height)
        text_shader.set_matrix4("projection", projection)
        self.text_renderer = gogl.TextRenderer(text_shader)
        self.text_renderer.make_face("res/TerminusTTFWindows-4.46.0.ttf")

        poly_shader = self.resource_manager.get_shader("polygon")
        poly_shader.use()
        projection = glm.ortho(0.0, self.win_width, 0.0, self.win_height)
        poly_shader.set_matrix4("projection", projection)

    def window_size_callback(self, window, width, height):
        self.win_width = width
        self.win_height = height
        self.on_window_resize()

    def window_pos_callback(self, window, x, y):
        self.win_x = x
        self.win_y = y

    def window_maximize_callback(self, window, maximized):
        self.win_maximized = maximized

    def draw_memory(self, memory, pos, scale):
        x0 = pos[0]
        y0 = pos[1]

        # polygon = gogl.Polygon(self.resource_manager.get_shader("polygon"))
        # polygon.set_points([
        #     glm.vec2(0.0, 0.0),
        #     glm.vec2(1.0, 0.0),
        #     glm.vec2(1.0, 1.0),
        #     glm.vec2(0.0, 1.0),
        #     glm.vec2(0.0, 0.0)
        # ])
        # polygon.draw(glm.vec2(x0, y0), glm.vec2(width, height), 0.0, glm.vec3(0.1, 0.1, 0.1), True)

        net_w = 0.0
        net_h = 0.0
        top_left = cells.Point(0.0, 0.0, 0.0)
        bottom_right = cells.Point(0.0, 0.0, 0.0)
        for ent in memory.entities:
            neuron = ent.get_facet(cells.Neuron)
            if not neuron:
                continue

            if neuron.position.x < top_left.x:
                top_left.x = neuron.position.x
            if neuron.position.y < top_left.y:
                top_left.y = neuron.position.y
            r = neuron.position.x + neuron.size.x
            b = neuron.position.y + neuron.size.y
            if r > bottom_right.x:
                bottom_right.x = r
            if b > bottom_right.y:
                bottom_right.y = b

        for key, lnk in memory.links.items():
            src_ent = memory.get_entity_by_id(lnk.src_id)
            if not src_ent:
                continue
            dst_ent = memory.get_entity_by_id(lnk.dst_id)
            if not dst_ent:
                continue
            pt_src = glm.vec2(
                x0 + src_ent.neuron.position.x + src_ent.neuron.size.x * 0.5,
                y0 + src_ent.neuron.position.y + src_ent.neuron.size.y * 0.5
            )
            pt_dst = glm.vec2(
                x0 + dst_ent.neuron.position.x + dst_ent.neuron.size.x * 0.5,
                y0 + dst_ent.neuron.position.y + dst_ent.neuron.size.y * 0.5
            )

            lnk_color = glm.vec3(0.8, 0.8, 0.8)
            if lnk.polarity > 0:
                lnk_color = glm.vec3(1.0, 0.5, 0.5)
            elif lnk.polarity < 0:
                lnk_color = glm.vec3(0.5, 0.5, 1.0)
            self.lnk_arc.draw_by_two_points(pt_src, pt_dst, lnk_color, False)

        for ent in memory.entities:
            neuron = ent.get_facet(cells.Neuron)
            if not neuron:
                continue

            fill_color = self.color_neuron_inactive
            if neuron.is_active():
                fill_color = self.color_neuron_active

            neuron_input_percent = 0
            border_color = glm.vec3(0.1, 0.1, 0.1)
            if neuron.input > 0:
                if neuron.input < neuron.threshold:
                    neuron_input_percent = neuron.input / neuron.threshold
                    border_color = glm.vec3(
                        0.5 * neuron_input_percent, neuron_input_percent, 0.5 * neuron_input_percent
                    )
                else:
                    neuron_input_percent = 1.0
                    border_color = glm.vec3(1.0, 0.1, 0.1)

            # граница нейрона
            # self.neuron_circle.draw(
            #     glm.vec2(x0 + neuron.position.x + neuron.size.x * 0.5, y0 + neuron.position.y + neuron.size.y * 0.5),
            #     glm.vec2(neuron.size.x + 4, neuron.size.y + 4), 0.0, border_color)
            # внутренность нейрона
            self.neuron_circle.draw(
                glm.vec2(x0 + neuron.position.x + neuron.size.x * 0.5, y0 + neuron.position.y + neuron.size.y * 0.5),
                glm.vec2(neuron.size.x, neuron.size.y), 0.0, fill_color)

            indicator_size_x = neuron.size.x
            indicator_size_y = indicator_size_x / 10.0
            self.neuron_input_indicator.draw(
                glm.vec2(x0 + neuron.position.x + neuron.size.x + 4, y0 + neuron.position.y + neuron.size.y + 4),
                glm.vec2(indicator_size_x, indicator_size_y),
                0.0,
                glm.vec3(0.3, 0.3, 0.3),
                True
            )
            self.neuron_input_indicator.draw(
                glm.vec2(x0 + neuron.position.x + neuron.size.x + 4, y0 + neuron.position.y + neuron.size.y + 4),
                glm.vec2(indicator_size_x * neuron_input_percent, indicator_size_y),
                0.0,
                glm.vec3(0.5, 1.0, 0.5),
                True
            )

            #info_str = "{} - {}".format(str(ent.uuid.fields[0]), basis.qual_class_name(ent))
            info_str = "{} - {}".format(str(ent.uuid.fields[0]), ent.full_name())
            self.text_renderer.draw_text(info_str, x0 + neuron.position.x, y0 + neuron.position.y, 0.3,
                                         glm.vec3(1.0, 1.0, 1.0))

    def draw(self):
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

        self.render_engine.process_inputs()

        self.draw_memory(self.agent.memory, (self.win_width * 0.5, self.win_height * 0.5), 1.0)

        glfw.swap_buffers(self.window)

    def step(self):
        self.draw()

    def init_glfw(self):
        # Initialize the GLFW library
        if not glfw.init():
            return None

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
            return None

        # Makes window current on the calling thread
        glfw.make_context_current(window)

        # Passing window to main()
        return window
