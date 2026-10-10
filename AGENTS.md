This project is a custom node repository for ComfyUI.

## Shipping changes to ComfyUI

ComfyUI does not load this folder directly. It runs in a sandbox
(`/workspace/dev/ComfyUI`, see its `README.md`) that installs this pack from its
public GitHub repository, pinned to one commit. A change reaches ComfyUI only
after it is pushed and the pack is reinstalled at the new commit.

1. **Test and commit.** Run `pytest` from the repository root. Commit on `master`.
   Keep `config/credentials.json`, `wildcards/` and `resources/` out of git: they
   are ignored on purpose.
2. **Push.** Run `git push origin master`. If the push fails for lack of
   credentials, stop and ask the human to push. Don't change the remote or set
   up keys.
3. **Confirm the commit is public.** The sandbox fetches over HTTPS, so the
   remote must already have the commit:
   ```sh
   SHA=$(git rev-parse HEAD)
   git ls-remote https://github.com/cidiro/cid-node-pack.git master   # must print $SHA
   ```
4. **Reinstall in the development copy of ComfyUI.** ComfyUI must be stopped
   first:
   ```sh
   cd /workspace/dev/ComfyUI
   ./comfy-sandbox status          # must list no containers; otherwise ./comfy-sandbox stop
   ./comfy-sandbox install-node https://github.com/cidiro/cid-node-pack "$SHA"
   ```
   Use the full 40-character SHA; branch names are refused. Agent sessions run
   `./comfy-sandbox` directly. From a human terminal it is
   `agents comfy-sandbox …`. The build must end with
   `Node image ready.`. If it fails, the previous image stays selected.
5. **Verify it loads.** Start the backend, then check the log and the
   registered node count before stopping it:
   ```sh
   ./comfy-sandbox start --headless
   ./comfy-sandbox logs 2>&1 | grep -E "cid-node-pack|IMPORT FAILED"
   podman exec comfy-backend python -I -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8188/object_info')); print(sum(k.startswith('Cid') for k in d))"
   ./comfy-sandbox stop
   ```
   The count must equal the number of entries in `NODE_CLASS_MAPPINGS` in
   `__init__.py`. If something is wrong, `./comfy-sandbox rollback` restores
   the previous node set.
6. **Hand off to the human.** The real ComfyUI app runs from a separate,
   root-owned copy that agents cannot change. Tell the human the new SHA and ask
   them to close ComfyUI and run `agentctl app-install comfyui`.

## Sandbox constraints for nodes

The backend is offline, and it can only see `/data/input`, `/data/output`,
`/data/user` and read-only models. The node code folder is read-only there.
So nodes must not write inside this repository at runtime, and they cannot
reach host services such as a local LLM server. New third-party imports need a
`requirements.txt` entry with plain package names only (no URLs, paths or pip
options), and a binary wheel must exist for each one.
