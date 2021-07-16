FROM python:3.8

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt
RUN apt-get update && apt-get install -y apt-transport-https \
    ca-certificates curl gnupg2 \
    software-properties-common libssl-dev qemu-utils
RUN apt-get install qemu-utils xz-utils

WORKDIR /usr/local/bin
COPY src ./


ENTRYPOINT ["python3", "/usr/local/bin/manage.py"]
