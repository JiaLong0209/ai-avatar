import numpy as np
from scipy.spatial.transform import Rotation as R
import torch

# --- 1. 定義 HumanML3D 的 22 關節結構 ---
# 這是 Light-T2M / MDM / T2M-GPT 通用的標準骨架
# Joint Names
JOINT_NAMES = [
    'pelvis', 'left_hip', 'right_hip', 'spine1', 'left_knee', 'right_knee', 
    'spine2', 'left_ankle', 'right_ankle', 'spine3', 'left_foot', 'right_foot', 
    'neck', 'left_collar', 'right_collar', 'head', 'left_shoulder', 'right_shoulder', 
    'left_elbow', 'right_elbow', 'left_wrist', 'right_wrist'
]

# Parent Indices (-1 表示 Root)
PARENTS = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]

# 標準 T-Pose 的 Offset (參考 HumanML3D)
# 格式: (X, Y, Z)
OFFSETS = np.array([
    [0, 0, 0],       # 0: pelvis
    [0.1, -0.1, 0],  # 1: left_hip (approx)
    [-0.1, -0.1, 0], # 2: right_hip
    [0, 0.2, 0],     # 3: spine1
    [0, -0.4, 0],    # 4: left_knee
    [0, -0.4, 0],    # 5: right_knee
    [0, 0.2, 0],     # 6: spine2
    [0, -0.4, 0],    # 7: left_ankle
    [0, -0.4, 0],    # 8: right_ankle
    [0, 0.2, 0],     # 9: spine3
    [0, -0.1, 0.1],  # 10: left_foot
    [0, -0.1, 0.1],  # 11: right_foot
    [0, 0.1, 0],     # 12: neck
    [0.1, 0.1, 0],   # 13: left_collar
    [-0.1, 0.1, 0],  # 14: right_collar
    [0, 0.2, 0],     # 15: head
    [0.2, 0, 0],     # 16: left_shoulder
    [-0.2, 0, 0],    # 17: right_shoulder
    [0.3, 0, 0],     # 18: left_elbow
    [-0.3, 0, 0],    # 19: right_elbow
    [0.25, 0, 0],    # 20: left_wrist
    [-0.25, 0, 0]    # 21: right_wrist
])

