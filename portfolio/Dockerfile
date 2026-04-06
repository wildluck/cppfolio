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

RUN cmake -S portfolio -B portfolio/build \
    -DCMAKE_BUILD_TYPE=Release \
    && cmake --build portfolio/build --parallel "$(nproc)"

FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /src/portfolio/build/cppfolio ./cppfolio
COPY --from=builder /src/portfolio/static ./static

ENV PORT=8080
EXPOSE 8080

ENTRYPOINT [ "./cppfolio" ]
