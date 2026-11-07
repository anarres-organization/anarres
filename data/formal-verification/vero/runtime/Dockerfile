FROM docker.io/library/ubuntu:24.04@sha256:78d4744ead1f5b19b04d0df558ab182a5300903900755e515b2ca4d10eb2044d

ARG ELAN_VERSION=4.2.3
ARG ELAN_SHA256=df0b2b3a439961ffcbb3985214365ffe40f49bc871df04dff268c7d8e21ca8b2
ARG LEAN_TOOLCHAIN=leanprover/lean4:v4.29.1

ENV DEBIAN_FRONTEND=noninteractive \
    ELAN_HOME=/opt/elan \
    PATH=/opt/elan/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        curl \
        findutils \
        git \
        grep \
        patch \
        procps \
        python3 \
        ripgrep \
        sed \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
        "https://github.com/leanprover/elan/releases/download/v${ELAN_VERSION}/elan-x86_64-unknown-linux-gnu.tar.gz" \
        --output /tmp/elan.tar.gz \
    && echo "${ELAN_SHA256}  /tmp/elan.tar.gz" | sha256sum --check --strict \
    && tar --extract --gzip --file /tmp/elan.tar.gz --directory /tmp elan-init \
    && /tmp/elan-init -y --no-modify-path --default-toolchain none \
    && elan toolchain install "${LEAN_TOOLCHAIN}" \
    && elan default "${LEAN_TOOLCHAIN}" \
    && rm -f /tmp/elan-init /tmp/elan.tar.gz \
    && lean --version | grep -F 'Lean (version 4.29.1' \
    && lake --version \
    && python3 --version \
    && timeout --version | head -1 \
    && chmod -R a+rX /opt/elan

LABEL org.opencontainers.image.title="Anarres Vero Lean runtime" \
      org.opencontainers.image.description="Network-isolated model-facing runtime for the frozen Vero development probe" \
      org.opencontainers.image.source="https://github.com/anarres-organization/anarres" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.base.name="docker.io/library/ubuntu:24.04" \
      org.anarres.lean.toolchain="leanprover/lean4:v4.29.1" \
      org.anarres.elan.version="4.2.3"

WORKDIR /workspace
