import OpenGL.GL as gl
import glm
import math
from PIL import Image
from numpy import asarray
import freetype


def angle_between_vectors_2d(vec1, vec2):
    """
    Вычисляет угол в радианах от вектора vec1 к вектору vec2 (векторы двухмерные).
    :param vec1:
    :param vec2:
    :return:
    """
    vec1_norm = glm.normalize(vec1)
    vec2_norm = glm.normalize(vec2)
    ang = glm.acos(glm.dot(vec1_norm, vec2_norm))
    crz = vec1_norm.x * vec2_norm.y - vec2_norm.x * vec1_norm.y
    if crz < 0:
        ang *= -1.0
        #ang += glm.pi()

    return ang

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
        try:
            gl.glUseProgram(self.shader_program)
        except gl.GLError as err:
            print("GLError {} in Shader.use(), shader program id {}".format(err.err, self.shader_program))
            if err.err == 1282:  # похоже, ошибку 1282 можно игнорировать без видимых последствий
                pass
            else:
                raise

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


class ResourceManager:
    def __init__(self):
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
        try:
            self.shader.set_matrix4("model", model)
            self.shader.set_vector3f("spriteColor", color)
        except gl.GLError as err:
            print("GLError {} occured, ignored".format(err.err))
            if err.err == 1282:  # похоже, ошибку 1282 можно игнорировать без видимых последствий
                pass
            else:
                raise

        gl.glActiveTexture(gl.GL_TEXTURE0)
        texture.bind()

        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)
        gl.glBindVertexArray(0)


class Line:
    def __init__(self, shader):
        self.vao = None
        self.shader = shader
        self.vertex_count = 2
        self.vertices = list()
        self.vertices.append(0.0)
        self.vertices.append(0.0)
        self.vertices.append(1.0)
        self.vertices.append(0.0)

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

    def draw(self, position, size, rotate, color):
        model = glm.mat4(1.0)
        model = glm.translate(model, glm.vec3(position, 0.0))
        model = glm.rotate(model, glm.radians(rotate), glm.vec3(0.0, 0.0, 1.0))
        model = glm.scale(model, glm.vec3(size, 1.0))

        self.shader.use()
        self.shader.set_matrix4("model", model)
        self.shader.set_vector3f("polygonColor", color)

        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_LINE_STRIP, 0, self.vertex_count)
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
        """
        Нарисовать ломаную относительно точки position.
        :param position:
        :param size:
        :param rotate:
        :param color:
        :param filled:
        :return:
        """
        model = glm.mat4(1.0)
        model = glm.translate(model, glm.vec3(position, 0.0))
        model = glm.rotate(model, rotate, glm.vec3(0.0, 0.0, 1.0))
        model = glm.scale(model, glm.vec3(size, 1.0))

        self.shader.use()
        self.shader.set_matrix4("model", model)
        self.shader.set_vector3f("polygonColor", color)

        gl.glBindVertexArray(self.vao)
        if filled:
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, self.vertex_count)
        else:
            gl.glDrawArrays(gl.GL_LINE_STRIP, 0, self.vertex_count)
        gl.glBindVertexArray(0)

    def draw_centered(self, position, size, rotate, color, filled):
        """
        Нарисовать ломаную относительно ее геометрического центра.
        :param position:
        :param size:
        :param rotate:
        :param color:
        :param filled:
        :return:
        """
        model = glm.mat4(1.0)
        model = glm.translate(model, glm.vec3(position, 0.0))
        model = glm.translate(model, glm.vec3(0.5 * size[0], 0.5 * size[1], 0.0))
        #model = glm.rotate(model, glm.radians(rotate), glm.vec3(0.0, 0.0, 1.0))
        model = glm.rotate(model, rotate, glm.vec3(0.0, 0.0, 1.0))
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
        gl.glBindVertexArray(0)


class Arc(Polygon):
    def __init__(self, shader, alpha, num_points):
        """
        Инициализация дуги
        :param shader:
        :param alpha: радиус кривизны дуги в радианах
        :param num_points: кол-во промежуточных точек дуги (не считая начальной и конечной)
        """
        super().__init__(shader)
        points = list()

        d = 1.0
        r = (0.5 * d) / glm.sin(0.5 * alpha)  # радиус дуги
        d_angle = alpha / (num_points + 1)  # приращение угла между точками ломаной
        vAB_3 = glm.vec3(r, 0.0, 0.0)
        beta = (glm.pi() - alpha) * 0.5
        vOA_3 = -glm.rotateZ(vAB_3, -beta)
        vOA_2 = glm.vec2(vOA_3.x, vOA_3.y)

        points.append(glm.vec2(0.0, 0.0))  # точка A

        angle = 0.0
        for i in range(num_points):
            angle += d_angle
            v_3 = glm.rotateZ(vOA_3, -angle)  # вращаем вокруг центра дуги по часовой стрелке
            v_2 = glm.vec2(v_3.x, v_3.y)
            x_v = v_2 - vOA_2

            points.append(x_v)

        points.append(glm.vec2(1.0, 0.0))  # точка B

        self.set_points(points)

    def draw_by_two_points(self, p1, p2, color, filled):
        v1 = glm.vec2(1.0, 0.0)
        v2 = p2 - p1
        length = glm.length(v2)
        size = glm.vec2(length, length)
        angle = angle_between_vectors_2d(v1, v2)
        super().draw(p1, size, angle, color, filled)


