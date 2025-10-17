import tempfile
import os
from t2m import T2MGenerator, T2MConfig

# Singleton pattern for generator instance
class T2MService:
    _generator = None

    @classmethod
    def get_generator(cls):
        if cls._generator is None:
            config = T2MConfig(
                vqvae_path='T2M-GPT-main/pretrained/VQVAE/net_last.pth',
                transformer_path='T2M-GPT-main/pretrained/VQTransformer_corruption05/net_best_fid.pth',
                meta_path='T2M-GPT-main/checkpoints/t2m/VQVAEV3_CB1024_CMT_H1024_NRES3/meta/'
            )
            cls._generator = T2MGenerator(config)
        return cls._generator

def generate_bvh_from_text(text: str) -> str:
    """
    Generate a BVH file from a text description and return the file path.
    The caller is responsible for deleting the file.
    """
    generator = T2MService.get_generator()
    motion_xyz = generator.generate_motion(text)
    # with tempfile.NamedTemporaryFile(delete=False, suffix=".bvh") as tmp:
    #     bvh_path = tmp.name
    bvh_path = "test.bvh"
    generator.motion_to_bvh(motion_xyz, bvh_path)
    return bvh_path

def test_generate_bvh(save = True):
    """
    Example test for BVH generation.
    """
    test_text = "A person is running like zombie"
    bvh_path = generate_bvh_from_text(test_text)
    print(os.getcwd())
    try:
        assert os.path.exists(bvh_path), "BVH file was not created."
        with open(bvh_path, "r") as f:
            content = f.read()
            assert "HIERARCHY" in content and "MOTION" in content, "BVH file missing expected sections."
        print("Test passed: BVH file generated and contains expected content.")
        print(f"BVH file saved to {bvh_path}")
    finally:
        if os.path.exists(bvh_path) and not save:
            os.remove(bvh_path)

if __name__ == "__main__":
    test_generate_bvh()
