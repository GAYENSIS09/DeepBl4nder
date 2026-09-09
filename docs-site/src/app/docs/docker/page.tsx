import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'Docker Setup: Isolation and GPU Passthrough - DeepBl4nder',
  description: 'Why Docker matters for isolation, how GPU passthrough works with NVIDIA Container Toolkit, and what each service does in its own container.',
}

const mermaidChart1 = `graph TB
    subgraph Host["Host Machine"]
      subgraph Docker["Docker Engine"]
        subgraph Core["Core Services"]
          LLM["llm-server<br/>:8080<br/>Optional Local Inference<br/>GPU: CUDA/OptiX"]
          BW["blender-worker<br/>GPU: CUDA/OptiX"]
        end
      end
    end
  `

const section1 = `
# Docker Setup: Isolation and GPU Passthrough

The decision to containerize DeepBl4nder's services was not made for convenience or deployment simplicity — though it provides both. It was made because Docker provides something that bare-metal execution cannot: **process isolation with resource control**. When an LLM generates a Python script that will execute Blender in headless mode, that script needs to run in an environment where its effects are bounded, its resources are allocated, and its failures do not cascade to the host system. Docker provides all three guarantees, and it does so with a maturity and ecosystem that makes it the natural choice for production deployment.

But Docker introduces its own challenges, particularly around GPU access. 3D rendering is a GPU-intensive workload, and containers do not have native access to host GPUs. DeepBl4nder solves this through NVIDIA Container Toolkit, which provides transparent GPU passthrough to containers. The result is that services inside containers see and use GPUs as if they were running on bare metal, while the host system maintains control over resource allocation and process isolation.

## Why Docker Matters for Isolation

The isolation provided by Docker serves three purposes in DeepBl4nder: security, resource management, and reproducibility.

**Security isolation.** When BlenderBridge executes a Python script, that script runs inside a Docker container with a limited filesystem view, no network access (unless explicitly configured), and controlled resource limits. Even if the AST validator misses a dangerous operation, the Docker container limits what the operation can affect. The script cannot access files outside its mounted volumes, it cannot make network connections, and it cannot consume more CPU or memory than allocated.

**Resource management.** Each service in the DeepBl4nder stack has different resource requirements. The Blender worker needs CPU cores for scene computation and GPU cores for rendering. The optional local LLM server needs GPU memory for model inference if it is used. Docker Compose's \`deploy.resources\` configuration allows each service to declare its GPU requirements, and the NVIDIA Container Toolkit ensures that only the allocated GPUs are accessible to each service.

**Reproducibility.** Docker images encapsulate the exact versions of Blender, FFmpeg, Python, and all dependencies that a service requires. A production that works today will work tomorrow, next week, and next year — regardless of what software is installed on the host machine. This reproducibility is essential for a system that may run productions over extended periods.
`

