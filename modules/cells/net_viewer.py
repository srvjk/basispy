import basis
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glm
import graphics_opengl as gogl
import net
import basis_ui


class NetViewer(basis.Entity):
    initial_win_size = (initial_win_width, initial_win_height) = (800, 600)

    def __init__(self, system):
        super().__init__(system)
        self.net_name = None
        self.net = None

        self.imgui_context = imgui.create_context()
        imgui.set_current_context(self.imgui_context)
        self.window = basis_ui.create_glfw_window()
        self.render_engine = GlfwRenderer(self.window)
        io = imgui.get_io()
        io.fonts.add_font_default()

        glfw.set_window_size_callback(self.window, self.window_size_callback)

        glfw.make_context_current(self.window)

        self.win_width = NetViewer.initial_win_width
        self.win_height = NetViewer.initial_win_height

        gogl.resource_manager.load_shader("polygon", "polygon.vs", "polygon.fs")

        self.renderer = None
        self.on_window_resize()

        # alpha blending (for transparency, semi-transparency, etc.)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.inactive_neuron_color = glm.vec3(0.2, 0.2, 0.2)
        self.active_neuron_color = glm.vec3(1.0, 1.0, 0.2)

    def on_window_resize(self):
        glfw.make_context_current(self.window)

        gl.glViewport(0, 0, self.win_width, self.win_height)
        projection = glm.ortho(0.0, self.win_width, self.win_height, 0.0)

        poly_shader = gogl.resource_manager.get_shader("polygon")
        poly_shader.use()
        poly_shader.set_matrix4("projection", projection)

    def window_size_callback(self, window, width, height):
        self.win_width = width
        self.win_height = height
        self.on_window_resize()

    def draw_net(self, pos, size):
        if not self.net:
            return

        x0 = pos[0]
        y0 = pos[1]
        n_size = 5

        polygon = gogl.Polygon(gogl.resource_manager.get_shader("polygon"))
        polygon.set_points([
            glm.vec2(0.0, 0.0),
            glm.vec2(1.0, 0.0),
            glm.vec2(1.0, 1.0),
            glm.vec2(0.0, 1.0),
            glm.vec2(0.0, 0.0)
        ])

        for ent in self.net.entities:
            if isinstance(ent, net.SubNet):
                for neuron in ent.neurons:
                    n_x = neuron.geo_pos[0]
                    n_y = neuron.geo_pos[1]
                    color = self.active_neuron_color if neuron.is_active() else self.inactive_neuron_color
                    polygon.draw(glm.vec2(x0 + n_x, y0 + n_y), glm.vec2(n_size, n_size), 0.0, color, True)

    def draw_control_window(self):
        imgui.set_next_window_size(200, 200)
        imgui.begin("Control panel")

        selected_neuron_number = imgui.input_int("neuron number", 0)

        imgui.end()

    def step(self):
        glfw.make_context_current(self.window)
        imgui.set_current_context(self.imgui_context)
        glfw.poll_events()

        glfw.set_window_title(self.window, "Net")
        glfw.set_window_size(self.window, self.win_width, self.win_height)

        imgui.new_frame()

        self.draw_control_window()

        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        if not self.net: # TODO временно, переделать!
            if self.net_name:
                nets = self.system.find_entities_by_name_recursively(self.net_name)
                if len(nets) > 0:
                    self.net = nets[0]

        self.draw_net((0, 0), (self.win_width, self.win_height))

        imgui.render()
        self.render_engine.render(imgui.get_draw_data())
        glfw.swap_buffers(self.window)
        self.render_engine.process_inputs()
