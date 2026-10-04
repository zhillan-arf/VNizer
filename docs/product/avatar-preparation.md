# Avatar preparation

The local release uses Ene from the VModel source project.
The five moods are neutral, explaining, curious, positive, and serious.
Each clip contains a speaking mouth cycle and a blink.
The mouth cycle is decorative. It does not provide phoneme-level lip synchronization.

The repository also contains an original vector character for portable setup and tests.
`seed_avatars` prepares this fallback when a new data directory starts.
Import the Ene pack to select the VModel character for all five moods.

## Prepare the local pack

Run these commands from the VNizer repository:

```sh
blender -b -t 4 --python scripts/render_vmodel_avatars.py -- \
  /home/zhillan/misc/vmodel /tmp/vnizer/ene-frames
uv run python scripts/import_vmodel_avatars.py /tmp/vnizer/ene-frames
```

The render uses four CPU threads. It does not use the occupied inference GPU.
The importer writes the pack under `/data-model/zhillan/VNizer/avatars/ene`.
It copies the selected clips into the configured VNizer data directory.
The pack inventory records the source hash, Blender version, credits, and output hashes.

Set `VNIZER_DATA_ROOT` before import if the deployment uses a different data directory.
The source model and generated character media are not committed to Git.
Keep the VModel source notices with the local asset pack.

## Replace an avatar

Use the admin page to upload an image or a short animated clip for a mood.
Select the new asset to use it in later attempts.
Running attempts keep their own copies of selected assets.
