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
          LLM["llm-server<br/>:8080<br/>GPU: CUDA/OptiX"]
          BW["blender-worker<br/>GPU: CUDA/OptiX"]
        end

        subgraph Optional["Optional Services"]
          UE5["ue5-server<br/>:8081<br/>GPU: CUDA"]
          GODOT["godot-server<br/>:8082"]
          AIV["ai-video-server<br/>:8083<br/>GPU: CUDA"]
        end
      end
    end
  `

const section1 = `
# Docker Setup: Isolation and GPU Passthrough

The decision to containerize DeepBl4nder's services was not made for convenience or deployment simplicity — though it provides both. It was made because Docker provides something that bare-metal execution cannot: **process isolation with resource control**. When an LLM generates a Python script that will execute Blender in headless mode, that script needs to run in an environment where its effects are bounded, its resources are allocated, and its failures do not cascade to the host system. Docker provides all three guarantees, and it does so with a maturity and ecosystem that makes it the natural choice for production deployment.

But Docker introduces its own challenges, particularly around GPU access. LLM inference and 3D rendering are GPU-intensive workloads, and containers do not have native access to host GPUs. DeepBl4nder solves this through NVIDIA Container Toolkit, which provides transparent GPU passthrough to containers. The result is that services inside containers see and use GPUs as if they were running on bare metal, while the host system maintains control over resource allocation and process isolation.

## Why Docker Matters for Isolation

The isolation provided by Docker serves three purposes in DeepBl4nder: security, resource management, and reproducibility.

**Security isolation.** When BlenderBridge executes a Python script, that script runs inside a Docker container with a limited filesystem view, no network access (unless explicitly configured), and controlled resource limits. Even if the AST validator misses a dangerous operation, the Docker container limits what the operation can affect. The script cannot access files outside its mounted volumes, it cannot make network connections, and it cannot consume more CPU or memory than allocated.

**Resource management.** Each service in the DeepBl4nder stack has different resource requirements. The LLM server needs GPU memory for model inference. The Blender worker needs CPU cores for scene computation and GPU cores for rendering. The AI video server needs GPU memory for video generation. Docker Compose's \`deploy.resources\` configuration allows each service to declare its GPU requirements, and the NVIDIA Container Toolkit ensures that only the allocated GPUs are accessible to each service.

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

