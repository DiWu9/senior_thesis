import time

import cv2
import numpy as np

import grid_fusion
import hash_fusion
import cProfile
import pstats
from pstats import SortKey


def one_frame_profiling():
    n_imgs = 1000
    cam_intr = np.loadtxt("../data/camera-intrinsics.txt", delimiter=' ')
    vol_bnds = np.zeros((3, 2))
    for i in range(n_imgs):
        depth_im = cv2.imread("../data/frame-%06d.depth.png" % (i), -1).astype(float)
        depth_im /= 1000.
        depth_im[depth_im == 65.535] = 0
        cam_pose = np.loadtxt("../data/frame-%06d.pose.txt" % (i))
        view_frust_pts = grid_fusion.get_view_frustum(depth_im, cam_intr, cam_pose)
        vol_bnds[:, 0] = np.minimum(vol_bnds[:, 0], np.amin(view_frust_pts, axis=1))
        vol_bnds[:, 1] = np.maximum(vol_bnds[:, 1], np.amax(view_frust_pts, axis=1))
    hash_table = hash_fusion.HashTable(vol_bnds, voxel_size=0.02)

    # fuse frame 0 for testing
    color_image = cv2.cvtColor(cv2.imread("../data/frame-%06d.color.jpg" % 0), cv2.COLOR_BGR2RGB)
    depth_im = cv2.imread("../data/frame-%06d.depth.png" % 0, -1).astype(float)
    depth_im /= 1000.
    depth_im[depth_im == 65.535] = 0
    cam_pose = np.loadtxt("../data/frame-%06d.pose.txt" % 0)
    hash_table.integrate(color_image, depth_im, cam_intr, cam_pose, obs_weight=1.)


def ten_frame_profiling():
    n_imgs = 1000
    cam_intr = np.loadtxt("../data/camera-intrinsics.txt", delimiter=' ')
    vol_bnds = np.zeros((3, 2))
    for i in range(n_imgs):
        depth_im = cv2.imread("../data/frame-%06d.depth.png" % (i), -1).astype(float)
        depth_im /= 1000.
        depth_im[depth_im == 65.535] = 0
        cam_pose = np.loadtxt("../data/frame-%06d.pose.txt" % (i))
        view_frust_pts = grid_fusion.get_view_frustum(depth_im, cam_intr, cam_pose)
        vol_bnds[:, 0] = np.minimum(vol_bnds[:, 0], np.amin(view_frust_pts, axis=1))
        vol_bnds[:, 1] = np.maximum(vol_bnds[:, 1], np.amax(view_frust_pts, axis=1))
    hash_table = hash_fusion.HashTable(vol_bnds, voxel_size=0.02)

    # Loop through the first 10 RGB-D images and fuse them together
    for i in range(10):
        color_image = cv2.cvtColor(cv2.imread("../data/frame-%06d.color.jpg" % (i)), cv2.COLOR_BGR2RGB)
        depth_im = cv2.imread("../data/frame-%06d.depth.png" % (i), -1).astype(float)
        depth_im /= 1000.
        depth_im[depth_im == 65.535] = 0
        cam_pose = np.loadtxt("../data/frame-%06d.pose.txt" % (i))
        hash_table.integrate(color_image, depth_im, cam_intr, cam_pose, obs_weight=1.)


def main():
    print("Estimating voxel volume bounds...")
    n_imgs = 1000
    cam_intr = np.loadtxt("../data/camera-intrinsics.txt", delimiter=' ')
    vol_bnds = np.zeros((3, 2))
    for i in range(n_imgs):
        # Read depth image and camera pose
        depth_im = cv2.imread("../data/frame-%06d.depth.png" % (i), -1).astype(float)
        depth_im /= 1000.  # depth is saved in 16-bit PNG in millimeters
        depth_im[depth_im == 65.535] = 0  # set invalid depth to 0 (specific to 7-scenes dataset)
        cam_pose = np.loadtxt("../data/frame-%06d.pose.txt" % (i))  # 4x4 rigid transformation matrix

        # Compute camera view frustum and extend convex hull
        view_frust_pts = grid_fusion.get_view_frustum(depth_im, cam_intr, cam_pose)
        vol_bnds[:, 0] = np.minimum(vol_bnds[:, 0], np.amin(view_frust_pts, axis=1))
        vol_bnds[:, 1] = np.maximum(vol_bnds[:, 1], np.amax(view_frust_pts, axis=1))

    print("Initializing hash table...")
    hash_table = hash_fusion.HashTable(vol_bnds, voxel_size=0.02)

    # Loop through RGB-D images and fuse them together
    t0_elapse = time.time()
    for i in range(n_imgs):
        print("Fusing frame %d/%d" % (i + 1, n_imgs))

        # Read RGB-D image and camera pose
        color_image = cv2.cvtColor(cv2.imread("../data/frame-%06d.color.jpg" % (i)), cv2.COLOR_BGR2RGB)
        depth_im = cv2.imread("../data/frame-%06d.depth.png" % (i), -1).astype(float)
        depth_im /= 1000.
        depth_im[depth_im == 65.535] = 0
        cam_pose = np.loadtxt("../data/frame-%06d.pose.txt" % (i))

        # Integrate observation into voxel volume (assume color aligned with depth)
        hash_table.integrate(color_image, depth_im, cam_intr, cam_pose, obs_weight=1.)

    fps = n_imgs / (time.time() - t0_elapse)
    print("Average FPS: {:.2f}".format(fps))

    # Get mesh from voxel volume and save to disk (can be viewed with Meshlab)
    print("Saving mesh to mesh.ply...")
    verts, faces, norms, colors = hash_table.get_mesh()
    grid_fusion.meshwrite("mesh_hash_demo1.ply", verts, faces, norms, colors)

    # Get point cloud from voxel volume and save to disk (can be viewed with Meshlab)
    print("Saving point cloud to pc.ply...")
    point_cloud = hash_table.get_point_cloud()
    grid_fusion.pcwrite("pc_hash_demo1.ply", point_cloud)


def profile_function_write_file(function_name, filename):
    cProfile.run(function_name, filename)


def read_profile_file(filename, top_n_functions):
    p = pstats.Stats(filename)
    p.sort_stats(SortKey.CUMULATIVE).print_stats(top_n_functions)


if __name__ == "__main__":
    # profile_function_write_file('one_frame_profiling()', 'stats_one_frame')
    # profile_function_write_file('ten_frame_profiling()', 'stats_ten_frame')
    read_profile_file('stats_one_frame', 20)
    read_profile_file('stats_ten_frame', 20)
    # main()
