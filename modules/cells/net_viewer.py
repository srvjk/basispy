import basis
import glfw
import OpenGL.GL as gl
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glm
import graphics_opengl as gogl
import net_core
import basis_ui

class NeuronInfoWindow(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.neuron = None

    def draw(self):
        if not self.neuron:
            return

        imgui.begin("Neuron {}".format(self.neuron.uuid))

        imgui.end()


class NetControlWindow(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.net_id = None
        self.net_viewer_id = None
        self.selected_neuron_x = 0
        self.selected_neuron_y = 0
        self.selected_neurons = set()
        self.show_net = False
        self.show_links = False
        self.pause_on = False

    def set_net(self, net_id):
        self.net_id = net_id

    def draw(self):
        network = self.get_entity_by_id(self.net_id)
        if not network:
            return

        # imgui.set_next_window_size(640, 480)
        imgui.begin("Net Control [{}]".format(network.name))

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


        show_net_button_text = "Hide Net" if self.show_net else "Show Net"
        if imgui.button(show_net_button_text):
            self.show_net = not self.show_net

        if imgui.button("Activate Net"):
            self.system.activate(network)

        # pause_button_text = "Resume" if self.pause_on else "Pause"
        # if imgui.button(pause_button_text):
        #     self.pause_on = not self.pause_on
        #     self.system.pause(self.pause_on)
        #     for k, v in self.system.entity_uuid_index.items():
        #         if not isinstance(v, (NetControlWindow, NetViewer)):
        #             v.pause(self.pause_on)

        pause_button_text = "Resume" if self.system.pause else "Pause"
        if imgui.button(pause_button_text):
            self.system.pause = not self.system.pause
        imgui.same_line()
        if imgui.button(">"):
            self.system.step_forward_time_delta = 1e9  #TODO сделать настраиваемым

        imgui.text("System steps: {}".format(self.system.get_step_counter()))
        imgui.text("System fps: {:.2f}".format(self.system.get_fps()))

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

            # кнопка 'Links':
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

            # кнопка 'Info':
            base_color = (0.0, 0.8, 0.5)
            color_dim = basis_ui.make_color_dim(*base_color)
            color_bright = basis_ui.make_color_bright(*base_color)
            color = color_bright if self.show_links else color_dim
            color_hovered = basis_ui.make_color_bright(*color, factor=1.1)
            color_active = color_hovered
            imgui.push_style_color(imgui.COLOR_BUTTON, *color)
            imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, *color_hovered)
            imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, *color_active)
            if imgui.button("Info"):
                self.append_info_windows(self.selected_neurons)
            imgui.pop_style_color(3)

        imgui.dummy(0.0, 20.0)

        # кнопки для триггеров, определенных в сценарии
        scenario = self.system.get_entity_by_name("Scenario")
        if scenario:
            triggers = scenario.get_entities_by_type(basis.OnOffTrigger)
            for trigger in triggers:
                if imgui.button("{}:{}".format(trigger.name, trigger.caption())):
                    trigger.toggle()
                imgui.same_line()

        imgui.end()

    def append_info_windows(self, uuids):
        """
        Создать и вывести информационные окна для данного списка сущностей, если таких ещё нет.
        :param uuids: идентификаторы сущностей, для которых нужно создать инфоокна
        :return:
        """
        net_viewer = self.get_entity_by_id(self.net_viewer_id)
        if not net_viewer:
            return

        for id in uuids:
            ent = self.system.get_entity_by_id(id)
            if not ent:
                continue
            if isinstance(ent, net_core.Neuron):
                if id not in net_viewer.neurons_to_show.keys():
                    info_window = net_viewer.new(NeuronInfoWindow)
                    info_window.neuron = ent
                    net_viewer.neurons_to_show[id] = info_window


class NetViewer(basis.Entity):
    initial_win_size = (initial_win_width, initial_win_height) = (800, 600)  #TODO убрать это, брать прошлый размер

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
        self.neurons_to_show = dict()

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

        if not self.net_control_window.show_net:
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

        # базовые цвета связей (окончательные будут зависеть от веса связи)
        excitatory_link_color_base = glm.vec3(1.0, 0.1, 0.1)  # базовый цвет для возбуждающей сввзи
        inhibitory_link_color_base = glm.vec3(0.1, 0.1, 1.0)  # базовый цвет для тормозящей связи

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
            for neuron_uuid in self.net_control_window.selected_neurons:
                neuron = self.net.get_entity_by_id(neuron_uuid)
                if neuron:
                    x = x0 + neuron.pos[0] * (self.neuron_size + self.margin)
                    y = y0 + neuron.pos[1] * (self.neuron_size + self.margin)
                    for link in neuron.out_links:
                        x_dst = (link.dst_neuron.pos[0] - neuron.pos[0]) * (self.neuron_size + self.margin)
                        y_dst = (link.dst_neuron.pos[1] - neuron.pos[1]) * (self.neuron_size + self.margin)
                        neur_half_size = self.neuron_size / 2.0
                        line.set_points([
                            glm.vec2(neur_half_size, neur_half_size),
                            glm.vec2(x_dst + neur_half_size, y_dst + neur_half_size)
                        ])

                        link_base_color = excitatory_link_color_base if link.sign > 0 else inhibitory_link_color_base

                        line.draw(glm.vec2(x, y), glm.vec2(1.0, 1.0), 0.0, link_base_color, False)

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

        # окно управления
        self.net_control_window.draw()
        # информационные окна нейронов, если они есть
        for _, wnd in self.neurons_to_show.items():
            wnd.draw()

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
