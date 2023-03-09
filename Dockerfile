FROM python:3.9.16-bullseye
WORKDIR /root
RUN  pip3 install --upgrade pip \
     && pip install --upgrade python-gitlab==3.13.0
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && apt-get clean \
    && apt-get update \
    && apt-get install -y vim tree
CMD ["/bin/bash"]
