# Motion System Setup Guide

## Quick Setup (Easiest Method)

### Method 1: Using Unity Menu (Recommended for Beginners)

1. **Open Unity Editor**
2. **Go to menu**: `Tools` → `Motion System` → `Setup MotionPlayback`
3. The script will automatically:
   - Create MotionManager if it doesn't exist
   - Find or create a GameObject with MotionPlayback
   - Try to find an Animator component (your character/avatar)
   - Set everything up automatically

### Method 2: Right-Click on GameObject

1. **Select your character/avatar GameObject** in the Hierarchy
2. **Right-click** on it
3. **Choose**: `GameObject` → `Motion System` → `Add MotionPlayback`
4. MotionPlayback will be added to that GameObject

---

## Manual Setup (Step by Step)

### Step 1: Add MotionManager

1. In Unity Hierarchy, **right-click** → `Create Empty`
2. Name it `MotionManager`
3. **Add Component** → Search for `MotionManager`
4. The MotionManager will persist across scenes (DontDestroyOnLoad)

### Step 2: Add MotionPlayback

**Option A: Add to Existing Character/Avatar (Recommended)**

1. **Select your character/avatar GameObject** (the one with Animator component)
2. **Add Component** → Search for `MotionPlayback`
3. In the Inspector, you'll see:
   - **Animation Target**: Drag your Animator here (or leave empty to auto-find)
   - **Register With Manager**: ✅ (checked by default)
   - **Is Primary**: ✅ (check this if it's your main character)

**Option B: Create New GameObject**

1. **Right-click** in Hierarchy → `Create Empty`
2. Name it `MotionPlayback`
3. **Add Component** → `MotionPlayback`
4. **Add Component** → `Animator` (or drag a GameObject with Animator to the Target Animator field)

---

## What You Need

### Required Components:

1. **Animator Component**
   - Your character/avatar needs an Animator component
   - This is what will play the animations
   - Usually already present on character models

2. **MotionManager** (Auto-created)
   - Manages all MotionPlayback instances
   - Automatically created if missing

3. **MotionPlayback** (What you're adding)
   - Handles playing FBX motion files
   - Automatically registers with MotionManager

---

## Setup via Code (For Programmers)

### At Runtime:

```csharp
// Automatically setup (finds Animator automatically)
MotionPlaybackSetup.SetupMotionPlaybackRuntime();

// Or setup on specific GameObject
GameObject myCharacter = GameObject.Find("MyCharacter");
MotionPlaybackSetup.SetupMotionPlaybackRuntime(myCharacter);
```

### In Your Own Script:

```csharp
using UnityEngine;

public class MySetupScript : MonoBehaviour
{
    void Start()
    {
        // Ensure MotionManager exists
        MotionManager.Ensure();
        
        // Get or create MotionPlayback
        MotionPlayback playback = GetComponent<MotionPlayback>();
        if (playback == null)
        {
            playback = gameObject.AddComponent<MotionPlayback>();
        }
        
        // Find Animator
        Animator animator = GetComponent<Animator>();
        if (animator != null)
        {
            playback.SetTargetAnimator(animator);
        }
    }
}
```

---

## Verification

After setup, check:

1. ✅ **MotionManager** exists in Hierarchy
2. ✅ **MotionPlayback** component is on your character/GameObject
3. ✅ **Animator** is assigned (in MotionPlayback's Inspector)
4. ✅ **MotionManager** shows the registered playback in Inspector (if you expand it)

---

## Troubleshooting

### "MotionPlayback instance not found"

**Solution**: Run `Tools` → `Motion System` → `Setup MotionPlayback` to auto-setup

### "No Animator found"

**Solution**: 
- Add an Animator component to your character GameObject
- Or drag an Animator component to MotionPlayback's "Target Animator" field

### Motion not playing

**Check**:
1. Is MotionPlayback registered? (Check MotionManager in Hierarchy)
2. Is Animator assigned? (Check MotionPlayback Inspector)
3. Is the FBX file valid? (Check console for errors)

---

## Tips

- **Multiple Characters**: You can have multiple MotionPlayback instances
  - Set one as "Primary" in MotionManager
  - Or specify which one to use in code

- **Auto-Registration**: MotionPlayback automatically registers with MotionManager on Awake()
  - No manual setup needed if you add the component

- **Scene Persistence**: MotionManager uses DontDestroyOnLoad
  - It persists across scene changes
  - Only one instance exists at a time

---

## Example Scene Structure

```
Scene
├── MotionManager (Auto-created, persists)
│   └── MotionManager Component
│
└── MyCharacter (Your avatar)
    ├── Animator Component
    ├── MotionPlayback Component
    │   ├── Target Animator: [MyCharacter's Animator]
    │   ├── Register With Manager: ✅
    │   └── Is Primary: ✅
    └── ... (other components)
```

---

## Next Steps

Once setup is complete:
1. Your ChatUIManager will automatically find MotionManager
2. Motion files will play automatically when received from backend
3. Check the Console for "[MotionManager]" logs to verify it's working

