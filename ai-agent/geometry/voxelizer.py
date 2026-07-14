import glfw
import numpy as np
from OpenGL.GL import *

################################################################################
# SHADERS

VERTEX_SHADER_SOURCE = \
r"""
#version 330 core
layout(location = 0) in vec3 vertex;
uniform mat4 u_proj;
void main()
{
    gl_Position = u_proj * vec4(vertex, 1.0);
}
"""

FRAGMENT_SHADER_SOURCE = \
r"""
#version 330 core
out vec4 frag_color;
void main() {
    frag_color = vec4(1.0, 0.0, 0.0, 1.0);
}
"""


#################################################################################
# HELPER FUNCTIONS

def ortho(l: float, r: float, b: float, t: float, n: float, f: float) -> np.ndarray:
    """
    Computes an orthographic projection matrix.
    """
    m = np.zeros((4,4), dtype=np.float32)

    m[0,0] = 2.0 / (r - l)
    m[1,1] = 2.0 / (t - b)
    m[2,2] = 2.0 / (f - n)
    m[3,3] = 1.0

    m[0,3] = -(r + l) / (r - l)
    m[1,3] = -(t + b) / (t - b)
    m[2,3] = -(f + n) / (f - n)

    return m

################################################################################
# MESH SLICE RENDERER

class MeshSliceRenderer:
    """
    Off-screen OpenGL renderer tightly coupled to a single mesh for obtaining 
    stencil occupancy slices and optional color slices.
    """

    def __init__(
        self, 
        vertices: np.ndarray, 
        triangles: np.ndarray, 
        voxel_size: float, 
        render_color: bool = False
    ) -> None:
        self.vertices = np.ascontiguousarray(vertices, dtype=np.float32)
        self.triangles = np.ascontiguousarray(triangles, dtype=np.uint32)
        self.voxel_size = voxel_size
        self.render_color = render_color
        
        self.min_bound = np.min(self.vertices, axis=0)
        self.max_bound = np.max(self.vertices, axis=0)
        extent = self.max_bound - self.min_bound
        
        self.width = int(extent[0] / self.voxel_size) + 1
        self.height = int(extent[1] / self.voxel_size) + 1
        self.nslices = int(extent[2] / self.voxel_size) + 1
        
        self.window = None
        self.fbo = None
        self.color = None
        self.stencil = None
        self.shader = None
        self.u_proj_loc = None
        self.vbo = None
        self.ebo = None
        self.vao = None
        self.elem_count = self.triangles.size
        
        self._initialize_context()
        self._create_framebuffer()
        self._create_shader()
        self._upload_model()

    def _initialize_context(self) -> None:
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

    def _create_framebuffer(self) -> None:
        self.color = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.color)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        
        self.stencil = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, self.stencil)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, self.width, self.height)
        
        self.fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.color, 0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, self.stencil)

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Error creating framebuffer")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
  
    def _create_shader(self) -> None:
        def compile_shader(shader_source: str, shader_type: int) -> int:
            shader = glCreateShader(shader_type)
            glShaderSource(shader, shader_source)
            glCompileShader(shader)
            if not glGetShaderiv(shader, GL_COMPILE_STATUS):
                raise RuntimeError(glGetShaderInfoLog(shader))
            return shader

        v_shader = compile_shader(VERTEX_SHADER_SOURCE, GL_VERTEX_SHADER)
        f_shader = compile_shader(FRAGMENT_SHADER_SOURCE, GL_FRAGMENT_SHADER)

        self.shader = glCreateProgram()
        glAttachShader(self.shader, v_shader)
        glAttachShader(self.shader, f_shader)
        glLinkProgram(self.shader)

        if not glGetProgramiv(self.shader, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(self.shader))
        
        self.u_proj_loc = glGetUniformLocation(self.shader, "u_proj")

        glDeleteShader(v_shader)
        glDeleteShader(f_shader)

    def _upload_model(self) -> None:
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)
        
        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.triangles.nbytes, self.triangles, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glBindVertexArray(0)

    def render_slices(self) -> tuple[list[np.ndarray], list[np.ndarray]]:
        """
        Executes the rendering loop over the Z-axis bounds and returns the captured 
        slices as lists of NumPy arrays.
        """
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

        stencils = []
        colors = []

        for i in range(self.nslices + 1):
            depth = self.max_bound[2] - i * self.voxel_size
            
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

            proj = ortho(
                self.min_bound[0] - 1e-6, self.max_bound[0] + 1e-6, 
                self.min_bound[1] - 1e-6, self.max_bound[1] + 1e-6, 
                depth, self.max_bound[2] + 1e-6
            )

            glUniformMatrix4fv(self.u_proj_loc, 1, GL_TRUE, proj)
            glDrawElements(GL_TRIANGLES, self.elem_count, GL_UNSIGNED_INT, None)

            # read stencil
            stencil = glReadPixels(0, 0, self.width, self.height, GL_STENCIL_INDEX, GL_UNSIGNED_BYTE)
            stencils.append(np.frombuffer(stencil, dtype=np.uint8).reshape(self.height, self.width))

            # read color if enabled
            if self.render_color:
                color = glReadPixels(0, 0, self.width, self.height, GL_RGBA, GL_UNSIGNED_BYTE)
                colors.append(np.frombuffer(color, dtype=np.uint8).reshape(self.height, self.width, 4))

        glBindVertexArray(0)
        glUseProgram(0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        return stencils, colors

    def destroy(self) -> None:
        """
        Frees OpenGL and GLFW resources associated with the renderer instance.
        """
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        if self.fbo is not None: glDeleteFramebuffers(1, [self.fbo])
        if self.stencil is not None: glDeleteRenderbuffers(1, [self.stencil])
        if self.color is not None: glDeleteTextures(1, [self.color])
        
        glUseProgram(0)
        if self.shader is not None: glDeleteProgram(self.shader)
        
        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        if self.vbo is not None: glDeleteBuffers(1, [self.vbo])
        if self.ebo is not None: glDeleteBuffers(1, [self.ebo])
        if self.vao is not None: glDeleteVertexArrays(1, [self.vao])

        glfw.destroy_window(self.window)
        glfw.terminate()


################################################################################
# VOXELIZATION WRAPPER

def voxelize_mesh(
    vertices: np.ndarray, 
    triangles: np.ndarray, 
    voxel_size: float,
    render_color: bool = False
) -> tuple[np.ndarray, np.ndarray]:
    """
    Instantiates a renderer to slice a given mesh and assembles a dense binary 
    voxel grid representation.
    """
    renderer = MeshSliceRenderer(vertices, triangles, voxel_size, render_color)
    origin = renderer.min_bound.copy()
    
    stencils, _ = renderer.render_slices()
    renderer.destroy()

    stencils.reverse()

    voxel_grid_zyx = np.stack(stencils, axis=0)
    voxel_grid_xyz = np.transpose(voxel_grid_zyx, (2, 1, 0))
    
    voxel_grid = np.where(voxel_grid_xyz != 0, 1, 0).astype(np.uint8)

    return voxel_grid, origin