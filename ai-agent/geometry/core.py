import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import numba

@numba.njit
def _compute_cotan_laplacian_kernel(vertices: np.ndarray, triangles: np.ndarray):
    """
    Computes the Cotan Laplacian matrix for a given mesh.
    Returns the numpy arrays for the rows, columns, and data of the COO matrix.
    """

    n_vertices = vertices.shape[0]
    n_triangles = triangles.shape[0]
    
    rows = np.zeros(n_triangles * 15, dtype=np.int64)
    cols = np.zeros(n_triangles * 15, dtype=np.int64)
    data = np.zeros(n_triangles * 15, dtype=np.float64)

    ptr = 0

    for t in range(n_triangles):
        i, j, k = triangles[t]

        # cotangent

        edges = ((j, k, i), (i, k, j), (i, j, k))

        for idx in range(3):
            v0, v1, v2 = edges[idx]
            u = vertices[v0] - vertices[v2]
            v = vertices[v1] - vertices[v2]
            
            cp = np.cross(u, v)
            norm_cp = np.sqrt(np.sum(cp**2))
            
            cotan = 0.0 if norm_cp < 1e-10 else np.dot(u, v) / norm_cp

            rows[ptr] = v0; cols[ptr] = v1; data[ptr] = -0.5 * cotan; ptr += 1
            rows[ptr] = v1; cols[ptr] = v0; data[ptr] = -0.5 * cotan; ptr += 1
            rows[ptr] = v0; cols[ptr] = v0; data[ptr] =  0.5 * cotan; ptr += 1
            rows[ptr] = v1; cols[ptr] = v1; data[ptr] =  0.5 * cotan; ptr += 1

        # regularization

        rows[ptr] = i; cols[ptr] = i; data[ptr] = 1e-8; ptr += 1
        rows[ptr] = j; cols[ptr] = j; data[ptr] = 1e-8; ptr += 1
        rows[ptr] = k; cols[ptr] = k; data[ptr] = 1e-8; ptr += 1

    return rows, cols, data


def compute_cotan_laplacian(vertices: np.ndarray, triangles: np.ndarray) -> sp.csr_matrix:
    """
    Computes the Cotan Laplacian matrix for a given mesh.
    """
    rows, cols, data = _compute_cotan_laplacian_kernel(vertices, triangles)
    return sp.csr_matrix((data, (rows, cols)), shape=(vertices.shape[0], vertices.shape[0]))