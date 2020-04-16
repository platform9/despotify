FROM python:3
ARG KUBE_VERSION=v1.16.8
ADD despotify.ini /
ADD requirements.txt /
RUN pip install --no-cache-dir -r requirements.txt
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$KUBE_VERSION/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin
ADD despotify/despotify.py /
ADD despotify/despotify.sh /
CMD [ "/despotify.sh"]
