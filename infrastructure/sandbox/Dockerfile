# Prototype only. Digest pins content; provenance is not approved by this file.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
LABEL org.codemate.sandbox.prototype="m9-fixture-v1"
COPY --chown=65532:65532 probe.py /opt/codemate/probe.py
USER 65532:65532
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "-I", "-S", "/opt/codemate/probe.py"]
