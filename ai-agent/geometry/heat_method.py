"""
Surface Distance via the Heat Method

References:
    Crane, K., Weischedel, C., & Wardetzky, M. (2013). 
    Geodesics in heat: A new approach to computing distance based on heat flow. 
    ACM Transactions on Graphics (ToG), 32(5), 1-11.
"""

from dataclasses import dataclass
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import numba

from geometry.core import compute_cotan_laplacian

###############################################################################
# DATA STRUCTURES

@dataclass
class HeatMethodResult:
    distance: np.ndarray      # Final geodesic distance field (phi)
    heat_flow: np.ndarray     # Intermediate heat distribution (u)
    divergence: np.ndarray    # Integrated divergence of normalized vector field


###############################################################################
# NUMBA KERNELS

@numba.njit
def _compute_mass_matrix(vertices: np.ndarray, triangles: np.ndarray):
    """
    Computes the mass matrix diagonal.
    """
    
    n_vertices = vertices.shape[0]
    n_triangles = triangles.shape[0]
    
    mass_diag = np.zeros(n_vertices, dtype=np.float64)

    for t in range(n_triangles):
        i, j, k = triangles[t]

        cross_prod = np.cross(vertices[j] - vertices[i], vertices[k] - vertices[i])
        norm_cross = np.sqrt(np.sum(cross_prod**2))
        area = norm_cross / 6.0

        mass_diag[i] += area
        mass_diag[j] += area
        mass_diag[k] += area

    return mass_diag


@numba.njit
def _compute_integrated_divergence(vertices: np.ndarray, triangles: np.ndarray, u: np.ndarray) -> np.ndarray:
    """
    Computes divergence of the normalized heat gradient field per vertex.
    """

    n_vertices = vertices.shape[0]
    n_triangles = triangles.shape[0]
    div = np.zeros(n_vertices, dtype=np.float64)

    for t in range(n_triangles):
        i, j, k = triangles[t]
        p_i, p_j, p_k = vertices[i], vertices[j], vertices[k]

        e_i = p_k - p_j
        e_j = p_i - p_k
        e_k = p_j - p_i

        n = np.cross(p_j - p_i, p_k - p_i)
        double_area = np.sqrt(np.sum(n**2))
        if double_area < 1e-10:
            continue
            
        unit_n = n / double_area

        # local rescaling to avoid precision issues

        u_vals = np.abs(np.array([u[i], u[j], u[k]]))
        max_u = np.max(u_vals)
        if max_u > 1e-12:
            u_vals /= max_u

        # evaluate gradient field grad(u)

        grad_u = (u_vals[0] * np.cross(unit_n, e_i) + 
                  u_vals[1] * np.cross(unit_n, e_j) + 
                  u_vals[2] * np.cross(unit_n, e_k)) / double_area

        grad_norm = np.sqrt(np.sum(grad_u**2))
        X = np.zeros(3) if grad_norm < 1e-10 else grad_u / grad_norm

        n_cross_X = np.cross(unit_n, X)

        # integrated divergence

        div[i] += 0.5 * np.dot(e_i, n_cross_X)
        div[j] += 0.5 * np.dot(e_j, n_cross_X)
        div[k] += 0.5 * np.dot(e_k, n_cross_X)

    return div


###############################################################################
# HEAT METHOD SOLVER CLASS

class HeatMethodSolver:
    """
    Computes geodesic distance on 3D triangle meshes using the Heat Method.

    Re-uses factorized matrices across multiple distance queries on the same mesh.
    """

    def __init__(self, vertices: np.ndarray, triangles: np.ndarray):
        self.vertices = np.ascontiguousarray(vertices, dtype=np.float64)
        self.triangles = np.ascontiguousarray(triangles, dtype=np.int64)
        
        # 1. Build mesh discretization matrices
        self.mass_matrix, self.laplacian = self._build()
        
        # 2. Estimate heat diffusion timestep
        D = np.ptp(self.vertices, axis=0).max()

        self.h = self._compute_avg_edge_length()
        self.t = D * self.h

        # 3. Pre-factorize heat diffusion system (M + t*L)
        self._heat_solver = spla.factorized((self.mass_matrix + self.t * self.laplacian).tocsc())

    def _build(self) -> tuple[sp.csr_matrix, sp.csr_matrix]:
        M = sp.diags(_compute_mass_matrix(self.vertices, self.triangles), format='csr')
        L = compute_cotan_laplacian(self.vertices, self.triangles)
        return M, L

    def _compute_avg_edge_length(self) -> float:
        v0 = self.vertices[self.triangles[:, 0]]
        v1 = self.vertices[self.triangles[:, 1]]
        v2 = self.vertices[self.triangles[:, 2]]
        
        e0 = np.linalg.norm(v1 - v0, axis=1)
        e1 = np.linalg.norm(v2 - v1, axis=1)
        e2 = np.linalg.norm(v0 - v2, axis=1)
        return float(np.mean((e0 + e1 + e2) / 3.0))

    def compute_distance(self, sources: list[int]) -> HeatMethodResult:
        """
        Computes geodesic distances from a set of source vertex indices.
        """

        # Step 1: Heat diffusion solve (M + t*L) u = delta
        b = np.zeros(self.vertices.shape[0], dtype=np.float64)
        b[sources] = 1.0
        u = self._heat_solver(b)

        # Step 2: Integrated divergence calculation of normalized vector field X
        div = _compute_integrated_divergence(self.vertices, self.triangles, u)

        # Step 3: Poisson equation solve (L * phi = div)
        phi = spla.spsolve(self.laplacian.tocsc(), div)

        # Shift values relative to source & clamp values
        phi -= np.min(phi[sources])
        phi = np.maximum(phi, 0.0)

        return HeatMethodResult(
            distance=phi,
            heat_flow=u,
            divergence=div
        )
    

###############################################################################
# FUNCTIONAL WRAPPER

def compute_geodesic_distance(
    vertices: np.ndarray, 
    triangles: np.ndarray, 
    sources: list[int]
) -> HeatMethodResult:
    """
    Convenience functional interface for one-off distance computations.
    """
    solver = HeatMethodSolver(vertices, triangles)
    return solver.compute_distance(sources)