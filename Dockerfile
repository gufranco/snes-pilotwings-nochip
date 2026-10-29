FROM mirror.gcr.io/library/debian:bookworm-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3 AS asar

ARG ASAR_REF=v1.81

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 --branch "${ASAR_REF}" https://github.com/RPGHacker/asar.git /src/asar \
    && cmake -S /src/asar/src -B /build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /build --parallel

RUN cp /build/asar/asar-standalone /usr/local/bin/asar \
    && /usr/local/bin/asar --version | grep -q "^Asar 1.81,"

FROM mirror.gcr.io/library/debian:bookworm-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3 AS emulator

ARG SNES9X_REF=2971061cf07fdc6fc7d18883edf4e648eb16a6d2

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git ca-certificates make perl \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --filter=blob:none --no-checkout \
        https://github.com/snes9xgit/snes9x.git /src/snes9x \
    && git -C /src/snes9x checkout --quiet "${SNES9X_REF}" \
    && test "$(git -C /src/snes9x rev-parse HEAD)" = "${SNES9X_REF}"

RUN perl -0pi -e 's/(void DSP1SetByte \(uint8 byte, uint16 address\)\n\{)/extern "C" void pw_note_dsp(int, unsigned char, unsigned short);\n$1\n\tpw_note_dsp(0, byte, address);/' /src/snes9x/dsp1.cpp \
    && test "$(grep -c 'pw_note_dsp(0, byte, address)' /src/snes9x/dsp1.cpp)" = "1"

RUN perl -0pi -e 's/(\n\treturn \(t\);\n\})/\n\tpw_note_dsp(1, t, address);$1/' /src/snes9x/dsp1.cpp \
    && test "$(grep -c 'pw_note_dsp(1, t, address)' /src/snes9x/dsp1.cpp)" = "1"

WORKDIR /src/snes9x/libretro
RUN make STATIC_LINKING=1 -j"$(nproc)" \
    && cp snes9x_libretro.so /src/snes9x/libretro/snes9x_libretro.a

COPY emu/main.cpp /src/frontend/main.cpp

RUN g++ -O2 -std=c++11 -o /src/pwemu \
        /src/frontend/main.cpp \
        -I/src/frontend -I/src/snes9x -I/src/snes9x/libretro \
        -I/src/snes9x/libretro/libretro-common/include \
        -I/src/snes9x/apu -I/src/snes9x/apu/bapu \
        /src/snes9x/libretro/snes9x_libretro.a

FROM mirror.gcr.io/library/python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

COPY --from=asar /usr/local/bin/asar /usr/local/bin/asar
COPY --from=emulator /src/pwemu /usr/local/bin/pwemu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

WORKDIR /work

FROM runtime AS gates

COPY --from=mirror.gcr.io/library/node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203 /usr/local /usr/local

RUN apt-get update && apt-get install -y --no-install-recommends shellcheck curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG ACTIONLINT=1.7.12

RUN arch="$(dpkg --print-architecture)" \
    && case "${arch}" in \
        amd64) sum=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8 ;; \
        arm64) sum=325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6 ;; \
        *) echo "no actionlint digest for ${arch}" >&2 && exit 1 ;; \
    esac \
    && curl -fsSL -o /tmp/actionlint.tar.gz \
        "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT}/actionlint_${ACTIONLINT}_linux_${arch}.tar.gz" \
    && echo "${sum}  /tmp/actionlint.tar.gz" | sha256sum --check --strict \
    && tar -xzf /tmp/actionlint.tar.gz -C /usr/local/bin actionlint \
    && rm /tmp/actionlint.tar.gz

COPY --from=ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 /uv /usr/local/bin/uv

RUN uv pip install --system --no-cache \
        ruff==0.16.3 mypy==1.14.1 coverage==7.6.10 yamllint==1.38.0

ENV COREPACK_HOME=/opt/corepack \
    PATH=/opt/tooling/node_modules/.bin:$PATH

COPY package.json pnpm-lock.yaml /opt/tooling/

RUN cd /opt/tooling \
    && corepack pnpm install --frozen-lockfile --ignore-scripts \
    && chmod -R a+rX /opt/corepack /opt/tooling