The \`count: 1\` parameter reserves one GPU for the service. The \`capabilities: [gpu]\` parameter grants the service access to CUDA compute capabilities. Together, these ensure that the LLM server has exclusive access to one GPU, and the Blender worker has exclusive access to another.

This exclusive allocation is important because GPU memory is not easily shared between processes. If the LLM server and Blender worker both tried to use the same GPU, they would compete for memory, potentially causing out-of-memory errors. By allocating separate GPUs to each service, DeepBl4nder eliminates this contention.

<Callout type="warning" title="GPU Requirements">
The LLM server requires an NVIDIA GPU with at least 8 GB VRAM for the Qwen3-8B model. The Blender worker benefits from GPU acceleration for Cycles rendering but can fall back to CPU rendering. The AI video server requires a GPU with at least 12 GB VRAM for video generation. If you have only one GPU, prioritize the LLM server and run the Blender worker in CPU mode.
</Callout>

## The Services: What Each Container Does

DeepBl4nder's Docker Compose configuration defines five services, each in its own container. The default profile starts only the two core services — the LLM server and the Blender worker. Optional services are started on demand using Docker Compose profiles.

### LLM Server

The LLM server runs llama.cpp with the Qwen3 model for local inference. It exposes an OpenAI-compatible API on port 8080, which means any tool or library that can call the OpenAI API can also call the local LLM server. The server loads the model into GPU memory at startup and serves inference requests with low latency.

The LLM server is the foundation of the entire system. Without it, agents cannot reason, code cannot be generated, and productions cannot proceed. This is why it is the only service that is always started — the \`docker compose up\` command starts the LLM server and the Blender worker by default.

The server uses a health check that polls the \`/v1/models\` endpoint every 30 seconds. Other services depend on this health check, ensuring that they do not start until the LLM server is ready to handle requests.

### Blender Worker

The Blender worker runs Blender 4.1 in headless mode, along with FFmpeg for video processing. It does not expose a network port — instead, it communicates with the rest of the system through shared volumes. The worker receives scripts via the filesystem, executes them in Blender, and writes output to the shared output directory.

The worker container includes both Blender and FFmpeg because these tools are tightly coupled in the production pipeline. Blender renders frames, and FFmpeg assembles them into video. Keeping them in the same container avoids the complexity of cross-container file transfer for intermediate rendering products.

The worker also reserves a GPU for Cycles rendering. While Blender can render on CPU, GPU rendering is significantly faster — often 5 to 10 times faster for complex scenes. The GPU reservation ensures that the worker has exclusive access to a GPU for rendering.

### UE5 Server (Optional)

The UE5 server runs Unreal Engine 5 as a REST API service on port 8081. It provides commands for level creation, asset import, material setup, lighting, and rendering via Movie Render Queue. The server requires its own GPU for real-time rendering and ray tracing.

This service is started on demand using the \`ue5\` Docker Compose profile:

\`\`\`bash
docker compose --profile ue5 up -d
\`\`\`

The UE5 server depends on the LLM server being healthy, ensuring that the full pipeline is available when production begins.

### Godot Server (Optional)

The Godot server runs Godot 4 as a REST API service on port 8082. It provides scene management, procedural mesh generation, material setup, lighting, and WebGL export. Unlike UE5, Godot does not require GPU access for its REST API operations, making it lighter on resources.

This service is started on demand using the \`godot\` profile:

\`\`\`bash
docker compose --profile godot up -d
\`\`\`

### AI Video Server (Optional)

The AI video server runs text-to-video and image-to-video generation models on port 8083. It supports CogVideoX, SVD, and AnimateDiff models. This is the most GPU-intensive service in the stack — video generation requires significant VRAM and compute time.

The server uses a named Docker volume (\`ai-video-cache\`) for caching generated videos and intermediate models. This cache persists across container restarts, avoiding the need to re-download models every time the service starts.

\`\`\`bash
docker compose --profile ai-video up -d
\`\`\`

## Docker Profiles: Selective Service Startup

Docker Compose profiles allow DeepBl4nder to start only the services that are needed. The default profile starts the core services — the LLM server and the Blender worker. Optional profiles add services on demand.

\`\`\`bash
# Core services only (default)
docker compose up -d

# With Unreal Engine 5
docker compose --profile ue5 up -d

# With Godot 4
docker compose --profile godot up -d

# With AI Video generation
docker compose --profile ai-video up -d

# All services
docker compose --profile ue5 --profile godot --profile ai-video up -d
\`\`\`

This selective startup is important for resource management. Not every production needs UE5 or Godot. Not every workstation has the VRAM for AI video generation. Profiles allow operators to start only what they need, conserving resources for the services that matter.

## Environment Variables

The Docker configuration uses environment variables to control service behavior. The most important variables are shared across services through the \`x-common-env\` YAML anchor:

- \`DeepBl4nder_MODELS_DIR\` controls where LLM models are stored (default: \`./models\`)
- \`DeepBl4nder_LLM_HOST\` and \`DeepBl4nder_LLM_PORT\` configure the LLM server connection
- \`BLENDER_EXE\` points to the Blender binary inside the container (default: \`/usr/local/bin/blender\`)
- \`FFMPEG_EXE\` points to the FFmpeg binary (default: \`/usr/local/bin/ffmpeg\`)
- \`DeepBl4nder_BUDGET\` sets the default production budget in USD (default: \`1.0\`)
- \`DeepBl4nder_DATA_DIR\` controls where production data is stored (default: \`./data\`)

These variables are defined in the \`docker-compose.yml\` file and can be overridden in a \`.env\` file for local customization.

<Callout type="tip" title="Troubleshooting">
Common Docker issues and their solutions:

- **GPU not found**: Verify that \`nvidia-smi\` works on the host, then check that the NVIDIA Container Toolkit is installed and Docker has been restarted
- **Port conflict**: If port 8080 is already in use, change the port mapping in \`docker-compose.yml\` or stop the conflicting service
- **Out of memory**: Use a smaller model (Qwen3-1.5B or Qwen3-4B) or reduce \`--n-gpu-layers\` in the LLM server command
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
