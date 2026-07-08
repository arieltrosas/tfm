from typing import Final
from geometry.types import TriangleMesh, mesh_to_tensor

import glfw
import numpy as np
import open3d as o3d

from OpenGL.GL import *

class Renderer:
    """
    Off screen renderer for obtaining stencil occupancy slices.
    """

    VertexShaderSource: Final[str] = \
    r"""
    #version 330 core

    layout(location = 0) in vec3 vertex;

    uniform mat4 u_proj;
    uniform mat4 u_model;

    void main()
    {
        gl_Position = u_proj * vec4(vertex, 1.0);
    }
    """

    FragmentShaderSource: Final[str] = \
    r"""
    #version 330 core

    out vec4 frag_color;

    void main() {
        frag_color = vec4(1.0, 0.0, 0.0, 1.0);
    }
    """

    @staticmethod
    def ortho(l, r, b, t, n, f):
        m = np.zeros((4,4), dtype=np.float32)

        m[0,0] = 2.0 / (r - l)
        m[1,1] = 2.0 / (t - b)
        m[2,2] = 2.0 / (f - n)
        m[3,3] = 1.0

        m[0,3] = -(r + l) / (r - l)
        m[1,3] = -(t + b) / (t - b)
        m[2,3] = -(f + n) / (f - n)

        return m


    @staticmethod
    def translation(x: float, y: float, z: float) -> np.ndarray:
        m = np.zeros((4,4), dtype=np.float32)
        m[0,0] = 1.0
        m[1,1] = 1.0
        m[2,2] = 1.0
        m[3,3] = 1.0
        m[3,0] = x
        m[3,1] = y
        m[3,2] = z
        return m


    @staticmethod
    def rotation(angle: float, axis: np.ndarray) -> np.ndarray:
        axis = np.asarray(axis, dtype=np.float32)
        axis = axis / np.linalg.norm(axis)
        x, y, z = axis
        c = np.cos(angle)
        s = np.sin(angle)
        t = 1 - c

        m = np.zeros((4, 4), dtype=np.float32)

        m[0, 0] = t * x * x + c
        m[0, 1] = t * x * y - s * z
        m[0, 2] = t * x * z + s * y
        m[1, 0] = t * x * y + s * z
        m[1, 1] = t * y * y + c
        m[1, 2] = t * y * z - s * x
        m[2, 0] = t * x * z - s * y
        m[2, 1] = t * y * z + s * x
        m[2, 2] = t * z * z + c
        m[3, 3] = 1.0

        return m
   

    @staticmethod
    def scale(x: float, y: float, z: float) -> np.ndarray:
        m = np.zeros((4,4), dtype=np.float32)
        m[0,0] = x
        m[1,1] = y
        m[2,2] = z
        m[3,3] = 1.0
        return m


    def __init__(self, render_color: bool = False) -> None:
        self.window = None

        self.width = None
        self.height = None

        self.min_bound = None
        self.max_bound = None

        self.fbo = None
        self.color = None
        self.stencil = None

        self.shader = None
        self.u_locs = None

        self.vbo = None
        self.ebo = None
        self.vao = None
        self.elem_count = None

        self.render_color = render_color


    def _create_framebuffer(self) -> None:

        self._delete_framebuffer()

        # color texture
            
        self.color = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.color)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA8,
            self.width,
            self.height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            None
        )
        
        # depth-stencil buffer

        self.stencil = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, self.stencil)

        glRenderbufferStorage(
            GL_RENDERBUFFER,
            GL_DEPTH24_STENCIL8,
            self.width,
            self.height
        )

        # framebuffer
        
        self.fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)

        glFramebufferTexture2D(
            GL_FRAMEBUFFER,
            GL_COLOR_ATTACHMENT0,
            GL_TEXTURE_2D,
            self.color,
            0
        )

        glFramebufferRenderbuffer(
            GL_FRAMEBUFFER,
            GL_DEPTH_STENCIL_ATTACHMENT,
            GL_RENDERBUFFER,
            self.stencil
        )

        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)

        if status != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Error creating framebuffer")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
  

    def _create_shader(self) -> None:

        self._delete_shader()

        def compile_shader(shader_source: str, shader_type: int) -> None:
            shader = glCreateShader(shader_type)
            glShaderSource(shader, shader_source)
            glCompileShader(shader)

            if not glGetShaderiv(shader, GL_COMPILE_STATUS):
                raise RuntimeError(glGetShaderInfoLog(shader))

            return shader

        vertex_shader = compile_shader(self.VertexShaderSource, GL_VERTEX_SHADER)
        fragment_shader = compile_shader(self.FragmentShaderSource, GL_FRAGMENT_SHADER)

        self.shader = glCreateProgram()

        glAttachShader(self.shader, vertex_shader)
        glAttachShader(self.shader, fragment_shader)
        glLinkProgram(self.shader)

        if not glGetProgramiv(self.shader, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(self.shader))
        
        self.u_locs = {
            "u_proj": glGetUniformLocation(self.shader, "u_proj"),
            "u_model": glGetUniformLocation(self.shader, "u_model"),
        }

        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
    

    def _delete_framebuffer(self) -> None:
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        if self.fbo is not None:
            glDeleteFramebuffers(1, [self.fbo])
        if self.stencil is not None:
            glDeleteRenderbuffers(1, [self.stencil])
        if self.color is not None:
            glDeleteTextures(1, [self.color])


    def _delete_shader(self) -> None:
        glUseProgram(0)
        if self.shader is not None:
            glDeleteProgram(self.shader)


    def _delete_vertex_buffers(self) -> None:
        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        if self.vbo is not None:
            glDeleteBuffers(1, [self.vbo])
        if self.ebo is not None:
            glDeleteBuffers(1, [self.ebo])
        if self.vao is not None:
            glDeleteVertexArrays(1, [self.vao])


    def _read_buffers(self) -> tuple[np.ndarray, np.ndarray]:

        color = None
        stencil = None

        stencil = glReadPixels(
            0, 0,
            self.width, self.height,
            GL_STENCIL_INDEX,
            GL_UNSIGNED_BYTE
        )
        stencil = np.frombuffer(stencil, dtype=np.uint8).reshape(self.height, self.width)

        if self.render_color:
            color = glReadPixels(
                0, 0,
                self.width, self.height,
                GL_RGBA,
                GL_UNSIGNED_BYTE
            )
            color = np.frombuffer(color, dtype=np.uint8).reshape(self.height, self.width, 4)
        
        return stencil, color
    

    def initialize(self, width: int, height: int) -> None:

        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")

        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 5)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

        self.window = glfw.create_window(1, 1, "", None, None)

        if self.window is None:
            glfw.terminate()
            raise RuntimeError("Failed to create OpenGL context")

        glfw.make_context_current(self.window)

        self.width = width
        self.height = height

        self._create_framebuffer()
        self._create_shader()
    

    def upload_model(self, min_bound: np.ndarray, max_bound: np.ndarray, vertex: np.ndarray, index: np.ndarray) -> None:

        self._delete_vertex_buffers()

        self.min_bound = min_bound
        self.max_bound = max_bound

        vertex_buffer = np.array(vertex, dtype=np.float32)
        index_buffer = np.array(index, dtype=np.uint32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertex_buffer.nbytes, vertex_buffer, GL_STATIC_DRAW)
        
        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, index_buffer.nbytes, index_buffer, GL_STATIC_DRAW)

        self.elem_count = index_buffer.size

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

        glBindVertexArray(0)
   

    def render_begin(self) -> None:
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)

        glViewport(0, 0, self.width, self.height)

        glClearColor(0, 0, 0, 0)

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_STENCIL_TEST)

        glDisable(GL_CULL_FACE)

        glStencilOpSeparate(GL_BACK, GL_KEEP, GL_KEEP, GL_INCR_WRAP)
        glStencilOpSeparate(GL_FRONT, GL_KEEP, GL_KEEP, GL_DECR_WRAP)

        glUseProgram(self.shader)
        glBindVertexArray(self.vao)


    def render_end(self) -> None:
        glBindVertexArray(0)
        glUseProgram(0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)


    def render_slice(self, depth: float) -> tuple[np.ndarray, np.ndarray]:

        glClear(
            GL_COLOR_BUFFER_BIT |
            GL_DEPTH_BUFFER_BIT |
            GL_STENCIL_BUFFER_BIT
        )

        # draw

        proj = self.ortho(
            self.min_bound[0], self.max_bound[0], 
            self.min_bound[1], self.max_bound[1], 
            depth, self.max_bound[2]
        )

        glUniformMatrix4fv(self.u_locs["u_proj"], 1, GL_TRUE, proj)
        glDrawElements(GL_TRIANGLES, self.elem_count, GL_UNSIGNED_INT, None)

        # read and return buffers

        return self._read_buffers()
        

    def destroy(self):
        self._delete_framebuffer()
        self._delete_shader()
        self._delete_vertex_buffers()

        glfw.destroy_window(self.window)
        glfw.terminate()


