# Build fasb as Wheel on Python 3.11-slim
FROM python:3.11-slim AS fasb

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates build-essential cmake clang && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain 1.88.0
ENV PATH="/root/.cargo/bin:${PATH}"

RUN pip install --no-cache-dir "maturin>=1.7, <2.0"

COPY lib/fasb /fasb
WORKDIR /fasb
RUN maturin build --release --interpreter python3.11 --out /wheels

FROM python:3.11-slim

WORKDIR /app

# Install only required build dependencies
RUN apt-get update && \
    apt-get install -y cmake g++ make && \
    rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY --from=fasb /wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY . . 
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Clean any old build artifacts
RUN rm -rf ./lib/downward/builds/release

# Run downward build script
RUN python3 ./lib/downward/build.py

# Test if fasb works
RUN python3 -c "from fasb import wrappers_bindings, interpreter_bindings"

# Expose Flask port
EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
