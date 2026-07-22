import copy
import numpy as np
import open3d as o3d


################################################################################
# Make fragments

def load_fragment_from_ply(ply_path, voxel_size=0.01):
    """
    Load a PLY file, downsample it, and calculate normals.
    """
    pcd = o3d.io.read_point_cloud(ply_path)
    pcd = pcd.voxel_down_sample(voxel_size)
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(
            radius=voxel_size * 2, max_nn=30
        )
    )
    return pcd


def make_fragment_with_poses(rgbd_images, intrinsic, voxel_size=0.01):
    """
    Tracks camera pose across a sequence of RGB-D images using Odometry.
    """
    volume = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=voxel_size,
        sdf_trunc=0.04,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
    )

    current_pose = np.identity(4)
    local_poses = [current_pose.copy()]
    volume.integrate(rgbd_images[0], intrinsic, np.linalg.inv(current_pose))

    for i in range(1, len(rgbd_images)):
        option = o3d.pipelines.odometry.OdometryOption()
        success, trans, _ = o3d.pipelines.odometry.compute_rgbd_odometry(
            rgbd_images[i - 1],
            rgbd_images[i],
            intrinsic,
            np.identity(4),
            o3d.pipelines.odometry.RGBDOdometryJacobianFromHybridTerm(),
            option,
        )

        if success:
            current_pose = current_pose @ trans
            local_poses.append(current_pose.copy())
            volume.integrate(rgbd_images[i], intrinsic, np.linalg.inv(current_pose))
        else:
            local_poses.append(current_pose.copy())

    fragment_pcd = volume.extract_point_cloud()
    return fragment_pcd, local_poses


################################################################################
# Register fragments

def register_fragments(source_pcd, target_pcd, voxel_size=0.01):
    """
    Aligns two fragments using FPFH + RANSAC and Point-to-Plane ICP.
    """
    source_pcd.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30)
    )
    target_pcd.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30)
    )

    source_down = source_pcd.voxel_down_sample(voxel_size)
    target_down = target_pcd.voxel_down_sample(voxel_size)

    source_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        source_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5, max_nn=100),
    )
    target_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        target_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5, max_nn=100),
    )

    distance_threshold = voxel_size * 1.5
    ransac_result = (
        o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
            source_down,
            target_down,
            source_fpfh,
            target_fpfh,
            mutual_filter=False,
            max_correspondence_distance=distance_threshold,
            estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(
                False
            ),
            ransac_n=3,
            checkers=[
                o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(
                    distance_threshold
                )
            ],
            criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(
                100000, 0.999
            ),
        )
    )

    if ransac_result.fitness < 0.10:
        return None, None, 0.0, float('inf')

    icp_threshold = voxel_size * 0.4
    icp_result = o3d.pipelines.registration.registration_icp(
        source_pcd,
        target_pcd,
        icp_threshold,
        ransac_result.transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
    )

    info_matrix = (
        o3d.pipelines.registration.get_information_matrix_from_point_clouds(
            source_pcd, target_pcd, icp_threshold, icp_result.transformation
        )
    )

    return (
        icp_result.transformation,
        info_matrix,
        icp_result.fitness,
        icp_result.inlier_rmse,
    )


def build_pose_graph(
    fragments, voxel_size=0.01, min_fitness=0.35, max_rmse=None
):
    """
    Constructs the pose graph for the fragments.
    """
    if max_rmse is None:
        max_rmse = voxel_size * 0.5

    pose_graph = o3d.pipelines.registration.PoseGraph()
    for _ in fragments:
        pose_graph.nodes.append(
            o3d.pipelines.registration.PoseGraphNode(np.identity(4))
        )

    num_fragments = len(fragments)

    for i in range(num_fragments):
        for j in range(i + 1, num_fragments):
            is_adjacent = j == i + 1

            transformation, info_matrix, fitness, rmse = register_fragments(
                fragments[i], fragments[j], voxel_size=voxel_size
            )

            if (
                transformation is None
                or fitness < min_fitness
                or rmse > float(max_rmse)
            ):
                continue

            is_high_confidence = is_adjacent and (fitness > 0.6)

            edge = o3d.pipelines.registration.PoseGraphEdge(
                i,
                j,
                transformation,
                info_matrix,
                uncertain=not is_high_confidence,
            )
            pose_graph.edges.append(edge)

    return pose_graph