class Character:
    def __init__(self):
        self.texture = None
        self.size = glm.vec2(1.0, 1.0)
        self.bearing = glm.vec2(0.0, 0.0)
        self.advance = 0


class TextRenderer:
    def __init__(self, shader):
        self.vao = None
        self.vbo = None
        self.shader = shader
        self.characters = dict()

        self.vao = gl.glGenVertexArrays(1)
        self.vbo = gl.glGenBuffers(1)
        gl.glBindVertexArray(self.vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * 6 * 4, None, gl.GL_DYNAMIC_DRAW)
        gl.glEnableVertexAttribArray(0)
        gl.glVertexAttribPointer(0, 4, gl.GL_FLOAT, gl.GL_FALSE, 16, None)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindVertexArray(0)

    def make_face(self, face_file_path):
        face = freetype.Face(face_file_path)
        face.set_pixel_sizes(0, 48)

        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)

        for i in range(0, 128):
            ch = chr(i)
            face.load_char(ch, flags=freetype.FT_LOAD_RENDER)
            bitmap = face.glyph.bitmap

            ch_descr = Character()
            self.characters[ch] = ch_descr

            ch_descr.size = glm.vec2(face.glyph.bitmap.width, face.glyph.bitmap.rows)
            ch_descr.bearing = glm.vec2(face.glyph.bitmap_left, face.glyph.bitmap_top)
            ch_descr.advance = face.glyph.advance.x

            ch_descr.texture = Texture()
            ch_descr.texture.internal_format = gl.GL_RED
            ch_descr.texture.image_format = gl.GL_RED
            ch_descr.texture.generate(bitmap.width, bitmap.rows, bitmap.buffer)

    def draw_text(self, text, x, y, scale, color):
        self.shader.use()
        self.shader.set_vector3f("textColor", color)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindVertexArray(self.vao)

        for ch in text:
            ch_descr = self.characters[ch]

            w = ch_descr.size.x * scale
            h = ch_descr.size.y * scale
            x_ch = x + ch_descr.bearing.x * scale
            y_ch = y - (ch_descr.size.y - ch_descr.bearing.y) * scale

            vertices = [
                # 1st triangle
                # pos               tex
                x_ch,     y_ch,     0.0, 1.0,
                x_ch + w, y_ch + h, 1.0, 0.0,
                x_ch,     y_ch + h, 0.0, 0.0,
                # 2nd triangle
                # pos               tex
                x_ch, y_ch,         0.0, 1.0,
                x_ch + w, y_ch,     1.0, 1.0,
                x_ch + w, y_ch + h, 1.0, 0.0
            ]

            ch_descr.texture.bind()

            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
            gl.glBufferSubData(gl.GL_ARRAY_BUFFER, 0, len(vertices) * 4, (gl.GLfloat * len(vertices))(*vertices))

            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
            gl.glBindVertexArray(0)

            gl.glBindVertexArray(self.vao)
            gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)
            gl.glBindVertexArray(0)

            x += (ch_descr.advance >> 6) * scale

        gl.glBindVertexArray(0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

def test():
    """
    Юнит-тесты.
    :return:
    """
    ang = angle_between_vectors_2d(glm.vec2(1.0, 0.0), glm.vec2(1.0, 0.0))
    if not math.isclose(ang, 0.0):
        return False
    ang = angle_between_vectors_2d(glm.vec2(1.0, 0.0), glm.vec2(0.0, 1.0))
    if not math.isclose(ang, glm.pi() / 2.0):
        return False
    ang = angle_between_vectors_2d(glm.vec2(0.0, 1.0), glm.vec2(1.0, 0.0))
    if not math.isclose(ang, -glm.pi() / 2.0):
        return False
    ang = angle_between_vectors_2d(glm.vec2(1.0, 0.0), glm.vec2(-1.0, 0.0))
    if not math.isclose(ang, glm.pi()):
        return False
    ang = angle_between_vectors_2d(glm.vec2(-1.0, 0.0), glm.vec2(1.0, 0.0))
    if not math.isclose(ang, glm.pi()):
        return False
    ang = angle_between_vectors_2d(glm.vec2(1.0, 0.0), glm.vec2(1.0, 1.0))
    if not math.isclose(ang, glm.pi() / 4.0, rel_tol=1e-6):
        return False
    ang = angle_between_vectors_2d(glm.vec2(1.0, 0.0), glm.vec2(-1.0, 1.0))
    if not math.isclose(ang, (3.0 * glm.pi()) / 4.0, rel_tol=1e-6):
        return False
    ang = angle_between_vectors_2d(glm.vec2(1.0, 0.0), glm.vec2(-1.0, -1.0))
    if not math.isclose(ang, -(3.0 * glm.pi()) / 4.0, rel_tol=1e-6):
        return False
    ang = angle_between_vectors_2d(glm.vec2(1.0, 0.0), glm.vec2(1.0, -1.0))
    if not math.isclose(ang, -glm.pi() / 4.0, rel_tol=1e-6):
        return False

    return True

if __name__ == "__main__":
    res = test()
    if res:
        print("unit tests passed successfully for module 'graphics_opengl'")
    else:
        print("unit tests FAILED for module 'graphics_opengl'")
