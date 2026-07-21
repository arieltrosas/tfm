import numpy as np
import open3d as o3d
import scipy.sparse as sp
import numba

from geometry.types import TriangleMesh, mesh_to_legacy


# ==============================================================================
# 1. NUMBA KERNELS
# ==============================================================================

@numba.njit
def _compute_mass_matrix_kernel(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """
    Computes the barycentric dual area (1/3 of triangle areas) for each vertex.
    """
    n_vertices = vertices.shape[0]
    n_triangles = triangles.shape[0]

    mass_diag = np.zeros(n_vertices, dtype=np.float64)

    for t in range(n_triangles):
        i, j, k = triangles[t]

        cross_prod = np.cross(vertices[j] - vertices[i], vertices[k] - vertices[i])
        norm_cross = np.sqrt(np.sum(cross_prod**2))
        area = norm_cross / 6.0  # 1/3 of (0.5 * norm_cross)

        mass_diag[i] += area
        mass_diag[j] += area
        mass_diag[k] += area

    return mass_diag


@numba.njit
def _compute_cotan_laplacian_kernel(vertices: np.ndarray, triangles: np.ndarray):
    """
    Computes the COO matrix components for the Cotan Laplacian stiffness matrix (L).
    """
    n_triangles = triangles.shape[0]

    rows = np.zeros(n_triangles * 15, dtype=np.int64)
    cols = np.zeros(n_triangles * 15, dtype=np.int64)
    data = np.zeros(n_triangles * 15, dtype=np.float64)

    ptr = 0

    for t in range(n_triangles):
        i, j, k = triangles[t]
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

        # Small diagonal regularization
        rows[ptr] = i; cols[ptr] = i; data[ptr] = 1e-8; ptr += 1
        rows[ptr] = j; cols[ptr] = j; data[ptr] = 1e-8; ptr += 1
        rows[ptr] = k; cols[ptr] = k; data[ptr] = 1e-8; ptr += 1

    return rows, cols, data


@numba.njit
def _compute_angle_defect_kernel(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """
    Computes the angle defect (2*pi - sum(interior_angles)) at each vertex.
    """
    n_vertices = vertices.shape[0]
    n_triangles = triangles.shape[0]

    angle_sum = np.zeros(n_vertices, dtype=np.float64)

    for t in range(n_triangles):
        i, j, k = triangles[t]

        # Angle at i

        u_i = vertices[j] - vertices[i]
        v_i = vertices[k] - vertices[i]

        norm_u_i = np.sqrt(np.sum(u_i**2))
        norm_v_i = np.sqrt(np.sum(v_i**2))

        if norm_u_i > 1e-10 and norm_v_i > 1e-10:
            cos_i = max(-1.0, min(1.0, np.dot(u_i, v_i) / (norm_u_i * norm_v_i)))
            angle_sum[i] += np.arccos(cos_i)

        # Angle at j

        u_j = vertices[i] - vertices[j]
        v_j = vertices[k] - vertices[j]

        norm_u_j = np.sqrt(np.sum(u_j**2))
        norm_v_j = np.sqrt(np.sum(v_j**2))

        if norm_u_j > 1e-10 and norm_v_j > 1e-10:
            cos_j = max(-1.0, min(1.0, np.dot(u_j, v_j) / (norm_u_j * norm_v_j)))
            angle_sum[j] += np.arccos(cos_j)

        # Angle at k

        u_k = vertices[i] - vertices[k]
        v_k = vertices[j] - vertices[k]
        
        norm_u_k = np.sqrt(np.sum(u_k**2))
        norm_v_k = np.sqrt(np.sum(v_k**2))

        if norm_u_k > 1e-10 and norm_v_k > 1e-10:
            cos_k = max(-1.0, min(1.0, np.dot(u_k, v_k) / (norm_u_k * norm_v_k)))
            angle_sum[k] += np.arccos(cos_k)

    return (2.0 * np.pi) - angle_sum


# ==============================================================================
# 2. EXPOSED CORE FUNCTIONS
# ==============================================================================

def compute_mass_matrix(vertices: np.ndarray, triangles: np.ndarray) -> sp.csr_matrix:
    """
    Computes the diagonal mass matrix for a mesh.
    """
    diag = _compute_mass_matrix_kernel(vertices, triangles)
    return sp.diags(diag, format="csr")


def compute_cotan_laplacian(vertices: np.ndarray, triangles: np.ndarray) -> sp.csr_matrix:
    """
    Computes the discrete Cotan Laplacian matrix.
    """
    rows, cols, data = _compute_cotan_laplacian_kernel(vertices, triangles)
    n = vertices.shape[0]
    return sp.csr_matrix((data, (rows, cols)), shape=(n, n))


def compute_angle_defect(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """
    Computes the raw angle defect (2*pi - sum(interior_angles)) per vertex.
    """
    return _compute_angle_defect_kernel(vertices, triangles)


# ==============================================================================
# CAVITY DETECTION
# ==============================================================================

def cluster_cavities(
    mesh: TriangleMesh,
    percentile: float = 5.0,
    min_points: int = 5,
) -> list[np.ndarray]:
    """
    Cluster negatively curved (dent/cavity-like) regions using mean curvature.
    """
    mesh = mesh_to_legacy(mesh)

    if mesh.is_empty():
        raise ValueError("Mesh geometry is empty")

    mesh.compute_vertex_normals()

    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    triangles = np.asarray(mesh.triangles, dtype=np.int64)
    normals = np.asarray(mesh.vertex_normals, dtype=np.float64)

    L = compute_cotan_laplacian(vertices, triangles)
    M = compute_mass_matrix(vertices, triangles)
    D = compute_angle_defect(vertices, triangles)

    M_inv = 1.0 / np.maximum(M.diagonal(), 1e-12)
    S = np.vecdot(normals, M_inv[:, None] * (L @ vertices))
    # K = D * M_inv

    threshold_S = np.percentile(S, percentile)
    # threshold_K = np.percentile(K, percentile)

    mask = (S < threshold_S) # & (K < threshold_K)
    indices = np.where(mask)[0]

    if len(indices) == 0:
        return []

    points = vertices[mask]

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(vertices)
    avg_spacing = float(np.mean(pcd.compute_nearest_neighbor_distance()))
    eps_distance = 3.0 * avg_spacing

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)

    labels = np.array(
        pcd.cluster_dbscan(
            eps=eps_distance,
            min_points=min_points,
            print_progress=False,
        )
    )

    valid_labels = np.unique(labels[labels >= 0])

    clusters: list[np.ndarray] = []
    for cluster_id in valid_labels:
        cluster_members = indices[labels == cluster_id]
        clusters.append(cluster_members)

    return clusters