"""Run with Blender to prepare private avatar frames from the VModel source."""

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    reference, output = Path(args[0]).resolve(), Path(args[1]).resolve()
    source = reference / "assets/work/ene/source.blend"
    profile = json.loads((reference / "config/avatars/ene.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(source))
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"
              and any(mod.type == "ARMATURE" and mod.object == armature for mod in obj.modifiers)]
    for obj in bpy.data.objects:
        obj.hide_render = obj not in meshes and obj != armature
    for obj in [armature, *meshes]:
        obj.animation_data_clear()
        if obj.type == "MESH" and obj.data.shape_keys:
            obj.data.shape_keys.animation_data_clear()
        if obj.type == "MESH":
            obj.data.validate(clean_customdata=False)
    for image in bpy.data.images:
        if image.source == "FILE" and not image.packed_file:
            path = Path(bpy.path.abspath(image.filepath))
            if not path.exists():
                basename = image.filepath.replace("\\", "/").split("/")[-1]
                matches = list((reference / "ops/resources/ENE").glob(basename))
                if not matches:
                    raise RuntimeError(f"Missing character texture: {basename}")
                image.filepath = str(matches[0])
                image.reload()
    for bone in armature.pose.bones:
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion.identity()
        bone.location = (0, 0, 0)
        bone.scale = (1, 1, 1)

    def rotate(name, axis, degrees):
        bone = armature.pose.bones[profile["humanoid"][name]]
        local = bone.bone.matrix_local.to_quaternion().inverted() @ Vector(axis)
        bone.rotation_quaternion = Quaternion(local, math.radians(degrees))

    def morph(name, value):
        source_name = profile["expressions"].get(name, name)
        for mesh in meshes:
            if mesh.data.shape_keys:
                key = mesh.data.shape_keys.key_blocks.get(source_name)
                if key:
                    key.value = value

    rotate("leftUpperArm", (0, 1, 0), 45)
    rotate("leftLowerArm", (0, 1, 0), -135)
    rotate("rightUpperArm", (0, 1, 0), -35)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.film_transparent = True
    scene.render.resolution_x = 480
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.world.color = (0.17, 0.17, 0.17)
    center = Vector((0, -0.025, 1.18))
    bpy.ops.object.camera_add(location=(0, -3.5, 1.18))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.12
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    for location, power in (((1.5, -3, 3), 100), ((-2, -1, 2), 70), ((1, 2, 3), 80)):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = power
        light.data.size = 4
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    expressions = {
        "neutral": {}, "explaining": {"happy": 0.15},
        "curious": {"sad": 0.35, "surprised": 0.15},
        "positive": {"happy": 0.65}, "serious": {"angry": 0.2},
    }
    if "--preview" in args:
        expressions = {"neutral": expressions["neutral"]}
    for mood, values in expressions.items():
        folder = output / mood
        folder.mkdir(parents=True, exist_ok=True)
        for frame in range(1 if "--preview" in args else 4):
            path = folder / f"{frame:02}.png"
            if path.exists():
                continue
            for mesh in meshes:
                if mesh.data.shape_keys:
                    for key in mesh.data.shape_keys.key_blocks:
                        key.value = 0
            for name, value in values.items():
                morph(name, value)
            morph("aa", (0.05, 0.4, 0.15, 0.55)[frame])
            morph("blink", 0.8 if frame == 2 else 0)
            rotate("head", (0, 1, 0), (-1, 0, 1, 0)[frame])
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            print(f"Completed {mood} frame {frame}", flush=True)
    (output / "source.json").write_text(json.dumps({
        "source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "blender": bpy.app.version_string, "engine": "Cycles CPU", "frames_per_mood": 4,
        "credits": "Ene edit: AuroraYok / yokkaulove (DA). Preserve the source package terms.",
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