def voxelize_gpu(mesh: TriangleMesh, voxel_size: float) -> np.ndarray:
    """
    Returns a dense grid (1 solid 0 air) of voxels from a triangle mesh.
    """

    mesh = mesh_to_tensor(mesh)

    if not mesh or mesh.is_empty():
        raise ValueError("Invalid mesh")

    min_bound = mesh.get_axis_aligned_bounding_box().min_bound.numpy()
    max_bound = mesh.get_axis_aligned_bounding_box().max_bound.numpy()
    extent = max_bound - min_bound

    renderer = Renderer()

    width = int(extent[0] / voxel_size) + 1
    height = int(extent[1] / voxel_size) + 1

    renderer.initialize(width, height)
    renderer.upload_model(min_bound, max_bound, mesh.vertex.positions.numpy(), mesh.triangle.indices.numpy())

    slices = []
    nslices = int(extent[2] / voxel_size) + 1

    renderer.render_begin()

    for i in range(nslices + 1):
        depth = max_bound[2] - i * voxel_size
        stencil, _ = renderer.render_slice(depth)
        slices.append(stencil)

    renderer.render_end()

    slices.reverse()

    voxel_grid = np.stack(slices, axis=0)[:, [2, 1, 0]]
    return np.where(voxel_grid != 0, 1, 0)