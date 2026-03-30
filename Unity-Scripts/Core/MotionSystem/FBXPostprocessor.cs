using UnityEditor;
using UnityEngine;

public class FBXPostprocessor : AssetPostprocessor
{
    void OnPreprocessModel()
    {
        var importer = assetImporter as ModelImporter;
        if (importer == null) return;
        if (!assetPath.EndsWith(".fbx")) return;

        Debug.Log("Processing FBX file: " + assetPath);

        // Set animation type to Humanoid
        importer.animationType = ModelImporterAnimationType.Human;

        // Configure avatar setup
        importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;

        Debug.Log("Animation type set to Humanoid for: " + assetPath);
    }
}
