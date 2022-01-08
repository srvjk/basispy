import basis
import glfw
import OpenGL.GL as gl
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glm
import graphics_opengl as gogl
import net_core
import basis_ui


class NetControlWindow(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.net_id = None
        self.net_viewer_id = None
        self.selected_neuron_x = 0
        self.selected_neuron_y = 0
        self.selected_neurons = set()
        self.show_links = False

    def set_net(self, net_id):
        self.net_id = net_id

    def draw(self):
        network = self.get_entity_by_id(self.net_id)
        if not network:
            return

        imgui.set_next_window_size(640, 480)
        imgui.begin("Net Control [{}]".format(network.name))

        net_viewer = self.get_entity_by_id(self.net_viewer_id)
        if not net_viewer:
            imgui.push_style_color(imgui.COLOR_TEXT, 1.0, 0.3, 0.0)
            imgui.text("Warning: NetViewer not found")
            imgui.pop_style_color()

        if net_viewer:
            if imgui.button("Size +"):
                net_viewer.neuron_size += 1
            if imgui.button("Size -"):
                if net_viewer.neuron_size > 1:
                    net_viewer.neuron_size -= 1

        _, self.selected_neuron_x = imgui.input_int("neur. X", self.selected_neuron_x)
        _, self.selected_neuron_y = imgui.input_int("neur. Y", self.selected_neuron_y)

        if imgui.button("Add to list"):
            d = 0.1
            x_min = self.selected_neuron_x - d
            y_min = self.selected_neuron_y - d
            z_min = 0 - d
            x_max = self.selected_neuron_x + d
            y_max = self.selected_neuron_y + d
            z_max = 0 + d

            neuron_uuids = network.spatial_index.intersection((x_min, y_min, z_min, x_max, y_max, z_max),
                                                              objects="raw")
            for item in neuron_uuids:
                self.selected_neurons.add(item)

            # current_neuron_index = 0
            # for neuron in network.entities:
            #     if isinstance(neuron, net.Neuron):
            #         if self.selected_neuron_number == current_neuron_index:
            #             self.selected_neurons.add(neuron.uuid)
            #         current_neuron_index += 1

        for item in self.selected_neurons:
            imgui.selectable("{}".format(item))

        if self.selected_neurons:
            if imgui.button("Clear list"):
                self.selected_neurons.clear()
            base_color = (0.5, 0.0, 0.8)
            color_dim = basis_ui.make_color_dim(*base_color)
            color_bright = basis_ui.make_color_bright(*base_color)
            color = color_bright if self.show_links else color_dim
            color_hovered = basis_ui.make_color_bright(*color, factor=1.1)
            color_active = color_hovered
            imgui.push_style_color(imgui.COLOR_BUTTON, *color)
            imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *color_hovered)
            imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *color_active)
            if imgui.button("Links"):
                self.show_links = not self.show_links
            imgui.pop_style_color(3)

        imgui.end()

class NetViewer(basis.Entity):
    initial_win_size = (initial_win_width, initial_win_height) = (800, 600)

    def __init__(self, system):
        super().__init__(system)
        self.net_name = None
        self.net = None
        self.neuron_size = 5
        self.margin = 2

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
        self.selection_frame_color = glm.vec3(1.0, 0.2, 0.2)

        # переменные состояния для пользовательского интерфейса ImGui
        self.selected_subnet_number = 0  # номер текущей выбранной подсети
        self.selected_neuron_number = 0  # номер нейрона, выбранного на контрольной панели

        self.net_control_window = self.new(NetControlWindow)

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

        polygon = gogl.Polygon(gogl.resource_manager.get_shader("polygon"))
        polygon.set_points([
            glm.vec2(0.0, 0.0),
            glm.vec2(1.0, 0.0),
            glm.vec2(1.0, 1.0),
            glm.vec2(0.0, 1.0),
            glm.vec2(0.0, 0.0)
        ])

        line = gogl.Polygon(gogl.resource_manager.get_shader("polygon"))
        line_color = glm.vec3(0.7, 0.7, 0.7)

        for neuron in self.net.entities:
            if not isinstance(neuron, net_core.Neuron):
                continue
            x = x0 + neuron.pos[0] * (self.neuron_size + self.margin)
            y = y0 + neuron.pos[1] * (self.neuron_size + self.margin)
            color = self.active_neuron_color if neuron.is_active() else self.inactive_neuron_color
            polygon.draw(glm.vec2(x, y), glm.vec2(self.neuron_size, self.neuron_size),
                         0.0, color, True)

            if self.net_control_window:
                if neuron.uuid in self.net_control_window.selected_neurons:
                    polygon.draw(glm.vec2(x, y), glm.vec2(self.neuron_size, self.neuron_size),
                                 0.0, self.selection_frame_color, False)
                    if self.net_control_window.show_links:
                        for link in neuron.out_links:
                            x_dst = (link.dst_neuron.pos[0] - neuron.pos[0]) * (self.neuron_size + self.margin)
                            y_dst = (link.dst_neuron.pos[1] - neuron.pos[1]) * (self.neuron_size + self.margin)
                            line.set_points([
                                glm.vec2(0.0, 0.0),
                                glm.vec2(x_dst, y_dst)
                            ])
                            line.draw(glm.vec2(x, y), glm.vec2(1.0, 1.0), 0.0, line_color, False)


    def step(self):
        if glfw.window_should_close(self.window):
            self.render_engine.shutdown()
            glfw.terminate()
            self.system.shutdown()
            return

        glfw.make_context_current(self.window)
        imgui.set_current_context(self.imgui_context)
        glfw.poll_events()

        glfw.set_window_title(self.window, "Net")
        glfw.set_window_size(self.window, self.win_width, self.win_height)

        imgui.new_frame()

        self.net_control_window.draw()

        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        if not self.net: # TODO временно, переделать!
            if self.net_name:
                nets = self.system.get_entities_by_name_recursively(self.net_name)
                if len(nets) > 0:
                    self.net = nets[0]
                    if self.net_control_window:
                        self.net_control_window.set_net(self.net.uuid)
                        self.net_control_window.net_viewer_id = self.uuid

        self.draw_net((0, 0), (self.win_width, self.win_height))

        imgui.render()
        self.render_engine.render(imgui.get_draw_data())
        glfw.swap_buffers(self.window)
        self.render_engine.process_inputs()
