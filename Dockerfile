# Third-party base image (from WZML-X), locked to a digest so a changed or
# hijacked "wzadv" tag cannot silently replace what we build on.
# To update: docker pull mysterysd/wzmlx:wzadv, check it, then put the new
# digest from `docker inspect --format '{{index .RepoDigests 0}}'` here.
# BASE_IMAGE can point at our own copy, e.g.
# ghcr.io/ownermood/villanbot-base@sha256:<same digest> (see mirror-base-image.yml)
ARG BASE_IMAGE=mysterysd/wzmlx:wzadv@sha256:1cb1de42b18361fa7babd7e4d6adef4be0138a7ef5b8126eef581dd3e1efd0bc
FROM ${BASE_IMAGE}
# COPY --from=mysterysd/wzmlx:m-tools /usr/local /usr/local

WORKDIR /usr/src/app

COPY requirements.txt .
RUN uv pip install --python /wzvenv/bin/python --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["bash", "start.sh"]
