FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    python3 \
    libssl-dev \
    zlib1g-dev \
    libasio-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY . .

RUN cmake -S blog -B blog/build \
    -DCMAKE_BUILD_TYPE=Release \
    && cmake --build blog/build --parallel "$(nproc)"

FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /src/blog/build/cppblog ./cppblog
COPY --from=builder /src/blog/static ./static

ENV PORT=8080
EXPOSE 8080

ENTRYPOINT ["./cppblog"]
