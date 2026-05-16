# Lathemix — Three.js Procedural 3D Generator

<a href="LICENSE.txt"><img src="https://img.shields.io/badge/License-MIT-green" alt="License"></a>

A miner generator for [404-Repo](https://github.com/404-Repo) subnet 17 on Bittensor,
producing validator-compliant Three.js JavaScript modules that procedurally reconstruct
3D objects from reference photographs.

## Architecture

**Image-to-code pipeline (6 stages)** — the coder agent receives the reference image
directly and decomposes it itself, with no intermediate scene description:

```
[1/6] Coder    image → JS module (multimodal, image required as input)
[2/6] Checker  Static analysis + sandbox execution validation
[3/6] Renderer JS → 4-view PNG grid (puppeteer + Three.js)
[4/6] Critic   reference + render → JSON critique (issues + matching aspects)
[5/6] Patcher  reference + render + critic feedback → JS repair (multimodal)
[6/6] Terminal best_iter selection
```

**Backend**: vLLM serving `Qwen/Qwen3.5-A17B-FP8` (multimodal MoE), TP=4 across
4× H200 GPUs. Pipeline orchestrated via async event bus with per-actor worker pools.

## Hardware Requirements

- 4× NVIDIA H200 (or equivalent, 320+ GB combined VRAM)
- ≥ 500 GB local disk
- CUDA 12.8 driver

## Software Requirements

- Docker with NVIDIA Container Toolkit
- Python 3.11
- Node.js 20 (for the renderer sidecar)

## API

The service exposes a FastAPI on port `10006`:

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness probe |
| `/status` | GET | Batch state, progress, counts |
| `/generate` | POST | Submit batch of prompts (image URL → JS) |
| `/results` | GET | ZIP of generated `.js` modules |
| `/debug/tasks` | GET | Per-task diagnostics |

Submit format:
```json
{
  "prompts": [{"stem": "abc123", "image_url": "https://example.com/x.png"}],
  "seed": 42
}
```

## Build

Docker image (used by the subnet build pipeline):

```console
cd docker
docker build -f Dockerfile -t lathe:latest ..
```

Base image: `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel` + vLLM venv + Node 20 + Chromium.

## Configuration

Edit `configuration.yaml`:

| Section | Key parameters |
|---|---|
| `llm_clients.vision-coder.vllm` | model, gpu_ids, tensor_parallel_size, max_model_len, max_num_seqs |
| `actors.coder` | multimodal=true (required), workers, max_tokens, temperature |
| `actors.patcher` | workers, queue_size |
| `actors.critic` | max_tokens, ensemble_size, reasoning_effort |
| `event_bus` | max_iter, score_threshold, task_deadline_s |
| `renderer` | sidecar_host, sidecar_port, img_size, grid_gap |

## Run

```console
bash pipeline_service/run.sh
```

The script auto-launches vLLM per `llm_clients` config, starts the renderer sidecar
(Node) on port 8003, and serves the FastAPI on port 10006.

## License

Released under the **[MIT License](LICENSE.txt)**.