################################################################################
# Refine registration

def optimize_pose_graph(pose_graph, max_correspondence_distance=0.03):
    """
    Optimizes the global pose graph to eliminate drift.
    """
    option = o3d.pipelines.registration.GlobalOptimizationOption(
        max_correspondence_distance=max_correspondence_distance,
        edge_prune_threshold=0.25,
        preference_loop_closure=2.0,
        reference_node=0,
    )

    o3d.pipelines.registration.global_optimization(
        pose_graph,
        method=o3d.pipelines.registration.GlobalOptimizationLevenbergMarquardt(),
        criteria=o3d.pipelines.registration.GlobalOptimizationConvergenceCriteria(),
        option=option,
    )
    return pose_graph


################################################################################
# Integrate scene

def integrate_scene_from_fragments(fragments, pose_graph, voxel_size=0.005):
    """
    Transforms point clouds by their optimized poses, merges them, and creates a
    surface mesh using Poisson Surface Reconstruction.
    """
    merged_pcd = o3d.geometry.PointCloud()

    for i, pcd in enumerate(fragments):
        pose = pose_graph.nodes[i].pose
        pcd_transformed = copy.deepcopy(pcd).transform(pose)
        merged_pcd += pcd_transformed

    merged_pcd = merged_pcd.voxel_down_sample(voxel_size)
    merged_pcd.orient_normals_consistent_tangent_plane(k=15)

    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        merged_pcd, depth=9
    )

    vertices_to_remove = densities < np.quantile(densities, 0.01)
    mesh.remove_vertices_by_mask(vertices_to_remove)

    return mesh, merged_pcd


def integrate_scene_rgbd_images(
    all_rgbd_images, global_frame_poses, intrinsic, voxel_size=0.01
):
    """
    Integrates all RGB-D frames using their final global poses into a mesh.
    """
    volume = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=voxel_size,
        sdf_trunc=0.04,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
    )

    for rgbd, pose in zip(all_rgbd_images, global_frame_poses):
        volume.integrate(rgbd, intrinsic, np.linalg.inv(pose))

    mesh = volume.extract_triangle_mesh()
    mesh.compute_vertex_normals()
    return mesh


################################################################################
# Pipelines

def rgbd_reconstruction_pipeline(all_rgbd_images, intrinsic, fragment_size=100, voxel_size=0.01):
    """
    Reconstructs a scene from a sequence of RGB-D images.
    """

    fragments = []
    local_poses_per_fragment = []

    chunks = [
        all_rgbd_images[i : i + fragment_size]
        for i in range(0, len(all_rgbd_images), fragment_size)
    ]

    for chunk in chunks:
        pcd, local_poses = make_fragment_with_poses(
            chunk, intrinsic, voxel_size=voxel_size
        )
        fragments.append(pcd)
        local_poses_per_fragment.append(local_poses)

    pose_graph = build_pose_graph(fragments, voxel_size=voxel_size * 2)

    optimized_pose_graph = optimize_pose_graph(
        pose_graph, max_correspondence_distance=voxel_size * 2
    )

    global_frame_poses = []
    for i, local_poses in enumerate(local_poses_per_fragment):
        fragment_global_pose = optimized_pose_graph.nodes[i].pose
        for local_pose in local_poses:
            global_pose = fragment_global_pose @ local_pose
            global_frame_poses.append(global_pose)

    final_mesh = integrate_scene_rgbd_images(
        all_rgbd_images, global_frame_poses, intrinsic, voxel_size=voxel_size
    )

    return final_mesh


def ply_reconstruction_pipeline(ply_paths, voxel_size=0.01):
    """
    Reconstructs a scene from a sequence of PLY files.
    """
    
    fragments = [
        load_fragment_from_ply(path, voxel_size=voxel_size) for path in ply_paths
    ]

    pose_graph = build_pose_graph(fragments, voxel_size=voxel_size * 2)

    optimized_pose_graph = optimize_pose_graph(
        pose_graph, max_correspondence_distance=voxel_size * 2
    )

    final_mesh, merged_pcd = integrate_scene_from_fragments(
        fragments, optimized_pose_graph, voxel_size=voxel_size
    )

    return final_mesh, merged_pcd