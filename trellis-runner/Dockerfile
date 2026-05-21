# Blackwell-compatible TRELLIS.2 inference image.
# Deviates from upstream setup.sh: CUDA 12.8 (sm_120) instead of 12.4,
# PyTorch 2.7 + cu128 instead of 2.6 + cu124, and a newer flash-attn that
# ships Blackwell wheels.

FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/opt/conda/bin:/usr/local/cuda/bin:$PATH \
    TORCH_CUDA_ARCH_LIST="12.0" \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    OPENCV_IO_ENABLE_OPENEXR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates build-essential ninja-build \
        libjpeg-dev libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Miniforge (conda + mamba) — keeps the env layout setup.sh expects.
RUN curl -fsSL -o /tmp/mf.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
    && bash /tmp/mf.sh -b -p /opt/conda \
    && rm /tmp/mf.sh \
    && /opt/conda/bin/conda create -y -n trellis2 python=3.10 \
    && /opt/conda/bin/conda clean -afy

# Make sure subsequent RUNs use the trellis2 env's python/pip.
ENV PATH=/opt/conda/envs/trellis2/bin:$PATH

# Torch matched to CUDA 12.8 (Blackwell support).
RUN pip install --no-cache-dir \
        torch==2.7.1 torchvision==0.22.1 \
        --index-url https://download.pytorch.org/whl/cu128

# TRELLIS.2 source — clone INSIDE the image, not on the host.
RUN git clone -b main --recursive https://github.com/microsoft/TRELLIS.2.git /opt/trellis2

WORKDIR /opt/trellis2

# Basic deps (lifted from setup.sh --basic, minus the conda env create and
# minus pillow-simd which is abandoned and breaks on modern Pillow).
RUN pip install --no-cache-dir \
        imageio imageio-ffmpeg tqdm easydict opencv-python-headless ninja \
        trimesh transformers gradio==6.0.1 tensorboard pandas lpips zstandard \
        kornia timm \
    && pip install --no-cache-dir \
        "git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8"

# Attention backends. xformers's bundled flash kernels stop at sm_90 (Hopper);
# Blackwell (sm_120) needs the real flash-attn 2.8.x build with Blackwell
# kernels. Keep xformers around as the sparse-conv attention path TRELLIS
# uses by default, but install flash-attn for the main pipeline attention.
RUN pip install --no-cache-dir xformers==0.0.30 \
        --index-url https://download.pytorch.org/whl/cu128
RUN pip install --no-cache-dir \
    https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3+cu12torch2.7cxx11abiTRUE-cp310-cp310-linux_x86_64.whl

# From-source CUDA extensions. nvcc 12.8 will emit sm_120 because of
# TORCH_CUDA_ARCH_LIST above.
RUN git clone -b v0.4.0 https://github.com/NVlabs/nvdiffrast.git /tmp/nvdiffrast \
    && pip install --no-cache-dir /tmp/nvdiffrast --no-build-isolation \
    && rm -rf /tmp/nvdiffrast

RUN git clone -b renderutils https://github.com/JeffreyXiang/nvdiffrec.git /tmp/nvdiffrec \
    && pip install --no-cache-dir /tmp/nvdiffrec --no-build-isolation \
    && rm -rf /tmp/nvdiffrec

RUN git clone --recursive https://github.com/JeffreyXiang/CuMesh.git /tmp/cumesh \
    && pip install --no-cache-dir /tmp/cumesh --no-build-isolation \
    && rm -rf /tmp/cumesh

RUN git clone --recursive https://github.com/JeffreyXiang/FlexGEMM.git /tmp/flexgemm \
    && pip install --no-cache-dir /tmp/flexgemm --no-build-isolation \
    && rm -rf /tmp/flexgemm

RUN pip install --no-cache-dir /opt/trellis2/o-voxel --no-build-isolation

# Make TRELLIS.2 importable.
ENV PYTHONPATH=/opt/trellis2:$PYTHONPATH

# TRELLIS.2's BiRefNet (rembg) custom code uses `_tied_weights_keys`, an API
# that transformers 5.x renamed to `all_tied_weights_keys`. Pin back to 4.x
# until upstream updates the modeling file.
RUN pip install --no-cache-dir 'transformers<5'

# torch 2.7 pins triton==3.3.0 which doesn't have working sm_120 codegen —
# flex_gemm's JIT kernels die with `PassManager::run failed` on Blackwell.
# Triton 3.4 has the Blackwell backend; force-install past torch's pin AFTER
# every other pip install so nothing downgrades it back.
RUN pip install --no-cache-dir --no-deps --force-reinstall triton==3.4.0

COPY trellis_generate.py /opt/trellis2/trellis_generate.py

ENTRYPOINT ["python", "/opt/trellis2/trellis_generate.py"]