const section2 = `
## GPU Passthrough with NVIDIA Container Toolkit

The NVIDIA Container Toolkit is the bridge between Docker's containerization model and NVIDIA's GPU hardware. Without it, containers cannot access GPUs at all. With it, containers see GPUs as if they were local devices, complete with CUDA support, memory management, and driver integration.

The toolkit works by injecting NVIDIA's container runtime into Docker. When a container is configured with GPU access — either through \`docker run --gpus all\` or through Docker Compose's \`deploy.resources.reservations.devices\` configuration — the NVIDIA runtime mounts the necessary driver libraries and device files into the container. The container then sees the GPU as a local device and can use it through standard CUDA APIs.

### Installation

Installing the NVIDIA Container Toolkit requires three steps: adding the NVIDIA package repository, installing the toolkit package, and configuring Docker to use the NVIDIA runtime.

\`\`\`bash
# Add NVIDIA package repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \\
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \\
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \\
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install the toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use the NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker

# Restart Docker
sudo systemctl restart docker
\`\`\`

After installation, you can verify that GPU access works inside containers:

\`\`\`bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
\`\`\`

This command should display the same GPU information that \`nvidia-smi\` shows on the host. If it does, GPU passthrough is working correctly.

### GPU Allocation in Docker Compose

DeepBl4nder's \`docker-compose.yml\` configures GPU allocation for each service that needs GPU access. The configuration uses Docker Compose's \`deploy.resources.reservations.devices\` syntax, which reserves specific GPU capabilities for each service.

\`\`\`yaml
services:
  llm-server:
    image: deepbl4nder-llm
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
\`\`\`

The \`count: 1\` parameter reserves one GPU for the service. The \`capabilities: [gpu]\` parameter grants the service access to CUDA compute capabilities. The Blender worker reserves GPU access for Cycles rendering. The optional local LLM server also reserves a GPU if it is used for local inference. If you have only one GPU, you can run the local LLM server in CPU mode or — more commonly — rely on cloud LLM providers entirely and skip the local LLM server.

<Callout type="info" title="GPU Requirements">
A GPU is required for Blender rendering (Cycles benefits greatly from GPU acceleration, though CPU rendering is a fallback). The optional local \`llm-server\` also uses an NVIDIA GPU for local inference with llama.cpp/Qwen3 — but it is NOT required when using cloud LLM providers. When agents are backed by the cloud LLM router (Gemini, Groq, NVIDIA, OpenRouter, Cloudflare), no local LLM GPU is needed at all.
</Callout>

## The Services: What Each Container Does

DeepBl4nder's Docker Compose configuration defines three services — the optional local LLM server, the Blender worker, and the TUI. The **primary production service for rendering is the \`blender-worker\`**. The \`llm-server\` is an optional, legacy local inference service that is not required when using cloud LLM providers, which is how the agents are normally powered.

### Blender Worker — The Core Rendering Service

The Blender worker runs Blender 4.1 in headless mode, along with FFmpeg for video processing. It does not expose a network port — instead, it communicates with the rest of the system through shared volumes. The worker receives scripts via the filesystem, executes them in Blender, and writes output to the shared output directory.

The worker container includes both Blender and FFmpeg because these tools are tightly coupled in the production pipeline. Blender renders frames, and FFmpeg assembles them into video. Keeping them in the same container avoids the complexity of cross-container file transfer for intermediate rendering products.

The worker reserves a GPU for Cycles rendering. While Blender can render on CPU, GPU rendering is significantly faster — often 5 to 10 times faster for complex scenes. The GPU reservation ensures that the worker has exclusive access to a GPU for rendering. Blender is the only rendering engine in the stack (Cycles or EEVEE on Blender 4.1+).

### LLM Server (Optional Local Inference)

The \`llm-server\` service is an optional, legacy local inference option that runs llama.cpp with a Qwen3 GGUF model. It exposes an OpenAI-compatible API on port 8080 and is built from \`Dockerfile.llm\`. This service is **not required** — the agents' LLM is a cloud multi-provider router aggregated via litellm and configured by API keys. The local \`llm-server\` exists for environments where an operator specifically wants to run a local model instead of using cloud providers.

If you choose to run the local LLM server, it loads the model into GPU memory at startup and serves inference requests with low latency. It uses a health check that polls the \`/v1/models\` endpoint. For most deployments, however, agents are configured with cloud provider API keys, and the local server is left disabled.

### TUI Service

A \`tui\` service is defined under the \`tui\` Docker profile, providing a containerized way to launch the terminal interface.

## Docker Profiles: Service Startup

The \`docker compose up\` command starts the core services — the Blender worker (and the optional LLM server if enabled):

\`\`\`bash
# Core services only (default)
docker compose up -d
\`\`\`

Blender is the only rendering engine in the stack, so no optional engine profiles are needed. This keeps the deployment simple and the resource footprint predictable.

## Environment Variables

The Docker configuration uses environment variables to control service behavior. The most important variables are shared across services through the \`x-common-env\` YAML anchor:

- \`GEMINI_API_KEY\`, \`GROQ_API_KEY\`, \`NVIDIA_API_KEY\`, \`OPENROUTER_API_KEY\` configure the cloud LLM router providers (at least one is required)
- \`CLOUDFLARE_API_KEY\` and \`CLOUDFLARE_ACCOUNT_ID\` configure the Cloudflare LLM provider
- \`DeepBl4nder_BUDGET\` sets the default production budget in USD (default: \`1.0\`)
- \`DeepBl4nder_LLM_HOST\` and \`DeepBl4nder_LLM_PORT\` configure the optional local \`llm-server\` connection
- \`DeepBl4nder_MODELS_DIR\` controls where local LLM models are stored (default: \`./models\`) — used only by the optional local \`llm-server\`
- \`BLENDER_EXE\` points to the Blender binary inside the container (default: \`/usr/local/bin/blender\`)
- \`FFMPEG_EXE\` points to the FFmpeg binary (default: \`/usr/local/bin/ffmpeg\`)
- \`GIT_EXE\` points to the Git binary

These variables are defined in the \`docker-compose.yml\` file and can be overridden in a \`.env\` file for local customization.

<Callout type="tip" title="Troubleshooting">
Common Docker issues and their solutions:

- **GPU not found**: Verify that \`nvidia-smi\` works on the host, then check that the NVIDIA Container Toolkit is installed and Docker has been restarted
- **Port conflict**: If port 8080 is already in use, change the port mapping in \`docker-compose.yml\` or stop the conflicting service
- **Out of memory (local LLM server)**: Use a smaller model (Qwen3-1.5B or Qwen3-4B) or reduce the GPU layers in the LLM server command — or disable the local server and use cloud providers
- **Blender not found**: The container includes Blender — if it is missing, rebuild the Docker image with \`docker compose build\`
</Callout>
`

export default function DockerPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={mermaidChart1} title="Docker Service Architecture" />
      <MDXRenderer source={section2} />
    </>
  )
}