def save_bvh_from_xyz(xyz_tensor, filename, fps=20):
    """
    將 (Seq, Joints, 3) 的 XYZ 座標轉換並存檔為 BVH
    :param xyz_tensor: numpy array or torch tensor, shape (F, 22, 3)
    :param filename: 輸出檔名
    :param fps: 幀率
    """
    if torch.is_tensor(xyz_tensor):
        xyz = xyz_tensor.detach().cpu().numpy()
    else:
        xyz = xyz_tensor

    n_frames, n_joints, _ = xyz.shape
    
    # 用於儲存每一幀的 Root 位置與所有關節的歐拉角
    # Channel 順序通常是: Xpos Ypos Zpos Zrot Xrot Yrot (Root)
    # 其他關節: Zrot Xrot Yrot
    motion_data = []

    # 1. 寫入 BVH Header
    with open(filename, 'w') as f:
        f.write("HIERARCHY\n")
        
        # 遞迴寫入 Joint 定義
        def write_joint(idx, indent):
            offset = OFFSETS[idx]
            name = JOINT_NAMES[idx]
            indent_str = "\t" * indent
            
            if idx == 0:
                f.write(f"{indent_str}ROOT {name}\n")
            else:
                f.write(f"{indent_str}JOINT {name}\n")
            
            f.write(f"{indent_str}{{\n")
            f.write(f"{indent_str}\tOFFSET {offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}\n")
            
            if idx == 0:
                f.write(f"{indent_str}\tCHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation\n")
            else:
                f.write(f"{indent_str}\tCHANNELS 3 Zrotation Xrotation Yrotation\n")
            
            # 找所有以此關節為父節點的子節點
            children = [i for i, p in enumerate(PARENTS) if p == idx]
            
            if len(children) > 0:
                for child_idx in children:
                    write_joint(child_idx, indent + 1)
            else:
                # End Site (末端)
                f.write(f"{indent_str}\tEnd Site\n")
                f.write(f"{indent_str}\t{{\n")
                f.write(f"{indent_str}\t\tOFFSET 0 0 0\n")
                f.write(f"{indent_str}\t}}\n")
                
            f.write(f"{indent_str}}}\n")

        write_joint(0, 0)
        
        f.write("MOTION\n")
        f.write(f"Frames: {n_frames}\n")
        f.write(f"Frame Time: {1.0/fps:.6f}\n")

        # 2. 計算 Motion Data (Analytical IK)
        for frame_idx in range(n_frames):
            frame_xyz = xyz[frame_idx] # (22, 3)
            root_pos = frame_xyz[0]
            
            # 這一行的數據: RootPos(3) + 22 * Euler(3)
            row_data = [root_pos[0], root_pos[1], root_pos[2]]
            
            # 用於儲存 Global Rotation 以便計算子節點的 Local Rotation
            # 初始化所有關節的 Global Rotation 為 Identity
            global_rots = [R.identity() for _ in range(n_joints)]
            
            for j in range(n_joints):
                # 找出子節點來計算當前骨骼的方向
                children = [i for i, p in enumerate(PARENTS) if p == j]
                
                if len(children) == 0:
                    # 末端節點，通常沿用父節點的旋轉或設為 0
                    # 為了簡單，我們填 0 (這不會影響視覺，因為沒有子骨骼了)
                    row_data.extend([0, 0, 0])
                    continue
                
                # 取第一個子節點作為主要方向 (Main Axis)
                child_idx = children[0]
                
                # A. 骨骼在世界座標的向量 (Current Bone Vector)
                curr_vec = frame_xyz[child_idx] - frame_xyz[j]
                curr_vec = curr_vec / (np.linalg.norm(curr_vec) + 1e-8)
                
                # B. 骨骼在 T-Pose (Rest) 的向量 (Rest Bone Vector)
                # 注意：這裡要算 Global 的 Rest 向量，比較麻煩
                # 簡化版：假設 T-Pose 父子 Offset 就是 Rest Vector
                rest_vec = OFFSETS[child_idx]
                rest_vec = rest_vec / (np.linalg.norm(rest_vec) + 1e-8)
                
                # C. 計算這兩個向量之間的旋轉 (這是 Global Rotation 的近似)
                # 找出把 rest_vec 轉到 curr_vec 的旋轉矩陣
                if np.allclose(curr_vec, rest_vec):
                    rot_val = R.identity()
                else:
                    cross = np.cross(rest_vec, curr_vec)
                    dot = np.dot(rest_vec, curr_vec)
                    angle = np.arccos(np.clip(dot, -1.0, 1.0))
                    if np.linalg.norm(cross) < 1e-6:
                         rot_val = R.identity() # 180度或0度處理需更細緻，這邊先略過
                    else:
                        axis = cross / np.linalg.norm(cross)
                        rot_val = R.from_rotvec(axis * angle)
                
                # 保存 Global
                global_rots[j] = rot_val
                
                # D. 轉成 Local Rotation
                # Local = Parent_Global_Inverse * Current_Global
                parent_idx = PARENTS[j]
                if parent_idx == -1:
                    local_rot = rot_val
                else:
                    parent_global = global_rots[parent_idx]
                    local_rot = parent_global.inv() * rot_val
                
                # E. 轉成 Euler (ZXY 通常是 BVH 常用的旋轉順序)
                euler = local_rot.as_euler('ZXY', degrees=True)
                row_data.extend(euler)
            
            # 寫入檔案
            f.write(" ".join([f"{x:.6f}" for x in row_data]) + "\n")
            
    print(f"BVH saved to {filename}")