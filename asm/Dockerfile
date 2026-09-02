FROM debian:bookworm-slim AS build

ARG ASAR_REF=v1.81

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 --branch "${ASAR_REF}" https://github.com/RPGHacker/asar.git /src/asar \
    && cmake -S /src/asar/src -B /build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /build --parallel

# Where the standalone binary lands moved between releases, so it is found
# rather than named. v1.81 builds /build/asar/asar-standalone; v1.91 does not.
RUN find /build -type f -name 'asar*' -perm -u+x ! -name '*.so*' ! -name '*.a' \
        -exec cp {} /usr/local/bin/asar \; \
    && test -x /usr/local/bin/asar \
    && /usr/local/bin/asar --version

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 xxd \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /usr/local/bin/asar /usr/local/bin/asar

RUN useradd --create-home --uid 1000 builder
USER builder
WORKDIR /work

ENTRYPOINT ["asar"]
CMD ["--version"]
