FROM python@sha256:e16ab55c341bfd0e7da665bc2d48939cff890b43a41867fe6e1f0690638ceb7c

RUN addgroup --system candidate && adduser --system --ingroup candidate candidate
COPY scripts/factory_qualification_controller.py /controller/controller.py
ENTRYPOINT ["python3", "/controller/controller.py"]
